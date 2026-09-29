import asyncio
import os
from collections.abc import AsyncGenerator, AsyncIterator, Iterator, Mapping
from contextlib import asynccontextmanager
from datetime import date, timedelta
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


async def _insert_gl_account(
    engine: AsyncEngine, *, company_id: UUID, status: str = "ACTIVE"
) -> UUID:
    return await _scalar(
        engine,
        "INSERT INTO core.gl_accounts (company_id, account_code, account_name, valid_from, status) "
        "VALUES (:company_id, :code, :name, '2025-01-01', :st) RETURNING id",
        {
            "company_id": company_id,
            "code": f"GL-{uuid4()}"[:20],
            "name": "Test GL Account",
            "st": status,
        },
    )


async def _insert_tax_type(engine: AsyncEngine) -> UUID:
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO core.countries (code, name, status) "
                "VALUES ('IN', 'India', 'ACTIVE') ON CONFLICT (code) DO NOTHING"
            )
        )
    return await _scalar(
        engine,
        "INSERT INTO core.tax_types (code, name, country_code, status) "
        "VALUES (:code, 'Test Tax Type', 'IN', 'ACTIVE') RETURNING id",
        {"code": f"TAX-{uuid4()}"[:30]},
    )


async def _insert_tax_statutory_code(
    engine: AsyncEngine, *, tax_type_id: UUID, code_kind: str
) -> UUID:
    return await _scalar(
        engine,
        "INSERT INTO core.tax_statutory_codes (tax_type_id, code, name, code_kind, country_code, status) "
        "VALUES (:tax_type_id, :code, 'Test Code', :code_kind, 'IN', 'ACTIVE') RETURNING id",
        {
            "tax_type_id": tax_type_id,
            "code": f"CODE-{uuid4()}"[:30],
            "code_kind": code_kind,
        },
    )


async def _insert_service_type(
    engine: AsyncEngine, *, company_id: UUID, status: str = "ACTIVE"
) -> UUID:
    cat_id = await _scalar(
        engine,
        "INSERT INTO ar.service_categories (company_id, name, status) VALUES (:c, 'Cat', 'ACTIVE') RETURNING id",
        {"c": company_id},
    )
    hsn_sac_id = await _scalar(
        engine,
        "INSERT INTO core.company_hsn_sac_codes "
        "(company_id, classification_type, code, description, status) "
        "VALUES (:c, 'SAC', '998311', 'IT consulting services', 'ACTIVE') "
        "RETURNING id",
        {"c": company_id},
    )
    tax_type_id = await _insert_tax_type(engine)
    tr_id = await _scalar(
        engine,
        "INSERT INTO core.tax_rates "
        "(tax_type_id, rate_percent, country_code, status) "
        "VALUES (:tax_type, 18.0, 'IN', 'ACTIVE') RETURNING id",
        {"tax_type": tax_type_id},
    )
    tt_id = await _scalar(
        engine,
        "INSERT INTO core.tax_treatments "
        "(code, name, tax_type_id, country_code, status) "
        "VALUES ('TAXABLE', 'Taxable', :tax_type, 'IN', 'ACTIVE') "
        "RETURNING id",
        {"tax_type": tax_type_id},
    )
    return await _scalar(
        engine,
        "INSERT INTO ar.service_types ("
        "  company_id, service_category_id, name, company_hsn_sac_code_id, selected_tax_rate_id, tax_treatment_id, status"
        ") VALUES (:c, :cat, :name, :sac, :tr, :tt, :st) RETURNING id",
        {
            "c": company_id,
            "cat": cat_id,
            "name": f"Service {uuid4()}",
            "sac": hsn_sac_id,
            "tr": tr_id,
            "tt": tt_id,
            "st": status,
        },
    )


async def _insert_sku(
    engine: AsyncEngine, *, company_id: UUID, status: str = "ACTIVE"
) -> UUID:
    cat_id = await _scalar(
        engine,
        "INSERT INTO ar.product_categories (company_id, name, status) VALUES (:c, 'ProdCat', 'ACTIVE') RETURNING id",
        {"c": company_id},
    )
    p_id = await _scalar(
        engine,
        "INSERT INTO ar.products (company_id, product_category_id, name, status) VALUES (:c, :cat, 'Prod', 'ACTIVE') RETURNING id",
        {"c": company_id, "cat": cat_id},
    )
    hsn_sac_id = await _scalar(
        engine,
        "INSERT INTO core.company_hsn_sac_codes "
        "(company_id, classification_type, code, description, status) "
        "VALUES (:c, 'HSN', '84713010', 'Portable computers', 'ACTIVE') "
        "RETURNING id",
        {"c": company_id},
    )
    tax_type_id = await _insert_tax_type(engine)
    tr_id = await _scalar(
        engine,
        "INSERT INTO core.tax_rates "
        "(tax_type_id, rate_percent, country_code, status) "
        "VALUES (:tax_type, 18.0, 'IN', 'ACTIVE') RETURNING id",
        {"tax_type": tax_type_id},
    )
    tt_id = await _scalar(
        engine,
        "INSERT INTO core.tax_treatments "
        "(code, name, tax_type_id, country_code, status) "
        "VALUES ('TAXABLE', 'Taxable', :tax_type, 'IN', 'ACTIVE') "
        "RETURNING id",
        {"tax_type": tax_type_id},
    )
    return await _scalar(
        engine,
        "INSERT INTO ar.skus ("
        "  company_id, product_id, sku_code, name, uom, company_hsn_sac_code_id, selected_tax_rate_id, tax_treatment_id, status"
        ") VALUES (:c, :p, :code, 'SKU Item', 'NOS', :sac, :tr, :tt, :st) RETURNING id",
        {
            "c": company_id,
            "p": p_id,
            "code": f"SKU-{uuid4()}"[:20],
            "sac": hsn_sac_id,
            "tr": tr_id,
            "tt": tt_id,
            "st": status,
        },
    )


async def _insert_company_location(
    engine: AsyncEngine, *, company_id: UUID, status: str = "ACTIVE"
) -> UUID:
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO core.countries (code, name, status) VALUES ('IN', 'India', 'ACTIVE') ON CONFLICT (code) DO NOTHING"
            )
        )
    return await _scalar(
        engine,
        "INSERT INTO core.company_locations ("
        "  company_id, location_name, address_line_1, city, country_code, is_branch, status"
        ") VALUES (:c, 'Location Name', 'Addr', 'City', 'IN', true, :st) RETURNING id",
        {"c": company_id, "st": status},
    )


# --- Tax GL Mapping Tests ---

@pytest.mark.asyncio
async def test_assign_tax_gl_mapping(api_context: tuple[AsyncClient, AsyncEngine, FastAPI]):
    client, engine, _ = api_context
    tenant_id = await _insert_tenant(engine)
    company_id = await _insert_company(engine, tenant_id=tenant_id)
    gl_account_id = await _insert_gl_account(engine, company_id=company_id)
    tax_type_id = await _insert_tax_type(engine)
    stat_code_id = await _insert_tax_statutory_code(engine, tax_type_id=tax_type_id, code_kind="COMPONENT")

    response = await client.post(
        f"/companies/{company_id}/tax-gl-mappings",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={
            "tax_statutory_code_id": str(stat_code_id),
            "gl_account_id": str(gl_account_id),
            "valid_from": "2026-04-01",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["gl_account_id"] == str(gl_account_id)
    assert data["tax_statutory_code_id"] == str(stat_code_id)
    assert data["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_assign_tax_gl_mapping_cross_company_gl_rejected(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI]
):
    client, engine, _ = api_context
    tenant_id = await _insert_tenant(engine)
    company_1 = await _insert_company(engine, tenant_id=tenant_id)
    company_2 = await _insert_company(engine, tenant_id=tenant_id)

    gl_account_2_id = await _insert_gl_account(engine, company_id=company_2)
    tax_type_id = await _insert_tax_type(engine)
    stat_code_id = await _insert_tax_statutory_code(engine, tax_type_id=tax_type_id, code_kind="COMPONENT")

    response = await client.post(
        f"/companies/{company_1}/tax-gl-mappings",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={
            "tax_statutory_code_id": str(stat_code_id),
            "gl_account_id": str(gl_account_2_id),
            "valid_from": "2026-04-01",
        },
    )
    assert response.status_code == 409
    assert "same Company" in response.json()["detail"]


@pytest.mark.asyncio
async def test_assign_tax_gl_mapping_overlap_rejected(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI]
):
    client, engine, _ = api_context
    tenant_id = await _insert_tenant(engine)
    company_id = await _insert_company(engine, tenant_id=tenant_id)
    gl_account_id = await _insert_gl_account(engine, company_id=company_id)
    tax_type_id = await _insert_tax_type(engine)
    stat_code_id = await _insert_tax_statutory_code(engine, tax_type_id=tax_type_id, code_kind="COMPONENT")

    await client.post(
        f"/companies/{company_id}/tax-gl-mappings",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={
            "tax_statutory_code_id": str(stat_code_id),
            "gl_account_id": str(gl_account_id),
            "valid_from": "2026-04-01",
        },
    )

    response = await client.post(
        f"/companies/{company_id}/tax-gl-mappings",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={
            "tax_statutory_code_id": str(stat_code_id),
            "gl_account_id": str(gl_account_id),
            "valid_from": "2026-05-01",
        },
    )
    assert response.status_code == 409
    assert "overlaps" in response.json()["detail"]


# --- Revenue GL Mapping Tests ---

@pytest.mark.asyncio
async def test_assign_revenue_gl_mapping_service_type_item_only(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI]
):
    client, engine, _ = api_context
    tenant_id = await _insert_tenant(engine)
    company_id = await _insert_company(engine, tenant_id=tenant_id)
    gl_id = await _insert_gl_account(engine, company_id=company_id)
    st_id = await _insert_service_type(engine, company_id=company_id)

    response = await client.post(
        f"/companies/{company_id}/revenue-gl-mappings",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={
            "service_type_id": str(st_id),
            "gl_account_id": str(gl_id),
            "valid_from": "2026-01-01",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["service_type_id"] == str(st_id)
    assert data["sku_id"] is None
    assert data["supply_type_code"] is None
    assert data["company_location_id"] is None
    assert data["gl_account_id"] == str(gl_id)
    assert data["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_assign_revenue_gl_mapping_sku_item_only(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI]
):
    client, engine, _ = api_context
    tenant_id = await _insert_tenant(engine)
    company_id = await _insert_company(engine, tenant_id=tenant_id)
    gl_id = await _insert_gl_account(engine, company_id=company_id)
    sku_id = await _insert_sku(engine, company_id=company_id)

    response = await client.post(
        f"/companies/{company_id}/revenue-gl-mappings",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={
            "sku_id": str(sku_id),
            "gl_account_id": str(gl_id),
            "valid_from": "2026-01-01",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["sku_id"] == str(sku_id)
    assert data["service_type_id"] is None


@pytest.mark.asyncio
async def test_assign_revenue_gl_mapping_service_type_supply_and_location(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI]
):
    client, engine, _ = api_context
    tenant_id = await _insert_tenant(engine)
    company_id = await _insert_company(engine, tenant_id=tenant_id)
    gl_id = await _insert_gl_account(engine, company_id=company_id)
    st_id = await _insert_service_type(engine, company_id=company_id)
    loc_id = await _insert_company_location(engine, company_id=company_id)

    response = await client.post(
        f"/companies/{company_id}/revenue-gl-mappings",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={
            "service_type_id": str(st_id),
            "supply_type_code": "B2B",
            "company_location_id": str(loc_id),
            "gl_account_id": str(gl_id),
            "valid_from": "2026-01-01",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["supply_type_code"] == "B2B"
    assert data["company_location_id"] == str(loc_id)


@pytest.mark.asyncio
async def test_assign_revenue_gl_mapping_both_items_rejected(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI]
):
    client, engine, _ = api_context
    tenant_id = await _insert_tenant(engine)
    company_id = await _insert_company(engine, tenant_id=tenant_id)
    gl_id = await _insert_gl_account(engine, company_id=company_id)
    st_id = await _insert_service_type(engine, company_id=company_id)
    sku_id = await _insert_sku(engine, company_id=company_id)

    response = await client.post(
        f"/companies/{company_id}/revenue-gl-mappings",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={
            "service_type_id": str(st_id),
            "sku_id": str(sku_id),
            "gl_account_id": str(gl_id),
            "valid_from": "2026-01-01",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_assign_revenue_gl_mapping_neither_item_rejected(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI]
):
    client, engine, _ = api_context
    tenant_id = await _insert_tenant(engine)
    company_id = await _insert_company(engine, tenant_id=tenant_id)
    gl_id = await _insert_gl_account(engine, company_id=company_id)

    response = await client.post(
        f"/companies/{company_id}/revenue-gl-mappings",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={
            "gl_account_id": str(gl_id),
            "valid_from": "2026-01-01",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_assign_revenue_gl_mapping_unknown_supply_type_rejected(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI]
):
    client, engine, _ = api_context
    tenant_id = await _insert_tenant(engine)
    company_id = await _insert_company(engine, tenant_id=tenant_id)
    gl_id = await _insert_gl_account(engine, company_id=company_id)
    st_id = await _insert_service_type(engine, company_id=company_id)

    response = await client.post(
        f"/companies/{company_id}/revenue-gl-mappings",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={
            "service_type_id": str(st_id),
            "supply_type_code": "INVALID_SUPPLY",
            "gl_account_id": str(gl_id),
            "valid_from": "2026-01-01",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_assign_revenue_gl_mapping_inactive_service_type_rejected(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI]
):
    client, engine, _ = api_context
    tenant_id = await _insert_tenant(engine)
    company_id = await _insert_company(engine, tenant_id=tenant_id)
    gl_id = await _insert_gl_account(engine, company_id=company_id)
    st_id = await _insert_service_type(engine, company_id=company_id, status="INACTIVE")

    response = await client.post(
        f"/companies/{company_id}/revenue-gl-mappings",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={
            "service_type_id": str(st_id),
            "gl_account_id": str(gl_id),
            "valid_from": "2026-01-01",
        },
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_end_and_list_revenue_gl_mapping(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI]
):
    client, engine, _ = api_context
    tenant_id = await _insert_tenant(engine)
    company_id = await _insert_company(engine, tenant_id=tenant_id)
    gl_id = await _insert_gl_account(engine, company_id=company_id)
    st_id = await _insert_service_type(engine, company_id=company_id)

    create_res = await client.post(
        f"/companies/{company_id}/revenue-gl-mappings",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={
            "service_type_id": str(st_id),
            "gl_account_id": str(gl_id),
            "valid_from": "2026-01-01",
        },
    )
    mapping_id = create_res.json()["id"]

    end_res = await client.post(
        f"/companies/{company_id}/revenue-gl-mappings/{mapping_id}/end",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={"valid_to": "2026-12-31"},
    )
    assert end_res.status_code == 200
    assert end_res.json()["valid_to"] == "2026-12-31"
    assert end_res.json()["status"] == "INACTIVE"

    list_res = await client.get(
        f"/companies/{company_id}/revenue-gl-mappings",
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) == 1
    assert items[0]["id"] == mapping_id
    assert items[0]["status"] == "INACTIVE"
