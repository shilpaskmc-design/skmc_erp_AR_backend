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
    async with engine.connect() as connection:
        return await connection.scalar(text(sql), parameters or {})


async def _insert_tenant(
    engine: AsyncEngine,
    tenant_id: UUID,
) -> None:
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


async def _insert_country(
    engine: AsyncEngine,
    *,
    code: str,
    status: str = "ACTIVE",
) -> None:
    await _execute(
        engine,
        """
        INSERT INTO core.countries (code, name, status)
        VALUES (:code, :name, :status)
        """,
        {"code": code, "name": f"Country {code}", "status": status},
    )


async def _insert_subdivision(
    engine: AsyncEngine,
    *,
    country_code: str,
    code: str,
    status: str = "ACTIVE",
) -> None:
    await _execute(
        engine,
        """
        INSERT INTO core.country_subdivisions
            (country_code, code, name, subdivision_type, status)
        VALUES
            (:country_code, :code, :name, 'STATE', :status)
        """,
        {
            "country_code": country_code,
            "code": code,
            "name": f"Subdivision {code}",
            "status": status,
        },
    )


def _location_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "location_name": "Noida Branch",
        "address_line_1": "Sector 62",
        "city": "Noida",
        "country_code": "IN",
        "is_branch": True,
    }
    payload.update(overrides)
    return payload


async def test_minimal_location_creation_and_multiple_purposes(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = uuid4()
    company_id = uuid4()
    await _insert_tenant(engine, tenant_id)
    await _insert_company(engine, company_id=company_id, tenant_id=tenant_id)
    await _insert_country(engine, code="IN")

    minimal = await client.post(
        f"/companies/{company_id}/locations",
        headers={"X-Tenant-ID": str(tenant_id)},
        json=_location_payload(),
    )
    multipurpose = await client.post(
        f"/companies/{company_id}/locations",
        headers={"X-Tenant-ID": str(tenant_id)},
        json=_location_payload(
            location_name="Corporate Billing Office",
            is_branch=False,
            is_corporate_office=True,
            is_billing_office=True,
        ),
    )

    assert minimal.status_code == 201
    assert UUID(minimal.json()["id"])
    assert minimal.json()["company_id"] == str(company_id)
    assert minimal.json()["status"] == "ACTIVE"
    assert minimal.json()["subdivision_code"] is None
    assert multipurpose.status_code == 201
    assert multipurpose.json()["is_corporate_office"] is True
    assert multipurpose.json()["is_billing_office"] is True
    assert await _scalar(
        engine,
        "SELECT count(*) FROM core.company_locations",
    ) == 2


async def test_company_lookup_is_tenant_safe_and_rejects_inactive_company(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = uuid4()
    other_tenant_id = uuid4()
    other_company_id = uuid4()
    inactive_company_id = uuid4()
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
    await _insert_country(engine, code="IN")

    for company_id in (uuid4(), other_company_id):
        response = await client.post(
            f"/companies/{company_id}/locations",
            headers={"X-Tenant-ID": str(tenant_id)},
            json=_location_payload(),
        )
        assert response.status_code == 404
        assert response.json() == {"detail": "Company not found"}

    inactive = await client.post(
        f"/companies/{inactive_company_id}/locations",
        headers={"X-Tenant-ID": str(tenant_id)},
        json=_location_payload(),
    )
    assert inactive.status_code == 409
    assert await _scalar(
        engine,
        "SELECT count(*) FROM core.company_locations",
    ) == 0


async def test_country_and_subdivision_validation(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = uuid4()
    company_id = uuid4()
    await _insert_tenant(engine, tenant_id)
    await _insert_company(engine, company_id=company_id, tenant_id=tenant_id)
    await _insert_country(engine, code="IN")
    await _insert_country(engine, code="US")
    await _insert_country(engine, code="CA", status="INACTIVE")
    await _insert_subdivision(
        engine,
        country_code="IN",
        code="IN-UP",
    )
    await _insert_subdivision(
        engine,
        country_code="US",
        code="US-CA",
    )
    await _insert_subdivision(
        engine,
        country_code="IN",
        code="IN-DL",
        status="INACTIVE",
    )

    cases = [
        (_location_payload(country_code="ZZ"), 422),
        (_location_payload(country_code="CA"), 409),
        (_location_payload(subdivision_code="IN-MH"), 422),
        (_location_payload(subdivision_code="IN-DL"), 409),
        (_location_payload(subdivision_code="US-CA"), 422),
    ]
    for payload, expected_status in cases:
        response = await client.post(
            f"/companies/{company_id}/locations",
            headers={"X-Tenant-ID": str(tenant_id)},
            json=payload,
        )
        assert response.status_code == expected_status

    valid = await client.post(
        f"/companies/{company_id}/locations",
        headers={"X-Tenant-ID": str(tenant_id)},
        json=_location_payload(subdivision_code="IN-UP"),
    )
    assert valid.status_code == 201
    assert valid.json()["subdivision_code"] == "IN-UP"
    assert await _scalar(
        engine,
        "SELECT count(*) FROM core.company_locations",
    ) == 1


async def test_registered_office_uniqueness_and_repeatable_other_purposes(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = uuid4()
    first_company_id = uuid4()
    second_company_id = uuid4()
    await _insert_tenant(engine, tenant_id)
    await _insert_company(
        engine,
        company_id=first_company_id,
        tenant_id=tenant_id,
    )
    await _insert_company(
        engine,
        company_id=second_company_id,
        tenant_id=tenant_id,
    )
    await _insert_country(engine, code="IN")

    first_registered = await client.post(
        f"/companies/{first_company_id}/locations",
        headers={"X-Tenant-ID": str(tenant_id)},
        json=_location_payload(
            location_name="Registered Corporate",
            is_branch=False,
            is_registered_office=True,
            is_corporate_office=True,
        ),
    )
    second_registered = await client.post(
        f"/companies/{first_company_id}/locations",
        headers={"X-Tenant-ID": str(tenant_id)},
        json=_location_payload(
            location_name="Second Registered",
            is_branch=False,
            is_registered_office=True,
        ),
    )
    other_company_registered = await client.post(
        f"/companies/{second_company_id}/locations",
        headers={"X-Tenant-ID": str(tenant_id)},
        json=_location_payload(
            location_name="Other Company Registered",
            is_branch=False,
            is_registered_office=True,
        ),
    )

    assert first_registered.status_code == 201
    assert second_registered.status_code == 409
    assert other_company_registered.status_code == 201

    for purpose in ("is_branch", "is_warehouse"):
        for index in range(2):
            purpose_flags = {"is_branch": False, purpose: True}
            response = await client.post(
                f"/companies/{first_company_id}/locations",
                headers={"X-Tenant-ID": str(tenant_id)},
                json=_location_payload(
                    location_name=f"{purpose} {index}",
                    **purpose_flags,
                ),
            )
            assert response.status_code == 201

    assert await _scalar(
        engine,
        "SELECT count(*) FROM core.company_locations",
    ) == 6
