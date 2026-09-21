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

        version_table_exists = await connection.scalar(
            text("SELECT to_regclass('public.alembic_version') IS NOT NULL")
        )
        if version_table_exists:
            version_count = await connection.scalar(
                text("SELECT count(*) FROM public.alembic_version")
            )
            if version_count:
                pytest.fail("TEST_DATABASE_URL already has an applied Alembic revision")


async def _assert_revision_006_removed_only_its_objects(
    database_url: str,
) -> None:
    async with _connection(database_url) as connection:
        for table_name in ("company_fiscal_settings", "financial_years"):
            assert not await connection.scalar(
                text(f"SELECT to_regclass('core.{table_name}') IS NOT NULL")
            )
        for table_name in ("companies", "company_locations", "countries"):
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
    command.upgrade(alembic_config, "0005_core_company_locations")
    command.upgrade(alembic_config, "0006_core_financial_years")

    try:
        yield database_url
    finally:
        try:
            command.downgrade(alembic_config, "0005_core_company_locations")
            asyncio.run(
                _assert_revision_006_removed_only_its_objects(database_url)
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


async def _insert_company(
    database_url: str,
    *,
    company_id: UUID,
    tenant_id: UUID,
    name: str,
) -> None:
    await _execute(
        database_url,
        """
        INSERT INTO core.companies (id, tenant_id, legal_name, status)
        VALUES (:id, :tenant_id, :name, 'DRAFT')
        """,
        {"id": company_id, "tenant_id": tenant_id, "name": name},
    )


async def _run_financial_year_contract_checks(database_url: str) -> None:
    async with _connection(database_url) as connection:
        for table_name in ("company_fiscal_settings", "financial_years"):
            assert await connection.scalar(
                text(f"SELECT to_regclass('core.{table_name}') IS NOT NULL")
            )
        assert await connection.scalar(
            text(
                """
                SELECT EXISTS (
                    SELECT 1 FROM pg_extension WHERE extname = 'btree_gist'
                )
                """
            )
        )
        assert await connection.scalar(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname = 'ex_financial_years_company_date_overlap'
                      AND contype = 'x'
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
        VALUES (:id, 'Fiscal Tenant', 'ACTIVE')
        """,
        {"id": tenant_id},
    )
    await _insert_company(
        database_url,
        company_id=first_company_id,
        tenant_id=tenant_id,
        name="First Fiscal Company",
    )
    await _insert_company(
        database_url,
        company_id=second_company_id,
        tenant_id=tenant_id,
        name="Second Fiscal Company",
    )

    settings_sql = """
        INSERT INTO core.company_fiscal_settings
            (company_id, fiscal_year_pattern, start_month, start_day)
        VALUES (:company_id, :pattern, :month, :day)
    """
    await _execute(
        database_url,
        settings_sql,
        {
            "company_id": first_company_id,
            "pattern": "CUSTOM",
            "month": 2,
            "day": 28,
        },
    )
    for month, day in ((2, 29), (4, 31)):
        await _assert_rejected(
            database_url,
            """
            UPDATE core.company_fiscal_settings
            SET start_month = :month, start_day = :day
            WHERE company_id = :company_id
            """,
            {"company_id": first_company_id, "month": month, "day": day},
        )
    await _assert_rejected(
        database_url,
        settings_sql,
        {
            "company_id": second_company_id,
            "pattern": "APR_MAR",
            "month": 4,
            "day": 2,
        },
    )

    one_day_transition = await _fetch_one(
        database_url,
        """
        INSERT INTO core.financial_years
            (company_id, start_date, end_date, display_code,
             is_transition, status)
        VALUES
            (:company_id, DATE '2025-03-31', DATE '2025-03-31',
             'TRANSITION-2025', true, 'DRAFT')
        RETURNING *
        """,
        {"company_id": first_company_id},
    )
    assert one_day_transition["is_transition"] is True

    await _execute(
        database_url,
        """
        INSERT INTO core.financial_years
            (company_id, start_date, end_date, display_code, status)
        VALUES
            (:company_id, DATE '2025-04-01', DATE '2026-03-31',
             'FY2025-26', 'CLOSED')
        """,
        {"company_id": first_company_id},
    )
    await _execute(
        database_url,
        """
        INSERT INTO core.financial_years
            (company_id, start_date, end_date, display_code, status)
        VALUES
            (:company_id, DATE '2026-04-01', DATE '2027-03-31',
             'FY2026-27', 'DRAFT')
        """,
        {"company_id": first_company_id},
    )
    await _assert_rejected(
        database_url,
        """
        INSERT INTO core.financial_years
            (company_id, start_date, end_date, display_code, status)
        VALUES
            (:company_id, DATE '2026-01-01', DATE '2026-12-31',
             'OVERLAP', 'OPEN')
        """,
        {"company_id": first_company_id},
    )
    await _execute(
        database_url,
        """
        INSERT INTO core.financial_years
            (company_id, start_date, end_date, display_code, status)
        VALUES
            (:company_id, DATE '2026-04-01', DATE '2027-03-31',
             'FY2026-27', 'DRAFT')
        """,
        {"company_id": second_company_id},
    )


def test_financial_year_migration_contract(migrated_database: str) -> None:
    asyncio.run(_run_financial_year_contract_checks(migrated_database))
