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


async def _insert_currency(engine: AsyncEngine, code: str) -> None:
    await _execute(
        engine,
        "INSERT INTO core.currencies (code, name, status, minor_units) "
        "VALUES (:code, :name, 'ACTIVE', 2) "
        "ON CONFLICT (code) DO NOTHING",
        {"code": code, "name": f"{code} Currency"},
    )


async def _insert_country(engine: AsyncEngine, code: str) -> None:
    await _execute(
        engine,
        "INSERT INTO core.countries (code, name, status) "
        "VALUES (:code, :name, 'ACTIVE') "
        "ON CONFLICT (code) DO NOTHING",
        {"code": code, "name": f"{code} Country"},
    )


async def test_bank_account_lifecycle(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = await _insert_tenant(engine)
    company_id = await _insert_company(engine, tenant_id=tenant_id)
    await _insert_country(engine, "IN")
    await _insert_currency(engine, "INR")

    # 1. Create Bank Account
    payload = {
        "bank_country_code": "IN",
        "account_holder_name": "Test Holder",
        "bank_name": "Test Bank",
        "account_number": "123456789",
        "currency_code": "INR",
        "is_default_for_billing": True
    }
    response = await client.post(
        f"/companies/{company_id}/bank-accounts",
        headers={"X-Tenant-ID": str(tenant_id)},
        json=payload,
    )
    assert response.status_code == 201
    bank_account = response.json()
    assert bank_account["bank_name"] == "Test Bank"
    assert bank_account["status"] == "ACTIVE"
    assert bank_account["is_default_for_billing"] is True

    bank_account_id = bank_account["id"]

    # 2. Get Bank Account
    response = await client.get(
        f"/companies/{company_id}/bank-accounts/{bank_account_id}",
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    assert response.status_code == 200

    # 3. List Bank Accounts
    response = await client.get(
        f"/companies/{company_id}/bank-accounts",
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1

    # 4. Update Bank Account
    response = await client.patch(
        f"/companies/{company_id}/bank-accounts/{bank_account_id}",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={"bank_name": "Updated Bank"},
    )
    assert response.status_code == 200
    assert response.json()["bank_name"] == "Updated Bank"

    # 5. Inactivate Bank Account
    response = await client.post(
        f"/companies/{company_id}/bank-accounts/{bank_account_id}/inactivate",
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "INACTIVE"


async def test_bank_account_duplicate_active_default(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = await _insert_tenant(engine)
    company_id = await _insert_company(engine, tenant_id=tenant_id)
    await _insert_country(engine, "US")
    await _insert_currency(engine, "USD")

    payload1 = {
        "bank_country_code": "US",
        "account_holder_name": "Test1",
        "bank_name": "Test Bank",
        "account_number": "111",
        "currency_code": "USD",
        "is_default_for_billing": True
    }
    response = await client.post(
        f"/companies/{company_id}/bank-accounts",
        headers={"X-Tenant-ID": str(tenant_id)},
        json=payload1,
    )
    assert response.status_code == 201

    payload2 = {
        "bank_country_code": "US",
        "account_holder_name": "Test2",
        "bank_name": "Test Bank",
        "account_number": "222",
        "currency_code": "USD",
        "is_default_for_billing": True
    }
    response = await client.post(
        f"/companies/{company_id}/bank-accounts",
        headers={"X-Tenant-ID": str(tenant_id)},
        json=payload2,
    )
    # Should raise a conflict due to active unique index
    assert response.status_code == 409
