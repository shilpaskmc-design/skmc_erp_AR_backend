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
        if await connection.scalar(
            text("SELECT to_regclass('public.alembic_version') IS NOT NULL")
        ):
            version_count = await connection.scalar(
                text("SELECT count(*) FROM public.alembic_version")
            )
            if version_count:
                pytest.fail(
                    "TEST_DATABASE_URL already has an applied Alembic revision"
                )


async def _assert_fresh_upgrade_version_storage(database_url: str) -> None:
    async with _connection(database_url) as connection:
        assert await connection.scalar(
            text(
                """
                SELECT character_maximum_length
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'alembic_version'
                  AND column_name = 'version_num'
                """
            )
        ) == 255
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
    asyncio.run(_assert_fresh_upgrade_version_storage(database_url))

    try:
        yield database_url
    finally:
        try:
            command.downgrade(alembic_config, "base")
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
                            core.company_gst_registrations,
                            core.gst_registration_types,
                            core.companies,
                            core.country_subdivisions,
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
    country_code: str | None = "IN",
    status: str = "DRAFT",
) -> None:
    await _execute(
        engine,
        """
        INSERT INTO core.companies
            (id, tenant_id, legal_name, country_code, status)
        VALUES (:id, :tenant_id, :name, :country_code, :status)
        """,
        {
            "id": company_id,
            "tenant_id": tenant_id,
            "name": f"Company {company_id}",
            "country_code": country_code,
            "status": status,
        },
    )


async def _insert_geography(
    engine: AsyncEngine,
    *,
    country_code: str,
    subdivision_code: str,
    gst_state_code: str | None,
    status: str = "ACTIVE",
) -> None:
    if not await _scalar(
        engine,
        "SELECT count(*) FROM core.countries WHERE code = :code",
        {"code": country_code},
    ):
        await _execute(
            engine,
            """
            INSERT INTO core.countries (code, name, status)
            VALUES (:code, :name, 'ACTIVE')
            """,
            {"code": country_code, "name": f"Country {country_code}"},
        )
    await _execute(
        engine,
        """
        INSERT INTO core.country_subdivisions
            (country_code, code, name, subdivision_type,
             gst_state_code, status)
        VALUES
            (:country_code, :code, :name, 'STATE',
             :gst_state_code, :status)
        """,
        {
            "country_code": country_code,
            "code": subdivision_code,
            "name": f"Subdivision {subdivision_code}",
            "gst_state_code": gst_state_code,
            "status": status,
        },
    )


def _payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "gstin": "09ABCDE1234F1Z5",
        "subdivision_code": "IN-UP",
    }
    payload.update(overrides)
    return payload


async def _post(
    client: AsyncClient,
    *,
    tenant_id: UUID,
    company_id: UUID,
    payload: dict[str, object],
):
    return await client.post(
        f"/companies/{company_id}/gst-registrations",
        headers={"X-Tenant-ID": str(tenant_id)},
        json=payload,
    )


async def test_create_draft_registration_and_reject_global_duplicate(
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
    await _insert_geography(
        engine,
        country_code="IN",
        subdivision_code="IN-UP",
        gst_state_code="09",
    )

    created = await _post(
        client,
        tenant_id=tenant_id,
        company_id=first_company_id,
        payload=_payload(
            gstin=" 09abcde1234f1z5 ",
            registered_legal_name=" Example Private Limited ",
        ),
    )
    duplicate = await _post(
        client,
        tenant_id=tenant_id,
        company_id=second_company_id,
        payload=_payload(),
    )

    assert created.status_code == 201
    assert created.json()["company_id"] == str(first_company_id)
    assert created.json()["gstin"] == "09ABCDE1234F1Z5"
    assert created.json()["registered_legal_name"] == "Example Private Limited"
    assert created.json()["gst_registration_type_id"] is None
    assert created.json()["valid_from"] is None
    assert created.json()["valid_to"] is None
    assert created.json()["status"] == "DRAFT"
    assert duplicate.status_code == 409
    assert await _scalar(
        engine,
        "SELECT count(*) FROM core.company_gst_registrations",
    ) == 1


async def test_company_lookup_and_country_rules(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = uuid4()
    other_tenant_id = uuid4()
    cross_tenant_company_id = uuid4()
    inactive_company_id = uuid4()
    foreign_company_id = uuid4()
    await _insert_tenant(engine, tenant_id)
    await _insert_tenant(engine, other_tenant_id)
    await _insert_company(
        engine,
        company_id=cross_tenant_company_id,
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
        company_id=foreign_company_id,
        tenant_id=tenant_id,
        country_code="US",
    )
    await _insert_geography(
        engine,
        country_code="IN",
        subdivision_code="IN-UP",
        gst_state_code="09",
    )

    for company_id in (uuid4(), cross_tenant_company_id):
        response = await _post(
            client,
            tenant_id=tenant_id,
            company_id=company_id,
            payload=_payload(),
        )
        assert response.status_code == 404
        assert response.json() == {"detail": "Company not found"}

    inactive = await _post(
        client,
        tenant_id=tenant_id,
        company_id=inactive_company_id,
        payload=_payload(),
    )
    foreign = await _post(
        client,
        tenant_id=tenant_id,
        company_id=foreign_company_id,
        payload=_payload(),
    )
    assert inactive.status_code == 409
    assert foreign.status_code == 409
    assert await _scalar(
        engine,
        "SELECT count(*) FROM core.company_gst_registrations",
    ) == 0


async def test_subdivision_and_gstin_prefix_validation(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = uuid4()
    company_id = uuid4()
    await _insert_tenant(engine, tenant_id)
    await _insert_company(
        engine,
        company_id=company_id,
        tenant_id=tenant_id,
    )
    await _insert_geography(
        engine,
        country_code="IN",
        subdivision_code="IN-UP",
        gst_state_code="09",
    )
    await _insert_geography(
        engine,
        country_code="IN",
        subdivision_code="IN-MH",
        gst_state_code=None,
    )
    await _insert_geography(
        engine,
        country_code="IN",
        subdivision_code="IN-DL",
        gst_state_code="07",
        status="INACTIVE",
    )
    await _insert_geography(
        engine,
        country_code="US",
        subdivision_code="US-CA",
        gst_state_code="06",
    )

    cases = [
        (_payload(subdivision_code="IN-XX"), 422),
        (_payload(subdivision_code="IN-MH"), 409),
        (_payload(subdivision_code="IN-DL", gstin="07ABCDE1234F1Z5"), 409),
        (_payload(subdivision_code="US-CA", gstin="06ABCDE1234F1Z5"), 422),
        (_payload(gstin="27ABCDE1234F1Z5"), 422),
        (_payload(gstin="invalid"), 422),
        (_payload(registered_legal_name="   "), 422),
        (_payload(valid_from="2026-12-31", valid_to="2026-01-01"), 422),
    ]
    for payload, expected_status in cases:
        response = await _post(
            client,
            tenant_id=tenant_id,
            company_id=company_id,
            payload=payload,
        )
        assert response.status_code == expected_status

    assert await _scalar(
        engine,
        "SELECT count(*) FROM core.company_gst_registrations",
    ) == 0


async def test_optional_registration_type_must_be_active_when_supplied(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = uuid4()
    company_id = uuid4()
    active_type_id = uuid4()
    inactive_type_id = uuid4()
    await _insert_tenant(engine, tenant_id)
    await _insert_company(
        engine,
        company_id=company_id,
        tenant_id=tenant_id,
    )
    await _insert_geography(
        engine,
        country_code="IN",
        subdivision_code="IN-UP",
        gst_state_code="09",
    )
    await _execute(
        engine,
        """
        INSERT INTO core.gst_registration_types (id, code, name, status)
        VALUES
            (:active_id, 'REGULAR_TEST', 'Regular Test', 'ACTIVE'),
            (:inactive_id, 'RETIRED_TEST', 'Retired Test', 'INACTIVE')
        """,
        {"active_id": active_type_id, "inactive_id": inactive_type_id},
    )

    missing = await _post(
        client,
        tenant_id=tenant_id,
        company_id=company_id,
        payload=_payload(gst_registration_type_id=str(uuid4())),
    )
    inactive = await _post(
        client,
        tenant_id=tenant_id,
        company_id=company_id,
        payload=_payload(gst_registration_type_id=str(inactive_type_id)),
    )
    active = await _post(
        client,
        tenant_id=tenant_id,
        company_id=company_id,
        payload=_payload(gst_registration_type_id=str(active_type_id)),
    )

    assert missing.status_code == 422
    assert inactive.status_code == 409
    assert active.status_code == 201
    assert active.json()["gst_registration_type_id"] == str(active_type_id)
