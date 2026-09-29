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

@pytest.mark.asyncio
async def test_accounting_structure_lifecycle(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = await _insert_tenant(engine)
    company_id = await _insert_company(engine, tenant_id=tenant_id)
    test_headers = {"X-Tenant-ID": str(tenant_id)}

    # 1. Primary Hierarchy Creation
    response = await client.post(
        f"/companies/{company_id}/accounting/hierarchy",
        json={"hierarchy_name": "Main Accounting"},
        headers=test_headers,
    )
    assert response.status_code == 201
    hierarchy = response.json()
    assert hierarchy["hierarchy_name"] == "Main Accounting"
    hierarchy_id = hierarchy["id"]

    # Prevent duplicate primary hierarchy
    response = await client.post(
        f"/companies/{company_id}/accounting/hierarchy",
        json={"hierarchy_name": "Main Accounting 2"},
        headers=test_headers,
    )
    assert response.status_code == 422

    # Get Primary Hierarchy
    response = await client.get(
        f"/companies/{company_id}/accounting/hierarchy",
        headers=test_headers,
    )
    assert response.status_code == 200
    assert response.json()["id"] == hierarchy_id

    # 2. Account Groups
    # Create Assets Group
    response = await client.post(
        f"/companies/{company_id}/accounting/hierarchy/{hierarchy_id}/account-groups",
        json={"group_name": "Assets", "group_code": "AST"},
        headers=test_headers,
    )
    assert response.status_code == 201
    assets_group = response.json()
    assets_id = assets_group["id"]

    # Create Current Assets Group
    response = await client.post(
        f"/companies/{company_id}/accounting/hierarchy/{hierarchy_id}/account-groups",
        json={"group_name": "Current Assets", "group_code": "CA"},
        headers=test_headers,
    )
    assert response.status_code == 201
    ca_id = response.json()["id"]

    # Update Group Name
    response = await client.patch(
        f"/companies/{company_id}/account-groups/{ca_id}",
        json={"group_name": "Current Assets Updated"},
        headers=test_headers,
    )
    assert response.status_code == 200
    assert response.json()["group_name"] == "Current Assets Updated"

    # 3. Group Relationships
    today = date.today()
    tomorrow = today + timedelta(days=1)

    # Reparent: Assign CA to Assets
    response = await client.post(
        f"/companies/{company_id}/account-groups/{ca_id}/reparent",
        json={"new_parent_group_id": assets_id, "effective_date": today.isoformat()},
        headers=test_headers,
    )
    assert response.status_code == 200
    assert response.json()["parent_group_id"] == assets_id

    # Reject Self-Parent
    response = await client.post(
        f"/companies/{company_id}/account-groups/{ca_id}/reparent",
        json={"new_parent_group_id": ca_id, "effective_date": tomorrow.isoformat()},
        headers=test_headers,
    )
    assert response.status_code == 422

    # Move CA to root
    response = await client.post(
        f"/companies/{company_id}/account-groups/{ca_id}/move-to-root",
        json={"effective_date": tomorrow.isoformat()},
        headers=test_headers,
    )
    assert response.status_code == 200

    # 4. GL Account Placements
    # Create GL Account
    response = await client.post(
        f"/companies/{company_id}/gl-accounts",
        json={"account_name": "Cash", "account_code": "CASH", "valid_from": today.isoformat()},
        headers=test_headers,
    )
    assert response.status_code == 201
    gl_id = response.json()["id"]

    # Place in Group (CA)
    response = await client.post(
        f"/companies/{company_id}/gl-accounts/{gl_id}/group-assignment?hierarchy_id={hierarchy_id}",
        json={"account_group_id": ca_id, "effective_date": today.isoformat()},
        headers=test_headers,
    )
    assert response.status_code == 200

    # Move GL Account to Root
    response = await client.post(
        f"/companies/{company_id}/gl-accounts/{gl_id}/root-assignment?hierarchy_id={hierarchy_id}",
        json={"effective_date": tomorrow.isoformat()},
        headers=test_headers,
    )
    assert response.status_code == 200
    assert response.json()["account_group_id"] is None

    # End Assignment
    future_date = today + timedelta(days=5)
    response = await client.post(
        f"/companies/{company_id}/gl-accounts/{gl_id}/end-assignment",
        json={"effective_date": future_date.isoformat()},
        headers=test_headers,
    )
    assert response.status_code == 200

    # 5. Inactivation Guards
    # Create a fresh group and GL to test inactivation cleanly
    group_inact = await client.post(
        f"/companies/{company_id}/accounting/hierarchy/{hierarchy_id}/account-groups",
        json={"group_name": "To Be Inactivated"},
        headers=test_headers,
    )
    inact_group_id = group_inact.json()["id"]

    gl_inact = await client.post(
        f"/companies/{company_id}/gl-accounts",
        json={"account_name": "Inact GL", "account_code": "INACT", "valid_from": "2020-01-01"},
        headers=test_headers,
    )
    inact_gl_id = gl_inact.json()["id"]

    # Assign GL to group on 2020-01-01
    await client.post(
        f"/companies/{company_id}/gl-accounts/{inact_gl_id}/group-assignment?hierarchy_id={hierarchy_id}",
        json={"account_group_id": inact_group_id, "effective_date": "2020-01-01"},
        headers=test_headers,
    )

    # Inactivation should fail
    response = await client.post(
        f"/companies/{company_id}/account-groups/{inact_group_id}/inactivate",
        headers=test_headers,
    )
    assert response.status_code == 409  # Blocked by GL placement

    # Remove GL placement on 2020-02-01 (so valid_to becomes 2020-01-31, which is in the past)
    await client.post(
        f"/companies/{company_id}/gl-accounts/{inact_gl_id}/end-assignment",
        json={"effective_date": "2020-02-01"},
        headers=test_headers,
    )

    # Create a child group on 2020-02-01
    child_group = await client.post(
        f"/companies/{company_id}/accounting/hierarchy/{hierarchy_id}/account-groups",
        json={"group_name": "Child Inact"},
        headers=test_headers,
    )
    child_id = child_group.json()["id"]

    await client.post(
        f"/companies/{company_id}/account-groups/{child_id}/reparent",
        json={"new_parent_group_id": inact_group_id, "effective_date": "2020-02-01"},
        headers=test_headers,
    )

    # Inactivation should fail again
    response = await client.post(
        f"/companies/{company_id}/account-groups/{inact_group_id}/inactivate",
        headers=test_headers,
    )
    assert response.status_code == 409  # Blocked by child relationship

    # Move child to root on 2020-03-01
    await client.post(
        f"/companies/{company_id}/account-groups/{child_id}/move-to-root",
        json={"effective_date": "2020-03-01"},
        headers=test_headers,
    )

    # Now inactivate should succeed
    response = await client.post(
        f"/companies/{company_id}/account-groups/{inact_group_id}/inactivate",
        headers=test_headers,
    )
    assert response.status_code == 200

    # 6. Company Accounting Settings
    response = await client.patch(
        f"/companies/{company_id}/accounting/settings",
        json={"default_receivable_gl_account_id": gl_id},
        headers=test_headers,
    )
    assert response.status_code == 200

    response = await client.get(
        f"/companies/{company_id}/accounting/settings",
        headers=test_headers,
    )
    assert response.status_code == 200
    assert response.json()["default_receivable_gl_account_id"] == gl_id
