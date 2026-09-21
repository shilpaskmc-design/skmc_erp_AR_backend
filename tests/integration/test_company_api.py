import asyncio
import os
import re
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
        core_exists = await connection.scalar(
            text("SELECT to_regnamespace('core') IS NOT NULL")
        )
        if core_exists:
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
        core_exists = await connection.scalar(
            text("SELECT to_regnamespace('core') IS NOT NULL")
        )
        assert not core_exists


@pytest.fixture(scope="module")
def migrated_database() -> Iterator[str]:
    database_url = os.getenv("TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL API tests")

    parsed_url = make_url(database_url)
    if parsed_url.drivername != "postgresql+asyncpg":
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

    development_settings = Settings(
        database_url=migrated_database,
        environment="development",
    )
    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_settings] = lambda: development_settings

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        try:
            yield client, test_engine, app
        finally:
            app.dependency_overrides.clear()
            async with test_engine.begin() as connection:
                await connection.execute(
                    text(
                        """
                        TRUNCATE TABLE
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
    *,
    tenant_id: UUID,
    status: str = "ACTIVE",
) -> None:
    await _execute(
        engine,
        """
        INSERT INTO core.tenants (id, name, status)
        VALUES (:tenant_id, :name, :status)
        """,
        {
            "tenant_id": tenant_id,
            "name": f"Tenant {tenant_id}",
            "status": status,
        },
    )


async def _insert_organisation(
    engine: AsyncEngine,
    *,
    organisation_id: UUID,
    tenant_id: UUID,
    status: str = "ACTIVE",
) -> None:
    await _execute(
        engine,
        """
        INSERT INTO core.organisations (id, tenant_id, name, status)
        VALUES (:id, :tenant_id, :name, :status)
        """,
        {
            "id": organisation_id,
            "tenant_id": tenant_id,
            "name": f"Organisation {organisation_id}",
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


async def _insert_entity_type(
    engine: AsyncEngine,
    *,
    entity_type_id: UUID,
    country_code: str,
    status: str = "ACTIVE",
) -> None:
    await _execute(
        engine,
        """
        INSERT INTO core.entity_types
            (id, country_code, code, name, status)
        VALUES
            (:id, :country_code, :code, :name, :status)
        """,
        {
            "id": entity_type_id,
            "country_code": country_code,
            "code": f"TYPE_{entity_type_id.hex.upper()}",
            "name": f"Entity Type {entity_type_id}",
            "status": status,
        },
    )


async def _insert_currency(
    engine: AsyncEngine,
    *,
    code: str,
    status: str = "ACTIVE",
) -> None:
    await _execute(
        engine,
        """
        INSERT INTO core.currencies
            (code, name, minor_units, status)
        VALUES
            (:code, :name, 2, :status)
        """,
        {"code": code, "name": f"Currency {code}", "status": status},
    )


async def test_tenant_header_validation_and_lookup(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, _, _ = api_context

    missing = await client.post("/companies", json={"legal_name": "Example"})
    malformed = await client.post(
        "/companies",
        headers={"X-Tenant-ID": "not-a-uuid"},
        json={"legal_name": "Example"},
    )
    nonexistent = await client.post(
        "/companies",
        headers={"X-Tenant-ID": str(uuid4())},
        json={"legal_name": "Example"},
    )

    assert missing.status_code == 422
    assert malformed.status_code == 422
    assert nonexistent.status_code == 404
    assert nonexistent.json() == {"detail": "Tenant not found"}


async def test_inactive_tenant_and_production_context_are_rejected(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, app = api_context
    inactive_tenant_id = uuid4()
    await _insert_tenant(
        engine,
        tenant_id=inactive_tenant_id,
        status="INACTIVE",
    )

    inactive = await client.post(
        "/companies",
        headers={"X-Tenant-ID": str(inactive_tenant_id)},
        json={"legal_name": "Example"},
    )
    assert inactive.status_code == 409
    assert inactive.json() == {"detail": "Tenant is not active"}

    production_settings = Settings(
        database_url="postgresql+asyncpg://example:example@localhost/example",
        environment="production",
    )
    app.dependency_overrides[get_settings] = lambda: production_settings
    production = await client.post(
        "/companies",
        headers={"X-Tenant-ID": str(inactive_tenant_id)},
        json={"legal_name": "Example"},
    )

    assert production.status_code == 503
    assert production.json() == {
        "detail": "Temporary tenant context is unavailable in production"
    }


async def test_minimal_draft_creation_persists_system_generated_values(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = uuid4()
    await _insert_tenant(engine, tenant_id=tenant_id)

    first = await client.post(
        "/companies",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={"legal_name": "  First Company  "},
    )
    second = await client.post(
        "/companies",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={"legal_name": "Second Company"},
    )

    assert first.status_code == 201
    assert second.status_code == 201
    first_body = first.json()
    second_body = second.json()
    assert UUID(first_body["id"])
    assert first_body["tenant_id"] == str(tenant_id)
    assert first_body["legal_name"] == "First Company"
    assert first_body["status"] == "DRAFT"
    assert re.fullmatch(r"COM\d{6,}", first_body["company_code"])
    assert first_body["company_code"] != second_body["company_code"]
    assert first_body["created_at"]
    assert first_body["updated_at"]
    assert await _scalar(
        engine,
        "SELECT count(*) FROM core.companies WHERE tenant_id = :tenant_id",
        {"tenant_id": tenant_id},
    ) == 2


async def test_active_optional_references_succeed(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = uuid4()
    organisation_id = uuid4()
    entity_type_id = uuid4()
    await _insert_tenant(engine, tenant_id=tenant_id)
    await _insert_organisation(
        engine,
        organisation_id=organisation_id,
        tenant_id=tenant_id,
    )
    await _insert_country(engine, code="IN")
    await _insert_entity_type(
        engine,
        entity_type_id=entity_type_id,
        country_code="IN",
    )
    await _insert_currency(engine, code="INR")

    response = await client.post(
        "/companies",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={
            "legal_name": "Complete Draft",
            "organisation_id": str(organisation_id),
            "entity_type_id": str(entity_type_id),
            "country_code": "IN",
            "base_currency_code": "INR",
            "base_timezone": "Asia/Kolkata",
            "business_nature": "BOTH",
        },
    )

    assert response.status_code == 201
    assert response.json()["organisation_id"] == str(organisation_id)
    assert response.json()["entity_type_id"] == str(entity_type_id)
    assert response.json()["country_code"] == "IN"
    assert response.json()["base_currency_code"] == "INR"
    assert response.json()["base_timezone"] == "Asia/Kolkata"


async def test_organisation_tenant_and_status_rules(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = uuid4()
    other_tenant_id = uuid4()
    cross_tenant_organisation_id = uuid4()
    inactive_organisation_id = uuid4()
    await _insert_tenant(engine, tenant_id=tenant_id)
    await _insert_tenant(engine, tenant_id=other_tenant_id)
    await _insert_organisation(
        engine,
        organisation_id=cross_tenant_organisation_id,
        tenant_id=other_tenant_id,
    )
    await _insert_organisation(
        engine,
        organisation_id=inactive_organisation_id,
        tenant_id=tenant_id,
        status="INACTIVE",
    )

    cross_tenant = await client.post(
        "/companies",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={
            "legal_name": "Cross Tenant",
            "organisation_id": str(cross_tenant_organisation_id),
        },
    )
    inactive = await client.post(
        "/companies",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={
            "legal_name": "Inactive Organisation",
            "organisation_id": str(inactive_organisation_id),
        },
    )

    assert cross_tenant.status_code == 422
    assert inactive.status_code == 409
    assert await _scalar(engine, "SELECT count(*) FROM core.companies") == 0


async def test_missing_references_are_rejected(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = uuid4()
    await _insert_tenant(engine, tenant_id=tenant_id)

    payloads = [
        {"organisation_id": str(uuid4())},
        {"entity_type_id": str(uuid4())},
        {"country_code": "ZZ"},
        {"base_currency_code": "ZZZ"},
    ]
    for index, reference in enumerate(payloads):
        response = await client.post(
            "/companies",
            headers={"X-Tenant-ID": str(tenant_id)},
            json={"legal_name": f"Missing Reference {index}", **reference},
        )
        assert response.status_code == 422

    assert await _scalar(engine, "SELECT count(*) FROM core.companies") == 0


async def test_inactive_references_and_country_mismatch_are_rejected(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = uuid4()
    inactive_entity_type_id = uuid4()
    active_entity_type_id = uuid4()
    await _insert_tenant(engine, tenant_id=tenant_id)
    await _insert_country(engine, code="IN", status="INACTIVE")
    await _insert_country(engine, code="US")
    await _insert_entity_type(
        engine,
        entity_type_id=inactive_entity_type_id,
        country_code="US",
        status="INACTIVE",
    )
    await _insert_entity_type(
        engine,
        entity_type_id=active_entity_type_id,
        country_code="US",
    )
    await _insert_currency(engine, code="INR", status="INACTIVE")

    payloads = [
        ({"entity_type_id": str(inactive_entity_type_id)}, 409),
        ({"country_code": "IN"}, 409),
        ({"base_currency_code": "INR"}, 409),
        (
            {
                "entity_type_id": str(active_entity_type_id),
                "country_code": "IN",
            },
            409,
        ),
    ]
    for index, (reference, expected_status) in enumerate(payloads):
        response = await client.post(
            "/companies",
            headers={"X-Tenant-ID": str(tenant_id)},
            json={"legal_name": f"Rejected Reference {index}", **reference},
        )
        assert response.status_code == expected_status

    await _execute(
        engine,
        "UPDATE core.countries SET status = 'ACTIVE' WHERE code = 'IN'",
    )
    mismatch = await client.post(
        "/companies",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={
            "legal_name": "Country Mismatch",
            "entity_type_id": str(active_entity_type_id),
            "country_code": "IN",
        },
    )
    assert mismatch.status_code == 422
    assert await _scalar(engine, "SELECT count(*) FROM core.companies") == 0
