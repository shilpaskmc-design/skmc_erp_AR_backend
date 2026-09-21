import asyncio
import os
from collections.abc import AsyncIterator, Iterator, Mapping
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from skmc_erp.config import get_settings


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


async def _assert_revision_005_removed_only_its_objects(
    database_url: str,
) -> None:
    async with _connection(database_url) as connection:
        assert not await connection.scalar(
            text("SELECT to_regclass('core.company_locations') IS NOT NULL")
        )
        supporting_constraint_exists = await connection.scalar(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname =
                        'uq_country_subdivisions_country_code_code'
                )
                """
            )
        )
        assert not supporting_constraint_exists

        for table_name in (
            "tenants",
            "entity_types",
            "currencies",
            "organisations",
            "companies",
            "countries",
            "country_subdivisions",
        ):
            assert await connection.scalar(
                text(f"SELECT to_regclass('core.{table_name}') IS NOT NULL")
            )


async def _assert_all_migrations_removed(database_url: str) -> None:
    async with _connection(database_url) as connection:
        assert not await connection.scalar(
            text("SELECT to_regnamespace('core') IS NOT NULL")
        )


@pytest.fixture(scope="module")
def migrated_database() -> Iterator[str]:
    database_url = os.getenv("TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL migration tests")

    if make_url(database_url).drivername != "postgresql+asyncpg":
        pytest.fail("TEST_DATABASE_URL must use postgresql+asyncpg")

    asyncio.run(_assert_safe_empty_database(database_url))
    previous_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    get_settings.cache_clear()

    alembic_config = Config("alembic.ini")
    command.upgrade(alembic_config, "0004_core_geographic_masters")
    command.upgrade(alembic_config, "0005_core_company_locations")

    try:
        yield database_url
    finally:
        try:
            command.downgrade(alembic_config, "0004_core_geographic_masters")
            asyncio.run(
                _assert_revision_005_removed_only_its_objects(database_url)
            )
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


async def _execute(
    database_url: str,
    sql: str,
    parameters: Mapping[str, object] | None = None,
) -> None:
    async with _connection(database_url) as connection:
        async with connection.begin():
            await connection.execute(text(sql), parameters or {})


async def _fetch_one(
    database_url: str,
    sql: str,
    parameters: Mapping[str, object] | None = None,
) -> dict[str, object]:
    async with _connection(database_url) as connection:
        async with connection.begin():
            result = await connection.execute(text(sql), parameters or {})
            return dict(result.mappings().one())


async def _assert_rejected(
    database_url: str,
    sql: str,
    parameters: Mapping[str, object] | None = None,
) -> None:
    with pytest.raises(DBAPIError):
        await _execute(database_url, sql, parameters)


async def _insert_location(
    database_url: str,
    *,
    company_id: UUID,
    name: str,
    country_code: str = "IN",
    subdivision_code: str | None = None,
    status: str = "ACTIVE",
    **purposes: object,
) -> dict[str, object]:
    columns = [
        "company_id",
        "location_name",
        "address_line_1",
        "city",
        "country_code",
        "subdivision_code",
        "status",
        *purposes.keys(),
    ]
    parameters: dict[str, object] = {
        "company_id": company_id,
        "location_name": name,
        "address_line_1": "Address Line",
        "city": "City",
        "country_code": country_code,
        "subdivision_code": subdivision_code,
        "status": status,
        **purposes,
    }
    return await _fetch_one(
        database_url,
        f"""
        INSERT INTO core.company_locations ({", ".join(columns)})
        VALUES ({", ".join(f":{column}" for column in columns)})
        RETURNING *
        """,
        parameters,
    )


async def _prepare_reference_data(database_url: str) -> tuple[UUID, UUID]:
    tenant_id = uuid4()
    first_company_id = uuid4()
    second_company_id = uuid4()
    await _execute(
        database_url,
        """
        INSERT INTO core.tenants (id, name, status)
        VALUES (:id, 'Location Tenant', 'ACTIVE')
        """,
        {"id": tenant_id},
    )
    for company_id, name in (
        (first_company_id, "First Company"),
        (second_company_id, "Second Company"),
    ):
        await _execute(
            database_url,
            """
            INSERT INTO core.companies (id, tenant_id, legal_name, status)
            VALUES (:id, :tenant_id, :name, 'DRAFT')
            """,
            {"id": company_id, "tenant_id": tenant_id, "name": name},
        )
    for code, name in (("IN", "India"), ("US", "United States")):
        await _execute(
            database_url,
            """
            INSERT INTO core.countries (code, name, status)
            VALUES (:code, :name, 'ACTIVE')
            """,
            {"code": code, "name": name},
        )
    for country_code, code, name in (
        ("IN", "IN-UP", "Uttar Pradesh"),
        ("US", "US-CA", "California"),
    ):
        await _execute(
            database_url,
            """
            INSERT INTO core.country_subdivisions
                (country_code, code, name, subdivision_type, status)
            VALUES (:country_code, :code, :name, 'STATE', 'ACTIVE')
            """,
            {"country_code": country_code, "code": code, "name": name},
        )
    return first_company_id, second_company_id


async def _run_company_location_contract_checks(database_url: str) -> None:
    async with _connection(database_url) as connection:
        assert await connection.scalar(
            text("SELECT to_regclass('core.company_locations') IS NOT NULL")
        )
        index_definition = await connection.scalar(
            text(
                """
                SELECT indexdef
                FROM pg_indexes
                WHERE schemaname = 'core'
                  AND tablename = 'company_locations'
                  AND indexname =
                      'uq_company_locations_active_registered_office'
                """
            )
        )
        assert "UNIQUE INDEX" in index_definition
        assert "status" in index_definition
        assert "is_registered_office" in index_definition

    first_company_id, second_company_id = await _prepare_reference_data(
        database_url
    )
    registered = await _insert_location(
        database_url,
        company_id=first_company_id,
        name="Registered and Corporate",
        subdivision_code="IN-UP",
        is_registered_office=True,
        is_corporate_office=True,
    )
    assert isinstance(registered["id"], UUID)
    assert registered["is_registered_office"] is True
    assert registered["is_corporate_office"] is True

    await _assert_rejected(
        database_url,
        """
        INSERT INTO core.company_locations
            (company_id, location_name, address_line_1, city,
             country_code, status)
        VALUES
            (:company_id, 'No Purpose', 'Address', 'City', 'IN', 'ACTIVE')
        """,
        {"company_id": first_company_id},
    )
    await _assert_rejected(
        database_url,
        """
        INSERT INTO core.company_locations
            (company_id, location_name, address_line_1, city,
             country_code, is_branch, status)
        VALUES
            (:company_id, 'Missing Country', 'Address', 'City',
             'ZZ', true, 'ACTIVE')
        """,
        {"company_id": first_company_id},
    )
    await _assert_rejected(
        database_url,
        """
        INSERT INTO core.company_locations
            (company_id, location_name, address_line_1, city,
             country_code, subdivision_code, is_branch, status)
        VALUES
            (:company_id, 'Missing Subdivision', 'Address', 'City',
             'IN', 'IN-MH', true, 'ACTIVE')
        """,
        {"company_id": first_company_id},
    )
    await _assert_rejected(
        database_url,
        """
        INSERT INTO core.company_locations
            (company_id, location_name, address_line_1, city,
             country_code, subdivision_code, is_branch, status)
        VALUES
            (:company_id, 'Mismatch', 'Address', 'City',
             'IN', 'US-CA', true, 'ACTIVE')
        """,
        {"company_id": first_company_id},
    )
    await _assert_rejected(
        database_url,
        """
        INSERT INTO core.company_locations
            (company_id, location_name, address_line_1, city,
             country_code, is_registered_office, status)
        VALUES
            (:company_id, 'Second Registered', 'Address', 'City',
             'IN', true, 'ACTIVE')
        """,
        {"company_id": first_company_id},
    )

    await _insert_location(
        database_url,
        company_id=first_company_id,
        name="Historical Registered",
        status="INACTIVE",
        is_registered_office=True,
    )
    await _insert_location(
        database_url,
        company_id=second_company_id,
        name="Other Company Registered",
        is_registered_office=True,
    )
    for index in range(2):
        await _insert_location(
            database_url,
            company_id=first_company_id,
            name=f"Branch {index}",
            is_branch=True,
        )
        await _insert_location(
            database_url,
            company_id=first_company_id,
            name=f"Warehouse {index}",
            is_warehouse=True,
        )


def test_company_location_migration_contract(
    migrated_database: str,
) -> None:
    asyncio.run(_run_company_location_contract_checks(migrated_database))
