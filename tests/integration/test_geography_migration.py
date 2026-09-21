import asyncio
import os
from collections.abc import AsyncIterator, Iterator, Mapping
from contextlib import asynccontextmanager
from datetime import datetime
from uuid import UUID

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


async def _assert_revision_004_removed_only_its_objects(
    database_url: str,
) -> None:
    async with _connection(database_url) as connection:
        countries_exist = await connection.scalar(
            text("SELECT to_regclass('core.countries') IS NOT NULL")
        )
        subdivisions_exist = await connection.scalar(
            text(
                "SELECT to_regclass('core.country_subdivisions') IS NOT NULL"
            )
        )
        assert not countries_exist
        assert not subdivisions_exist

        for table_name in (
            "tenants",
            "entity_types",
            "currencies",
            "organisations",
            "companies",
        ):
            exists = await connection.scalar(
                text(f"SELECT to_regclass('core.{table_name}') IS NOT NULL")
            )
            assert exists

        assert await connection.scalar(
            text("SELECT to_regclass('core.company_code_seq') IS NOT NULL")
        )
        assert await connection.scalar(
            text(
                "SELECT to_regprocedure('core.next_company_code()') IS NOT NULL"
            )
        )


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
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL migration tests")

    parsed_url = make_url(database_url)
    if parsed_url.drivername != "postgresql+asyncpg":
        pytest.fail("TEST_DATABASE_URL must use postgresql+asyncpg")

    asyncio.run(_assert_safe_empty_database(database_url))

    previous_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    get_settings.cache_clear()

    alembic_config = Config("alembic.ini")
    command.upgrade(alembic_config, "0003_core_company_identity")
    command.upgrade(alembic_config, "0004_core_geographic_masters")

    try:
        yield database_url
    finally:
        try:
            command.downgrade(alembic_config, "0003_core_company_identity")
            asyncio.run(
                _assert_revision_004_removed_only_its_objects(database_url)
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


async def _fetch_one(
    database_url: str,
    sql: str,
    parameters: Mapping[str, object] | None = None,
) -> dict[str, object]:
    async with _connection(database_url) as connection:
        async with connection.begin():
            result = await connection.execute(text(sql), parameters or {})
            return dict(result.mappings().one())


async def _execute(
    database_url: str,
    sql: str,
    parameters: Mapping[str, object] | None = None,
) -> None:
    async with _connection(database_url) as connection:
        async with connection.begin():
            await connection.execute(text(sql), parameters or {})


async def _assert_rejected(
    database_url: str,
    sql: str,
    parameters: Mapping[str, object] | None = None,
) -> None:
    with pytest.raises(DBAPIError):
        await _execute(database_url, sql, parameters)


async def _insert_country(
    database_url: str,
    *,
    code: str,
    name: str,
    status: str,
) -> dict[str, object]:
    return await _fetch_one(
        database_url,
        """
        INSERT INTO core.countries (code, name, status)
        VALUES (:code, :name, :status)
        RETURNING *
        """,
        {"code": code, "name": name, "status": status},
    )


async def _insert_subdivision(
    database_url: str,
    *,
    country_code: str,
    code: str,
    name: str,
    subdivision_type: str,
    status: str,
) -> dict[str, object]:
    return await _fetch_one(
        database_url,
        """
        INSERT INTO core.country_subdivisions
            (country_code, code, name, subdivision_type, status)
        VALUES
            (:country_code, :code, :name, :subdivision_type, :status)
        RETURNING *
        """,
        {
            "country_code": country_code,
            "code": code,
            "name": name,
            "subdivision_type": subdivision_type,
            "status": status,
        },
    )


async def _run_migration_shape_checks(database_url: str) -> None:
    async with _connection(database_url) as connection:
        for table_name in ("countries", "country_subdivisions"):
            exists = await connection.scalar(
                text(f"SELECT to_regclass('core.{table_name}') IS NOT NULL")
            )
            assert exists

        constraint_names = set(
            (
                await connection.execute(
                    text(
                        """
                        SELECT constraint_name
                        FROM information_schema.table_constraints
                        WHERE table_schema = 'core'
                          AND table_name IN (
                              'countries',
                              'country_subdivisions'
                          )
                        """
                    )
                )
            ).scalars()
        )
        assert {
            "pk_countries",
            "ck_countries_code_format",
            "ck_countries_name_not_blank",
            "ck_countries_status",
            "pk_country_subdivisions",
            "uq_country_subdivisions_code",
            "fk_country_subdivisions_country_code_countries",
            "ck_country_subdivisions_code_format",
            "ck_country_subdivisions_country_prefix",
            "ck_country_subdivisions_name_not_blank",
            "ck_country_subdivisions_type_format",
            "ck_country_subdivisions_status",
        } <= constraint_names

        index_exists = await connection.scalar(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM pg_indexes
                    WHERE schemaname = 'core'
                      AND tablename = 'country_subdivisions'
                      AND indexname = 'ix_country_subdivisions_country_code'
                )
                """
            )
        )
        assert index_exists

        counts = await connection.execute(
            text(
                """
                SELECT
                    (SELECT count(*) FROM core.countries),
                    (SELECT count(*) FROM core.country_subdivisions)
                """
            )
        )
        assert counts.one() == (0, 0)

        status_defaults = set(
            (
                await connection.execute(
                    text(
                        """
                        SELECT table_name, column_default
                        FROM information_schema.columns
                        WHERE table_schema = 'core'
                          AND table_name IN (
                              'countries',
                              'country_subdivisions'
                          )
                          AND column_name = 'status'
                        """
                    )
                )
            ).all()
        )
        assert status_defaults == {
            ("countries", None),
            ("country_subdivisions", None),
        }


def test_migration_creates_geographic_reference_masters(
    migrated_database: str,
) -> None:
    asyncio.run(_run_migration_shape_checks(migrated_database))


async def _run_country_contract_checks(database_url: str) -> None:
    country = await _insert_country(
        database_url,
        code="IN",
        name="India",
        status="ACTIVE",
    )
    assert country["code"] == "IN"
    assert isinstance(country["created_at"], datetime)
    assert country["created_at"].tzinfo is not None

    insert_sql = """
        INSERT INTO core.countries (code, name, status)
        VALUES (:code, :name, :status)
    """
    for parameters in (
        {"code": "in", "name": "Lowercase", "status": "ACTIVE"},
        {"code": "I", "name": "Too Short", "status": "ACTIVE"},
        {"code": "IND", "name": "Too Long", "status": "ACTIVE"},
        {"code": "ZZ", "name": "   ", "status": "ACTIVE"},
        {"code": "XY", "name": "Bad Status", "status": "DELETED"},
    ):
        await _assert_rejected(database_url, insert_sql, parameters)

    await _insert_country(
        database_url,
        code="US",
        name="United States",
        status="ACTIVE",
    )
    inactive = await _insert_country(
        database_url,
        code="CA",
        name="Canada",
        status="INACTIVE",
    )
    assert inactive["status"] == "INACTIVE"


def test_country_contract(migrated_database: str) -> None:
    asyncio.run(_run_country_contract_checks(migrated_database))


async def _run_country_subdivision_contract_checks(database_url: str) -> None:
    subdivision = await _insert_subdivision(
        database_url,
        country_code="IN",
        code="IN-UP",
        name="Uttar Pradesh",
        subdivision_type="STATE",
        status="ACTIVE",
    )
    assert isinstance(subdivision["id"], UUID)
    assert subdivision["country_code"] == "IN"
    assert subdivision["code"] == "IN-UP"

    await _insert_subdivision(
        database_url,
        country_code="IN",
        code="IN-DL",
        name="Delhi",
        subdivision_type="UNION_TERRITORY",
        status="ACTIVE",
    )
    await _insert_subdivision(
        database_url,
        country_code="US",
        code="US-CA",
        name="California",
        subdivision_type="STATE",
        status="ACTIVE",
    )
    inactive = await _insert_subdivision(
        database_url,
        country_code="IN",
        code="IN-MH",
        name="Maharashtra",
        subdivision_type="STATE",
        status="INACTIVE",
    )
    assert inactive["status"] == "INACTIVE"

    await _assert_rejected(
        database_url,
        """
        INSERT INTO core.country_subdivisions
            (country_code, code, name, subdivision_type, status)
        VALUES ('ZZ', 'ZZ-AA', 'Missing Country', 'REGION', 'ACTIVE')
        """,
    )

    for index, invalid_code in enumerate(
        ("in-UP", "IN_UP", "IN-", "IN-ABCD", "IN-UP!")
    ):
        await _assert_rejected(
            database_url,
            """
            INSERT INTO core.country_subdivisions
                (country_code, code, name, subdivision_type, status)
            VALUES ('IN', :code, :name, 'STATE', 'ACTIVE')
            """,
            {"code": invalid_code, "name": f"Invalid Code {index}"},
        )

    await _assert_rejected(
        database_url,
        """
        INSERT INTO core.country_subdivisions
            (country_code, code, name, subdivision_type, status)
        VALUES ('IN', 'US-NY', 'Prefix Mismatch', 'STATE', 'ACTIVE')
        """,
    )
    await _assert_rejected(
        database_url,
        """
        INSERT INTO core.country_subdivisions
            (country_code, code, name, subdivision_type, status)
        VALUES ('IN', 'IN-KA', '   ', 'STATE', 'ACTIVE')
        """,
    )

    for index, invalid_type in enumerate(
        ("state", "UNION TERRITORY", "_STATE", "STATE_", "STATE__AREA")
    ):
        await _assert_rejected(
            database_url,
            """
            INSERT INTO core.country_subdivisions
                (country_code, code, name, subdivision_type, status)
            VALUES ('IN', :code, :name, :subdivision_type, 'ACTIVE')
            """,
            {
                "code": f"IN-{index + 1}",
                "name": f"Invalid Type {index}",
                "subdivision_type": invalid_type,
            },
        )

    await _assert_rejected(
        database_url,
        """
        INSERT INTO core.country_subdivisions
            (country_code, code, name, subdivision_type, status)
        VALUES ('IN', 'IN-KA', 'Bad Status', 'STATE', 'DELETED')
        """,
    )
    await _assert_rejected(
        database_url,
        """
        INSERT INTO core.country_subdivisions
            (country_code, code, name, subdivision_type, status)
        VALUES ('IN', 'IN-UP', 'Duplicate Code', 'STATE', 'ACTIVE')
        """,
    )
    await _assert_rejected(
        database_url,
        "DELETE FROM core.countries WHERE code = 'IN'",
    )


def test_country_subdivision_contract(migrated_database: str) -> None:
    asyncio.run(_run_country_subdivision_contract_checks(migrated_database))
