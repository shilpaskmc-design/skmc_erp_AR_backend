import asyncio
import os
from collections.abc import AsyncGenerator, AsyncIterator, Iterator, Mapping
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from skmc_erp.config import Settings, get_settings


@asynccontextmanager
async def _connection(database_url: str) -> AsyncIterator[AsyncConnection]:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            yield connection
    finally:
        await engine.dispose()


async def _assert_safe_empty_database(database_url: str) -> None:
    async with _connection(database_url) as connection:
        if await connection.scalar(text("SELECT to_regnamespace('core') IS NOT NULL")):
            pytest.fail("TEST_DATABASE_URL must point to a database without core schema")
        if await connection.scalar(
            text("SELECT to_regclass('public.alembic_version') IS NOT NULL")
        ):
            count = await connection.scalar(
                text("SELECT count(*) FROM public.alembic_version")
            )
            if count:
                pytest.fail("TEST_DATABASE_URL already has an applied Alembic revision")


@pytest.fixture(scope="module")
def migrated_database() -> Iterator[str]:
    database_url = os.getenv("TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL API tests")
    if make_url(database_url).drivername != "postgresql+asyncpg":
        pytest.fail("TEST_DATABASE_URL must use postgresql+asyncpg")

    asyncio.run(_assert_safe_empty_database(database_url))
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    get_settings.cache_clear()
    command.upgrade(Config("alembic.ini"), "head")
    try:
        yield database_url
    finally:
        try:
            command.downgrade(Config("alembic.ini"), "base")
        finally:
            if previous is None:
                os.environ.pop("DATABASE_URL", None)
            else:
                os.environ["DATABASE_URL"] = previous
            get_settings.cache_clear()


@pytest.fixture
async def api_context(
    migrated_database: str,
) -> AsyncGenerator[tuple[AsyncClient, AsyncEngine, FastAPI], None]:
    from skmc_erp.database import get_db_session
    from skmc_erp.main import app

    test_engine = create_async_engine(migrated_database)
    factory = async_sessionmaker(bind=test_engine, class_=AsyncSession)

    async def override_db_session() -> AsyncGenerator[AsyncSession, None]:
        async with factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    settings = Settings(database_url=migrated_database, environment="development")
    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_settings] = lambda: settings
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        try:
            yield client, test_engine, app
        finally:
            app.dependency_overrides.clear()
            async with test_engine.begin() as connection:
                await connection.execute(text("TRUNCATE core.tenants CASCADE"))
            await test_engine.dispose()


async def _execute(
    engine: AsyncEngine,
    sql: str,
    parameters: Mapping[str, object] | None = None,
) -> None:
    async with engine.begin() as connection:
        await connection.execute(text(sql), parameters or {})


async def _scalar(
    engine: AsyncEngine,
    sql: str,
    parameters: Mapping[str, object] | None = None,
) -> object:
    async with engine.begin() as connection:
        return await connection.scalar(text(sql), parameters or {})


async def _insert_tenant(engine: AsyncEngine) -> UUID:
    return await _scalar(
        engine,
        "INSERT INTO core.tenants (name, status) VALUES (:name, 'ACTIVE') RETURNING id",
        {"name": f"Tenant {uuid4()}"},
    )


async def _insert_company(engine: AsyncEngine, *, tenant_id: UUID) -> UUID:
    return await _scalar(
        engine,
        "INSERT INTO core.companies (tenant_id, legal_name, status) VALUES (:tenant_id, :name, 'DRAFT') RETURNING id",
        {"tenant_id": tenant_id, "name": f"Company {uuid4()}"},
    )


import random

async def _insert_gst_registration(engine: AsyncEngine, *, company_id: UUID) -> UUID:
    async with engine.begin() as connection:
        await connection.execute(text(
            "INSERT INTO core.countries (code, name, status) "
            "VALUES ('IN', 'India', 'ACTIVE') ON CONFLICT (code) DO NOTHING"
        ))
        await connection.execute(text(
            "INSERT INTO core.country_subdivisions (country_code, code, name, subdivision_type, gst_state_code, status) "
            "VALUES ('IN', 'IN-UP', 'Uttar Pradesh', 'STATE', '09', 'ACTIVE') ON CONFLICT (code) DO NOTHING"
        ))

    random_digits = str(random.randint(1000, 9999))
    gstin = f"09ABCDE{random_digits}F1Z5"
    return await _scalar(
        engine,
        "INSERT INTO core.company_gst_registrations (company_id, gstin, subdivision_code, valid_from, status) "
        "VALUES (:company_id, :gstin, 'IN-UP', '2025-01-01', 'ACTIVE') RETURNING id",
        {"company_id": company_id, "gstin": gstin},
    )


async def _insert_financial_year(engine: AsyncEngine, *, company_id: UUID) -> UUID:
    return await _scalar(
        engine,
        "INSERT INTO core.financial_years (company_id, start_date, end_date, display_code, is_transition, status) "
        "VALUES (:company_id, '2026-04-01', '2027-03-31', 'FY 2026-27', FALSE, 'OPEN') RETURNING id",
        {"company_id": company_id},
    )


@pytest.mark.asyncio
async def test_create_company_lut(api_context: tuple[AsyncClient, AsyncEngine, FastAPI]):
    client, engine, _ = api_context
    tenant_id = await _insert_tenant(engine)
    company_id = await _insert_company(engine, tenant_id=tenant_id)
    gst_reg_id = await _insert_gst_registration(engine, company_id=company_id)
    fy_id = await _insert_financial_year(engine, company_id=company_id)

    response = await client.post(
        f"/companies/{company_id}/luts",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={
            "gst_registration_id": str(gst_reg_id),
            "financial_year_id": str(fy_id),
            "lut_reference": "LUT/2026/001",
            "valid_from": "2026-04-01",
            "valid_to": "2027-03-31",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["lut_reference"] == "LUT/2026/001"
    assert data["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_create_company_lut_uniqueness_rejected(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI]
):
    client, engine, _ = api_context
    tenant_id = await _insert_tenant(engine)
    company_id = await _insert_company(engine, tenant_id=tenant_id)
    gst_reg_id = await _insert_gst_registration(engine, company_id=company_id)
    fy_id = await _insert_financial_year(engine, company_id=company_id)

    await client.post(
        f"/companies/{company_id}/luts",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={
            "gst_registration_id": str(gst_reg_id),
            "financial_year_id": str(fy_id),
            "lut_reference": "LUT/2026/001",
            "valid_from": "2026-04-01",
        },
    )

    response = await client.post(
        f"/companies/{company_id}/luts",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={
            "gst_registration_id": str(gst_reg_id),
            "financial_year_id": str(fy_id),
            "lut_reference": "LUT/2026/002",
            "valid_from": "2026-05-01",
        },
    )
    assert response.status_code == 409
    assert "ACTIVE LUT already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_inactivate_company_lut(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI]
):
    client, engine, _ = api_context
    tenant_id = await _insert_tenant(engine)
    company_id = await _insert_company(engine, tenant_id=tenant_id)
    gst_reg_id = await _insert_gst_registration(engine, company_id=company_id)
    fy_id = await _insert_financial_year(engine, company_id=company_id)

    create_response = await client.post(
        f"/companies/{company_id}/luts",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={
            "gst_registration_id": str(gst_reg_id),
            "financial_year_id": str(fy_id),
            "lut_reference": "LUT/2026/001",
            "valid_from": "2026-04-01",
        },
    )
    lut_id = create_response.json()["id"]

    inact_response = await client.post(
        f"/companies/{company_id}/luts/{lut_id}/inactivate",
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    assert inact_response.status_code == 200
    assert inact_response.json()["status"] == "INACTIVE"

    # Now we should be able to create a new one since the old one is inactive
    new_response = await client.post(
        f"/companies/{company_id}/luts",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={
            "gst_registration_id": str(gst_reg_id),
            "financial_year_id": str(fy_id),
            "lut_reference": "LUT/2026/002",
            "valid_from": "2026-05-01",
            "valid_to": "2027-03-31",
        },
    )
    assert new_response.status_code == 200


@pytest.mark.asyncio
async def test_activate_company_lut_conflict(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI]
):
    client, engine, _ = api_context
    tenant_id = await _insert_tenant(engine)
    company_id = await _insert_company(engine, tenant_id=tenant_id)
    gst_reg_id = await _insert_gst_registration(engine, company_id=company_id)
    fy_id = await _insert_financial_year(engine, company_id=company_id)

    # Create first one
    create1 = await client.post(
        f"/companies/{company_id}/luts",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={
            "gst_registration_id": str(gst_reg_id),
            "financial_year_id": str(fy_id),
            "lut_reference": "LUT/1",
            "valid_from": "2026-04-01",
        },
    )
    lut1_id = create1.json()["id"]

    # Inactivate first one
    await client.post(
        f"/companies/{company_id}/luts/{lut1_id}/inactivate",
        headers={"X-Tenant-ID": str(tenant_id)},
    )

    # Create second one (ACTIVE)
    await client.post(
        f"/companies/{company_id}/luts",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={
            "gst_registration_id": str(gst_reg_id),
            "financial_year_id": str(fy_id),
            "lut_reference": "LUT/2",
            "valid_from": "2026-05-01",
        },
    )

    # Try to reactivate first one while second one is active -> should fail
    reactivate = await client.post(
        f"/companies/{company_id}/luts/{lut1_id}/activate",
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    assert reactivate.status_code == 409
    assert "already exists" in reactivate.json()["detail"]


@pytest.mark.asyncio
async def test_cross_company_lut_rejected(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI]
):
    client, engine, _ = api_context
    tenant_id = await _insert_tenant(engine)
    company_1 = await _insert_company(engine, tenant_id=tenant_id)
    company_2 = await _insert_company(engine, tenant_id=tenant_id)

    gst_reg_2 = await _insert_gst_registration(engine, company_id=company_2)
    fy_1 = await _insert_financial_year(engine, company_id=company_1)

    response = await client.post(
        f"/companies/{company_1}/luts",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={
            "gst_registration_id": str(gst_reg_2),
            "financial_year_id": str(fy_1),
            "lut_reference": "LUT/1",
            "valid_from": "2026-04-01",
        },
    )
    assert response.status_code == 409
    assert "same Company" in response.json()["detail"]
