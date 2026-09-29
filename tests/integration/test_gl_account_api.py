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


async def test_gl_account_lifecycle(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = await _insert_tenant(engine)
    company_id = await _insert_company(engine, tenant_id=tenant_id)

    # 1. Create GL Account
    payload = {
        "account_code": "1001",
        "account_name": "Test GL Account",
        "valid_from": "2026-01-01",
        "valid_to": "2026-12-31"
    }
    response = await client.post(
        f"/companies/{company_id}/gl-accounts",
        headers={"X-Tenant-ID": str(tenant_id)},
        json=payload,
    )
    assert response.status_code == 201
    gl_account = response.json()
    assert gl_account["account_name"] == "Test GL Account"
    assert gl_account["status"] == "ACTIVE"

    gl_account_id = gl_account["id"]

    # 2. Get GL Account
    response = await client.get(
        f"/companies/{company_id}/gl-accounts/{gl_account_id}",
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    assert response.status_code == 200

    # 3. List GL Accounts
    response = await client.get(
        f"/companies/{company_id}/gl-accounts",
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1

    # 4. Update GL Account
    response = await client.patch(
        f"/companies/{company_id}/gl-accounts/{gl_account_id}",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={"account_name": "Updated GL Account"},
    )
    assert response.status_code == 200
    assert response.json()["account_name"] == "Updated GL Account"

    # 5. Inactivate GL Account
    response = await client.post(
        f"/companies/{company_id}/gl-accounts/{gl_account_id}/inactivate",
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "INACTIVE"

    mutation = await client.patch(
        f"/companies/{company_id}/gl-accounts/{gl_account_id}",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={"account_name": "Forbidden"},
    )
    assert mutation.status_code == 409


async def test_gl_account_cross_tenant_concealment(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant1_id = await _insert_tenant(engine)
    company1_id = await _insert_company(engine, tenant_id=tenant1_id)

    tenant2_id = await _insert_tenant(engine)

    # Attempt to list using wrong tenant
    response = await client.get(
        f"/companies/{company1_id}/gl-accounts",
        headers={"X-Tenant-ID": str(tenant2_id)},
    )
    assert response.status_code == 200
    assert len(response.json()) == 0

    # Attempt to create using wrong tenant
    response = await client.post(
        f"/companies/{company1_id}/gl-accounts",
        headers={"X-Tenant-ID": str(tenant2_id)},
        json={
            "account_name": "Hack",
            "valid_from": "2026-01-01"
        },
    )
    assert response.status_code == 422


async def test_gl_account_duplicate_code(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = await _insert_tenant(engine)
    company_id = await _insert_company(engine, tenant_id=tenant_id)

    payload = {
        "account_code": "DUP123",
        "account_name": "Test1",
        "valid_from": "2026-01-01",
    }
    response = await client.post(
        f"/companies/{company_id}/gl-accounts",
        headers={"X-Tenant-ID": str(tenant_id)},
        json=payload,
    )
    assert response.status_code == 201

    payload["account_name"] = "Test2"
    response = await client.post(
        f"/companies/{company_id}/gl-accounts",
        headers={"X-Tenant-ID": str(tenant_id)},
        json=payload,
    )
    assert response.status_code == 409
