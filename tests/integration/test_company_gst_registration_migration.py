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


async def _assert_revision_007_removed_only_its_objects(
    database_url: str,
) -> None:
    async with _connection(database_url) as connection:
        for table_name in (
            "gst_registration_types",
            "company_gst_registrations",
        ):
            assert not await connection.scalar(
                text(f"SELECT to_regclass('core.{table_name}') IS NOT NULL")
            )
        assert await connection.scalar(
            text("SELECT to_regclass('core.company_locations') IS NOT NULL")
        )
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
        assert await connection.scalar(
            text("SELECT version_num FROM public.alembic_version")
        ) == "0006_core_financial_years"
        for table_name, column_name in (
            ("country_subdivisions", "gst_state_code"),
            ("company_locations", "gst_registration_id"),
        ):
            assert not await connection.scalar(
                text(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema = 'core'
                          AND table_name = :table_name
                          AND column_name = :column_name
                    )
                    """
                ),
                {"table_name": table_name, "column_name": column_name},
            )


async def _restore_legacy_version_column(database_url: str) -> None:
    async with _connection(database_url) as connection:
        async with connection.begin():
            assert await connection.scalar(
                text("SELECT version_num FROM public.alembic_version")
            ) == "0006_core_financial_years"
            assert not await connection.scalar(
                text(
                    """
                    SELECT to_regclass(
                        'core.company_gst_registrations'
                    ) IS NOT NULL
                    """
                )
            )
            await connection.execute(
                text(
                    """
                    ALTER TABLE public.alembic_version
                    ALTER COLUMN version_num TYPE VARCHAR(32)
                    """
                )
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
    command.upgrade(alembic_config, "0006_core_financial_years")
    asyncio.run(_restore_legacy_version_column(database_url))
    command.upgrade(alembic_config, "0007_core_company_gst_registrations")

    try:
        yield database_url
    finally:
        try:
            command.downgrade(alembic_config, "0006_core_financial_years")
            asyncio.run(
                _assert_revision_007_removed_only_its_objects(database_url)
            )
        finally:
            try:
                command.downgrade(alembic_config, "base")
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


async def _run_contract_checks(database_url: str) -> None:
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
        assert await connection.scalar(
            text("SELECT version_num FROM public.alembic_version")
        ) == "0007_core_company_gst_registrations"
        for table_name in (
            "gst_registration_types",
            "company_gst_registrations",
        ):
            assert await connection.scalar(
                text(f"SELECT to_regclass('core.{table_name}') IS NOT NULL")
            )
        assert await connection.scalar(
            text(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = 'core'
                      AND table_name = 'country_subdivisions'
                      AND column_name = 'gst_state_code'
                )
                """
            )
        )
        assert await connection.scalar(
            text(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = 'core'
                      AND table_name = 'company_locations'
                      AND column_name = 'gst_registration_id'
                )
                """
            )
        )

    tenant_id = uuid4()
    first_company_id = uuid4()
    second_company_id = uuid4()
    await _execute(
        database_url,
        """
        INSERT INTO core.tenants (id, name, status)
        VALUES (:id, 'GST Migration Tenant', 'ACTIVE')
        """,
        {"id": tenant_id},
    )
    for company_id, name in (
        (first_company_id, "First GST Company"),
        (second_company_id, "Second GST Company"),
    ):
        await _execute(
            database_url,
            """
            INSERT INTO core.companies
                (id, tenant_id, legal_name, country_code, status)
            VALUES (:id, :tenant_id, :name, 'IN', 'DRAFT')
            """,
            {"id": company_id, "tenant_id": tenant_id, "name": name},
        )
    await _execute(
        database_url,
        """
        INSERT INTO core.countries (code, name, status)
        VALUES ('IN', 'India', 'ACTIVE'), ('US', 'United States', 'ACTIVE')
        """,
    )
    await _execute(
        database_url,
        """
        INSERT INTO core.country_subdivisions
            (country_code, code, name, subdivision_type,
             gst_state_code, status)
        VALUES
            ('IN', 'IN-UP', 'Uttar Pradesh', 'STATE', '09', 'ACTIVE'),
            ('IN', 'IN-MH', 'Maharashtra', 'STATE', '27', 'ACTIVE'),
            ('US', 'US-CA', 'California', 'STATE', NULL, 'ACTIVE')
        """,
    )

    for invalid_code in ("9", "A9", "091"):
        await _assert_rejected(
            database_url,
            """
            INSERT INTO core.country_subdivisions
                (country_code, code, name, subdivision_type,
                 gst_state_code, status)
            VALUES ('IN', :code, 'Invalid GST State', 'STATE',
                    :gst_state_code, 'ACTIVE')
            """,
            {"code": f"IN-{invalid_code}", "gst_state_code": invalid_code},
        )
    await _assert_rejected(
        database_url,
        """
        INSERT INTO core.country_subdivisions
            (country_code, code, name, subdivision_type,
             gst_state_code, status)
        VALUES ('IN', 'IN-DL', 'Delhi', 'STATE', '09', 'ACTIVE')
        """,
    )

    registration_type = await _fetch_one(
        database_url,
        """
        INSERT INTO core.gst_registration_types (code, name, status)
        VALUES ('TEST_TYPE', 'Test Type', 'ACTIVE')
        RETURNING *
        """,
    )
    assert isinstance(registration_type["id"], UUID)

    registration = await _fetch_one(
        database_url,
        """
        INSERT INTO core.company_gst_registrations
            (company_id, gstin, registered_legal_name,
             gst_registration_type_id, subdivision_code,
             valid_from, valid_to, status)
        VALUES
            (:company_id, '09ABCDE1234F1Z5', 'Example Private Limited',
             :type_id, 'IN-UP', DATE '2026-01-01', DATE '2026-12-31',
             'DRAFT')
        RETURNING *
        """,
        {
            "company_id": first_company_id,
            "type_id": registration_type["id"],
        },
    )
    assert isinstance(registration["id"], UUID)
    assert registration["status"] == "DRAFT"

    insert_sql = """
        INSERT INTO core.company_gst_registrations
            (company_id, gstin, registered_legal_name,
             subdivision_code, valid_from, valid_to, status)
        VALUES
            (:company_id, :gstin, :legal_name,
             :subdivision_code, :valid_from, :valid_to, :status)
    """
    invalid_rows = (
        {
            "company_id": first_company_id,
            "gstin": "INVALID",
            "legal_name": None,
            "subdivision_code": "IN-UP",
            "valid_from": None,
            "valid_to": None,
            "status": "DRAFT",
        },
        {
            "company_id": second_company_id,
            "gstin": "09ABCDE1234F1Z5",
            "legal_name": None,
            "subdivision_code": "IN-UP",
            "valid_from": None,
            "valid_to": None,
            "status": "DRAFT",
        },
        {
            "company_id": first_company_id,
            "gstin": "27ABCDE1234F1Z5",
            "legal_name": "   ",
            "subdivision_code": "IN-MH",
            "valid_from": None,
            "valid_to": None,
            "status": "DRAFT",
        },
        {
            "company_id": first_company_id,
            "gstin": "27ABCDE1234F1Z5",
            "legal_name": None,
            "subdivision_code": "IN-MH",
            "valid_from": "2026-12-31",
            "valid_to": "2026-01-01",
            "status": "DRAFT",
        },
        {
            "company_id": first_company_id,
            "gstin": "27ABCDE1234F1Z5",
            "legal_name": None,
            "subdivision_code": "IN-MH",
            "valid_from": None,
            "valid_to": None,
            "status": "CANCELLED",
        },
    )
    for row in invalid_rows:
        await _assert_rejected(database_url, insert_sql, row)

    await _execute(
        database_url,
        insert_sql,
        {
            "company_id": first_company_id,
            "gstin": "09AAAAA0001A1Z5",
            "legal_name": None,
            "subdivision_code": "IN-UP",
            "valid_from": None,
            "valid_to": None,
            "status": "ACTIVE",
        },
    )
    await _assert_rejected(
        database_url,
        insert_sql,
        {
            "company_id": first_company_id,
            "gstin": "09BBBBB0002B1Z5",
            "legal_name": None,
            "subdivision_code": "IN-UP",
            "valid_from": None,
            "valid_to": None,
            "status": "ACTIVE",
        },
    )

    location_sql = """
        INSERT INTO core.company_locations
            (company_id, location_name, address_line_1, city,
             subdivision_code, country_code, is_branch,
             gst_registration_id, status)
        VALUES
            (:company_id, :name, 'Address', 'City',
             :subdivision_code, 'IN', true,
             :gst_registration_id, 'ACTIVE')
    """
    for name in ("First GST Location", "Second GST Location"):
        await _execute(
            database_url,
            location_sql,
            {
                "company_id": first_company_id,
                "name": name,
                "subdivision_code": "IN-UP",
                "gst_registration_id": registration["id"],
            },
        )
    await _assert_rejected(
        database_url,
        location_sql,
        {
            "company_id": second_company_id,
            "name": "Cross Company Location",
            "subdivision_code": "IN-UP",
            "gst_registration_id": registration["id"],
        },
    )
    await _assert_rejected(
        database_url,
        location_sql,
        {
            "company_id": first_company_id,
            "name": "Wrong Jurisdiction Location",
            "subdivision_code": "IN-MH",
            "gst_registration_id": registration["id"],
        },
    )
    await _assert_rejected(
        database_url,
        location_sql,
        {
            "company_id": first_company_id,
            "name": "Missing Jurisdiction Location",
            "subdivision_code": None,
            "gst_registration_id": registration["id"],
        },
    )


def test_company_gst_registration_migration_contract(
    migrated_database: str,
) -> None:
    asyncio.run(_run_contract_checks(migrated_database))
