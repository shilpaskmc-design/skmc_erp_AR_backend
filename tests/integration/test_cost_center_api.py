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
        "INSERT INTO core.tenants (name, status) "
        "VALUES (:name, 'ACTIVE') RETURNING id",
        {"name": f"Tenant {uuid4()}"},
    )


async def _insert_company(
    engine: AsyncEngine,
    *,
    tenant_id: UUID,
    status: str = "DRAFT",
) -> UUID:
    return await _scalar(
        engine,
        "INSERT INTO core.companies (tenant_id, legal_name, status) "
        "VALUES (:tenant_id, :name, :status) RETURNING id",
        {
            "tenant_id": tenant_id,
            "name": f"Company {uuid4()}",
            "status": status,
        },
    )


async def _put_settings(
    client: AsyncClient,
    *,
    tenant_id: UUID,
    company_id: UUID,
    payload: dict[str, object],
):
    return await client.put(
        f"/companies/{company_id}/cost-center-settings",
        headers={"X-Tenant-ID": str(tenant_id)},
        json=payload,
    )


async def _post_master(
    client: AsyncClient,
    *,
    tenant_id: UUID,
    company_id: UUID,
    path: str,
    payload: dict[str, object],
):
    return await client.post(
        f"/companies/{company_id}/{path}",
        headers={"X-Tenant-ID": str(tenant_id)},
        json=payload,
    )


async def test_settings_and_master_creation(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = await _insert_tenant(engine)
    company_id = await _insert_company(engine, tenant_id=tenant_id)

    combinations = (
        (False, False, False),
        (True, False, False),
        (True, True, False),
        (True, True, True),
    )
    for segment_enabled, team_enabled, location_enabled in combinations:
        response = await _put_settings(
            client,
            tenant_id=tenant_id,
            company_id=company_id,
            payload={
                "cost_center_reporting_enabled": True,
                "business_segment_enabled": segment_enabled,
                "team_enabled": team_enabled,
                "location_enabled": location_enabled,
            },
        )
        assert response.status_code == 200
        assert response.json()["business_segment_enabled"] is segment_enabled
        assert response.json()["team_enabled"] is team_enabled
        assert response.json()["location_enabled"] is location_enabled

    disabled = await _put_settings(
        client,
        tenant_id=tenant_id,
        company_id=company_id,
        payload={
            "cost_center_reporting_enabled": False,
            "business_segment_enabled": False,
            "team_enabled": False,
            "location_enabled": False,
        },
    )
    invalid_disabled = await _put_settings(
        client,
        tenant_id=tenant_id,
        company_id=company_id,
        payload={
            "cost_center_reporting_enabled": False,
            "business_segment_enabled": True,
            "team_enabled": False,
            "location_enabled": False,
        },
    )
    assert disabled.status_code == 200
    assert invalid_disabled.status_code == 422

    cases = (
        ("business-segments", {"name": "Advisory", "code": "ADV"}),
        (
            "cost-center-teams",
            {"name": "Regulatory Operations", "code": "REGOPS"},
        ),
        ("teams", {"name": "BIS Team"}),
        (
            "location-cost-centers",
            {"name": "Noida Operations", "code": "NOIDA"},
        ),
    )
    for path, payload in cases:
        created = await _post_master(
            client,
            tenant_id=tenant_id,
            company_id=company_id,
            path=path,
            payload=payload,
        )
        duplicate = await _post_master(
            client,
            tenant_id=tenant_id,
            company_id=company_id,
            path=path,
            payload=payload,
        )
        assert created.status_code == 201
        assert created.json()["status"] == "ACTIVE"
        assert duplicate.status_code == 409

    assert await _scalar(
        engine, "SELECT count(*) FROM core.company_cost_center_settings"
    ) == 1
    assert await _scalar(engine, "SELECT count(*) FROM core.teams") == 1


async def test_tenant_concealment_inactive_company_and_system_fields(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = await _insert_tenant(engine)
    other_tenant_id = await _insert_tenant(engine)
    hidden_company_id = await _insert_company(
        engine,
        tenant_id=other_tenant_id,
    )
    inactive_company_id = await _insert_company(
        engine,
        tenant_id=tenant_id,
        status="INACTIVE",
    )

    hidden = await _post_master(
        client,
        tenant_id=tenant_id,
        company_id=hidden_company_id,
        path="business-segments",
        payload={"name": "Hidden"},
    )
    inactive = await _post_master(
        client,
        tenant_id=tenant_id,
        company_id=inactive_company_id,
        path="teams",
        payload={"name": "Inactive Company Team"},
    )
    injected_assignment = await _post_master(
        client,
        tenant_id=tenant_id,
        company_id=inactive_company_id,
        path="teams",
        payload={
            "name": "Injected",
            "cost_center_team_id": str(uuid4()),
        },
    )

    assert hidden.status_code == 404
    assert hidden.json() == {"detail": "Company not found"}
    assert inactive.status_code == 409
    assert injected_assignment.status_code == 422
