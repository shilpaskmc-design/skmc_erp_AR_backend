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
        if await connection.scalar(
            text("SELECT to_regnamespace('core') IS NOT NULL")
        ):
            pytest.fail("TEST_DATABASE_URL must point to a database without core schema")

        version_table_exists = await connection.scalar(
            text("SELECT to_regclass('public.alembic_version') IS NOT NULL")
        )
        if version_table_exists:
            version_count = await connection.scalar(
                text("SELECT count(*) FROM public.alembic_version")
            )
            if version_count:
                pytest.fail("TEST_DATABASE_URL already has an applied Alembic revision")


async def _assert_all_migrations_removed(database_url: str) -> None:
    async with _connection(database_url) as connection:
        assert not await connection.scalar(
            text("SELECT to_regnamespace('core') IS NOT NULL")
        )


@pytest.fixture(scope="module")
def migrated_database() -> Iterator[str]:
    database_url = os.getenv("TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL API tests")
    if make_url(database_url).drivername != "postgresql+asyncpg":
        pytest.fail("TEST_DATABASE_URL must use postgresql+asyncpg")

    asyncio.run(_assert_safe_empty_database(database_url))
    previous_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    get_settings.cache_clear()
    alembic_config = Config("alembic.ini")
    command.upgrade(alembic_config, "head")

    try:
        yield database_url
    finally:
        try:
            command.downgrade(alembic_config, "base")
            asyncio.run(_assert_all_migrations_removed(database_url))
        finally:
            if previous_database_url is None:
                os.environ.pop("DATABASE_URL", None)
            else:
                os.environ["DATABASE_URL"] = previous_database_url
            get_settings.cache_clear()


@pytest.fixture
async def api_context(
    migrated_database: str,
) -> AsyncGenerator[tuple[AsyncClient, AsyncEngine, FastAPI], None]:
    from skmc_erp.database import get_db_session
    from skmc_erp.main import app

    test_engine = create_async_engine(migrated_database)
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
    )

    async def override_db_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    settings = Settings(
        database_url=migrated_database,
        environment="development",
    )
    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_settings] = lambda: settings

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        try:
            yield client, test_engine, app
        finally:
            app.dependency_overrides.clear()
            async with test_engine.begin() as connection:
                await connection.execute(
                    text(
                        """
                        TRUNCATE TABLE
                            core.financial_years,
                            core.company_fiscal_settings,
                            core.company_locations,
                            core.companies,
                            core.organisations,
                            core.country_subdivisions,
                            core.entity_types,
                            core.currencies,
                            core.countries,
                            core.tenants
                        CASCADE
                        """
                    )
                )
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


async def _insert_tenant(engine: AsyncEngine, tenant_id: UUID) -> None:
    await _execute(
        engine,
        """
        INSERT INTO core.tenants (id, name, status)
        VALUES (:id, :name, 'ACTIVE')
        """,
        {"id": tenant_id, "name": f"Tenant {tenant_id}"},
    )


async def _insert_company(
    engine: AsyncEngine,
    *,
    company_id: UUID,
    tenant_id: UUID,
    status: str = "DRAFT",
) -> None:
    await _execute(
        engine,
        """
        INSERT INTO core.companies (id, tenant_id, legal_name, status)
        VALUES (:id, :tenant_id, :name, :status)
        """,
        {
            "id": company_id,
            "tenant_id": tenant_id,
            "name": f"Company {company_id}",
            "status": status,
        },
    )


async def _configure(
    client: AsyncClient,
    *,
    tenant_id: UUID,
    company_id: UUID,
    payload: dict[str, object],
):
    return await client.put(
        f"/companies/{company_id}/financial-year-settings",
        headers={"X-Tenant-ID": str(tenant_id)},
        json=payload,
    )


async def _generate(
    client: AsyncClient,
    *,
    tenant_id: UUID,
    company_id: UUID,
    start_year: int,
):
    return await client.post(
        f"/companies/{company_id}/financial-years",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={"start_year": start_year},
    )


async def test_configure_patterns_and_generate_expected_years(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = uuid4()
    await _insert_tenant(engine, tenant_id)

    cases = [
        (
            {"fiscal_year_pattern": "APR_MAR"},
            (4, 1),
            ("2026-04-01", "2027-03-31", "FY2026-27"),
        ),
        (
            {"fiscal_year_pattern": "JAN_DEC"},
            (1, 1),
            ("2026-01-01", "2026-12-31", "FY2026"),
        ),
        (
            {
                "fiscal_year_pattern": "CUSTOM",
                "custom_fiscal_year_start_month": 7,
                "custom_fiscal_year_start_day": 15,
            },
            (7, 15),
            ("2026-07-15", "2027-07-14", "FY2026-27"),
        ),
        (
            {
                "fiscal_year_pattern": "CUSTOM",
                "custom_fiscal_year_start_month": 2,
                "custom_fiscal_year_start_day": 28,
            },
            (2, 28),
            ("2026-02-28", "2027-02-27", "FY2026-27"),
        ),
    ]
    for settings_payload, expected_start, expected_year in cases:
        company_id = uuid4()
        await _insert_company(
            engine,
            company_id=company_id,
            tenant_id=tenant_id,
        )
        configured = await _configure(
            client,
            tenant_id=tenant_id,
            company_id=company_id,
            payload=settings_payload,
        )
        generated = await _generate(
            client,
            tenant_id=tenant_id,
            company_id=company_id,
            start_year=2026,
        )

        assert configured.status_code == 200
        assert (
            configured.json()["start_month"],
            configured.json()["start_day"],
        ) == expected_start
        assert generated.status_code == 201
        assert (
            generated.json()["start_date"],
            generated.json()["end_date"],
            generated.json()["display_code"],
        ) == expected_year
        assert generated.json()["status"] == "DRAFT"
        assert generated.json()["is_transition"] is False


async def test_company_access_and_missing_settings_rules(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = uuid4()
    other_tenant_id = uuid4()
    other_company_id = uuid4()
    inactive_company_id = uuid4()
    own_company_id = uuid4()
    await _insert_tenant(engine, tenant_id)
    await _insert_tenant(engine, other_tenant_id)
    await _insert_company(
        engine,
        company_id=other_company_id,
        tenant_id=other_tenant_id,
    )
    await _insert_company(
        engine,
        company_id=inactive_company_id,
        tenant_id=tenant_id,
        status="INACTIVE",
    )
    await _insert_company(
        engine,
        company_id=own_company_id,
        tenant_id=tenant_id,
    )

    for company_id in (uuid4(), other_company_id):
        response = await _configure(
            client,
            tenant_id=tenant_id,
            company_id=company_id,
            payload={"fiscal_year_pattern": "APR_MAR"},
        )
        assert response.status_code == 404
        assert response.json() == {"detail": "Company not found"}

        generation_response = await _generate(
            client,
            tenant_id=tenant_id,
            company_id=company_id,
            start_year=2026,
        )
        assert generation_response.status_code == 404
        assert generation_response.json() == {"detail": "Company not found"}

    inactive = await _configure(
        client,
        tenant_id=tenant_id,
        company_id=inactive_company_id,
        payload={"fiscal_year_pattern": "APR_MAR"},
    )
    missing_settings = await _generate(
        client,
        tenant_id=tenant_id,
        company_id=own_company_id,
        start_year=2026,
    )
    assert inactive.status_code == 409
    assert missing_settings.status_code == 409
    assert await _scalar(engine, "SELECT count(*) FROM core.financial_years") == 0


async def test_duplicate_overlap_and_historical_coexistence(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = uuid4()
    first_company_id = uuid4()
    second_company_id = uuid4()
    await _insert_tenant(engine, tenant_id)
    for company_id in (first_company_id, second_company_id):
        await _insert_company(
            engine,
            company_id=company_id,
            tenant_id=tenant_id,
        )
        configured = await _configure(
            client,
            tenant_id=tenant_id,
            company_id=company_id,
            payload={"fiscal_year_pattern": "APR_MAR"},
        )
        assert configured.status_code == 200

    first = await _generate(
        client,
        tenant_id=tenant_id,
        company_id=first_company_id,
        start_year=2025,
    )
    second = await _generate(
        client,
        tenant_id=tenant_id,
        company_id=first_company_id,
        start_year=2026,
    )
    duplicate = await _generate(
        client,
        tenant_id=tenant_id,
        company_id=first_company_id,
        start_year=2026,
    )
    other_company = await _generate(
        client,
        tenant_id=tenant_id,
        company_id=second_company_id,
        start_year=2026,
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert duplicate.status_code == 409
    assert other_company.status_code == 201
    assert await _scalar(
        engine,
        "SELECT count(*) FROM core.financial_years",
    ) == 3


async def test_financial_year_reads_as_of_and_lifecycle(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = uuid4()
    company_id = uuid4()
    await _insert_tenant(engine, tenant_id)
    await _insert_company(engine, company_id=company_id, tenant_id=tenant_id)
    headers = {"X-Tenant-ID": str(tenant_id)}
    assert (await _configure(client, tenant_id=tenant_id, company_id=company_id, payload={"fiscal_year_pattern": "APR_MAR"})).status_code == 200
    created = await _generate(client, tenant_id=tenant_id, company_id=company_id, start_year=2026)
    financial_year_id = created.json()["id"]

    settings = await client.get(f"/companies/{company_id}/financial-year-settings", headers=headers)
    listed = await client.get(f"/companies/{company_id}/financial-years", headers=headers)
    fetched = await client.get(f"/companies/{company_id}/financial-years/{financial_year_id}", headers=headers)
    assert settings.status_code == 200
    assert len(listed.json()) == 1
    assert fetched.status_code == 200

    invalid_close = await client.post(f"/companies/{company_id}/financial-years/{financial_year_id}/close", headers=headers)
    assert invalid_close.status_code == 409
    opened = await client.post(f"/companies/{company_id}/financial-years/{financial_year_id}/open", headers=headers)
    assert opened.status_code == 200 and opened.json()["status"] == "OPEN"
    active = await client.get(f"/companies/{company_id}/financial-years/open", params={"as_of_date": "2026-04-01"}, headers=headers)
    assert active.status_code == 200 and active.json()["id"] == financial_year_id
    closed = await client.post(f"/companies/{company_id}/financial-years/{financial_year_id}/close", headers=headers)
    assert closed.status_code == 200 and closed.json()["status"] == "CLOSED"
    reopen = await client.post(f"/companies/{company_id}/financial-years/{financial_year_id}/open", headers=headers)
    assert reopen.status_code == 409
    no_open = await client.get(f"/companies/{company_id}/financial-years/open", params={"as_of_date": "2026-04-01"}, headers=headers)
    assert no_open.status_code == 404


async def test_financial_year_reads_conceal_cross_tenant_company(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    owner_tenant = uuid4()
    other_tenant = uuid4()
    company_id = uuid4()
    await _insert_tenant(engine, owner_tenant)
    await _insert_tenant(engine, other_tenant)
    await _insert_company(engine, company_id=company_id, tenant_id=owner_tenant)
    response = await client.get(
        f"/companies/{company_id}/financial-years",
        headers={"X-Tenant-ID": str(other_tenant)},
    )
    assert response.status_code == 200
    assert response.json() == []
