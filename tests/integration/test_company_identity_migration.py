import asyncio
import os
import re
from collections.abc import AsyncIterator, Iterator, Mapping
from contextlib import asynccontextmanager
from datetime import datetime
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


async def _assert_revision_003_removed_only_its_objects(
    database_url: str,
) -> None:
    async with _connection(database_url) as connection:
        for table_name in ("currencies", "organisations", "companies"):
            exists = await connection.scalar(
                text(f"SELECT to_regclass('core.{table_name}') IS NOT NULL")
            )
            assert not exists

        company_sequence_exists = await connection.scalar(
            text("SELECT to_regclass('core.company_code_seq') IS NOT NULL")
        )
        company_function_exists = await connection.scalar(
            text(
                "SELECT to_regprocedure('core.next_company_code()') IS NOT NULL"
            )
        )
        tenants_exist = await connection.scalar(
            text("SELECT to_regclass('core.tenants') IS NOT NULL")
        )
        entity_types_exist = await connection.scalar(
            text("SELECT to_regclass('core.entity_types') IS NOT NULL")
        )

        assert not company_sequence_exists
        assert not company_function_exists
        assert tenants_exist
        assert entity_types_exist


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
    command.upgrade(alembic_config, "0002_create_core_entity_types")
    command.upgrade(alembic_config, "0003_core_company_identity")

    try:
        yield database_url
    finally:
        try:
            command.downgrade(alembic_config, "0002_create_core_entity_types")
            asyncio.run(
                _assert_revision_003_removed_only_its_objects(database_url)
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


async def _insert_tenant(
    database_url: str,
    *,
    tenant_id: UUID,
    name: str,
) -> None:
    await _execute(
        database_url,
        """
        INSERT INTO core.tenants (id, name, status)
        VALUES (:tenant_id, :name, 'ACTIVE')
        """,
        {"tenant_id": tenant_id, "name": name},
    )


async def _insert_company(
    database_url: str,
    *,
    tenant_id: UUID,
    legal_name: str,
    status: str,
    **optional_values: object,
) -> dict[str, object]:
    columns = ["tenant_id", "legal_name", "status", *optional_values.keys()]
    values = [f":{column}" for column in columns]
    parameters: dict[str, object] = {
        "tenant_id": tenant_id,
        "legal_name": legal_name,
        "status": status,
        **optional_values,
    }
    return await _fetch_one(
        database_url,
        f"""
        INSERT INTO core.companies ({", ".join(columns)})
        VALUES ({", ".join(values)})
        RETURNING *
        """,
        parameters,
    )


async def _run_migration_shape_checks(database_url: str) -> None:
    async with _connection(database_url) as connection:
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
        assert await connection.scalar(text("SELECT count(*) FROM core.currencies")) == 0


def test_migration_creates_company_identity_foundation(
    migrated_database: str,
) -> None:
    asyncio.run(_run_migration_shape_checks(migrated_database))


async def _run_currency_contract_checks(database_url: str) -> None:
    currency = await _fetch_one(
        database_url,
        """
        INSERT INTO core.currencies (code, name, symbol, minor_units, status)
        VALUES ('INR', 'Indian Rupee', '₹', 2, 'ACTIVE')
        RETURNING *
        """,
    )
    assert currency["code"] == "INR"
    assert isinstance(currency["created_at"], datetime)
    assert currency["created_at"].tzinfo is not None

    invalid_currency_sql = """
        INSERT INTO core.currencies (code, name, minor_units, status)
        VALUES (:code, :name, :minor_units, :status)
    """
    for code in ("inr", "IN", "INRR"):
        await _assert_rejected(
            database_url,
            invalid_currency_sql,
            {
                "code": code,
                "name": f"Invalid {code}",
                "minor_units": 2,
                "status": "ACTIVE",
            },
        )

    for parameters in (
        {"code": "AAA", "name": "   ", "minor_units": 2, "status": "ACTIVE"},
        {"code": "AAB", "name": "Blank Symbol", "minor_units": 2, "status": "ACTIVE"},
        {"code": "AAC", "name": "Low Units", "minor_units": -1, "status": "ACTIVE"},
        {"code": "AAD", "name": "High Units", "minor_units": 5, "status": "ACTIVE"},
        {"code": "AAE", "name": "Bad Status", "minor_units": 2, "status": "DELETED"},
    ):
        sql = invalid_currency_sql
        if parameters["code"] == "AAB":
            sql = """
                INSERT INTO core.currencies
                    (code, name, symbol, minor_units, status)
                VALUES (:code, :name, '   ', :minor_units, :status)
            """
        await _assert_rejected(database_url, sql, parameters)

    async with _connection(database_url) as connection:
        defaults = dict(
            (
                await connection.execute(
                    text(
                        """
                        SELECT column_name, column_default
                        FROM information_schema.columns
                        WHERE table_schema = 'core'
                          AND table_name = 'currencies'
                          AND column_name IN ('minor_units', 'status')
                        """
                    )
                )
            ).all()
        )
        assert defaults == {"minor_units": None, "status": None}


def test_currency_contract(migrated_database: str) -> None:
    asyncio.run(_run_currency_contract_checks(migrated_database))


async def _run_organisation_contract_checks(database_url: str) -> None:
    first_tenant_id = uuid4()
    second_tenant_id = uuid4()
    await _insert_tenant(
        database_url,
        tenant_id=first_tenant_id,
        name="Organisation Tenant One",
    )
    await _insert_tenant(
        database_url,
        tenant_id=second_tenant_id,
        name="Organisation Tenant Two",
    )

    insert_sql = """
        INSERT INTO core.organisations (tenant_id, name, status)
        VALUES (:tenant_id, :name, :status)
        RETURNING id
    """
    first = await _fetch_one(
        database_url,
        insert_sql,
        {"tenant_id": first_tenant_id, "name": "Shared Name", "status": "ACTIVE"},
    )
    assert isinstance(first["id"], UUID)

    await _assert_rejected(
        database_url,
        insert_sql,
        {"tenant_id": first_tenant_id, "name": "Shared Name", "status": "ACTIVE"},
    )
    await _fetch_one(
        database_url,
        insert_sql,
        {"tenant_id": second_tenant_id, "name": "Shared Name", "status": "ACTIVE"},
    )
    await _assert_rejected(
        database_url,
        insert_sql,
        {"tenant_id": first_tenant_id, "name": "   ", "status": "ACTIVE"},
    )
    await _assert_rejected(
        database_url,
        insert_sql,
        {"tenant_id": first_tenant_id, "name": "Bad Status", "status": "SUSPENDED"},
    )
    await _assert_rejected(
        database_url,
        insert_sql,
        {"tenant_id": uuid4(), "name": "Missing Tenant", "status": "ACTIVE"},
    )


def test_organisation_contract(migrated_database: str) -> None:
    asyncio.run(_run_organisation_contract_checks(migrated_database))


async def _run_company_contract_checks(database_url: str) -> None:
    first_tenant_id = uuid4()
    second_tenant_id = uuid4()
    await _insert_tenant(
        database_url,
        tenant_id=first_tenant_id,
        name="Company Tenant One",
    )
    await _insert_tenant(
        database_url,
        tenant_id=second_tenant_id,
        name="Company Tenant Two",
    )

    organisation = await _fetch_one(
        database_url,
        """
        INSERT INTO core.organisations (tenant_id, name, status)
        VALUES (:tenant_id, 'Company Group', 'ACTIVE')
        RETURNING id
        """,
        {"tenant_id": first_tenant_id},
    )
    organisation_id = organisation["id"]

    entity_type_id = uuid4()
    await _execute(
        database_url,
        """
        INSERT INTO core.entity_types (id, country_code, code, name, status)
        VALUES (:id, 'IN', 'COMPANY_TEST_TYPE', 'Company Test Type', 'ACTIVE')
        """,
        {"id": entity_type_id},
    )
    await _execute(
        database_url,
        """
        INSERT INTO core.currencies (code, name, minor_units, status)
        VALUES ('USD', 'US Dollar', 2, 'ACTIVE')
        """,
    )

    first = await _insert_company(
        database_url,
        tenant_id=first_tenant_id,
        legal_name="Duplicate Legal Name",
        status="DRAFT",
    )
    second = await _insert_company(
        database_url,
        tenant_id=first_tenant_id,
        legal_name="Duplicate Legal Name",
        status="DRAFT",
    )

    assert isinstance(first["id"], UUID)
    assert re.fullmatch(r"COM\d{6,}", str(first["company_code"]))
    assert re.fullmatch(r"COM\d{6,}", str(second["company_code"]))
    assert first["company_code"] != second["company_code"]
    assert int(str(second["company_code"])[3:]) > int(
        str(first["company_code"])[3:]
    )
    assert first["organisation_id"] is None
    assert first["entity_type_id"] is None
    assert first["country_code"] is None
    assert first["base_timezone"] is None
    assert first["base_currency_code"] is None
    assert first["business_nature"] is None

    await _execute(
        database_url,
        "SELECT setval('core.company_code_seq', 999998, true)",
    )
    six_digit_code = await _insert_company(
        database_url,
        tenant_id=first_tenant_id,
        legal_name="Six Digit Company Code",
        status="DRAFT",
    )
    seven_digit_code = await _insert_company(
        database_url,
        tenant_id=first_tenant_id,
        legal_name="Seven Digit Company Code",
        status="DRAFT",
    )
    assert six_digit_code["company_code"] == "COM999999"
    assert seven_digit_code["company_code"] == "COM1000000"

    complete_draft = await _insert_company(
        database_url,
        tenant_id=first_tenant_id,
        legal_name="Complete Draft",
        status="DRAFT",
        organisation_id=organisation_id,
        entity_type_id=entity_type_id,
        country_code="IN",
        display_name="Complete",
        email="accounts@example.test",
        phone="+91 1234567890",
        website="https://example.test",
        base_timezone="Asia/Kolkata",
        base_currency_code="USD",
        business_nature="BOTH",
    )
    assert complete_draft["organisation_id"] == organisation_id
    assert complete_draft["entity_type_id"] == entity_type_id
    assert complete_draft["base_currency_code"] == "USD"

    await _assert_rejected(
        database_url,
        """
        INSERT INTO core.companies
            (tenant_id, organisation_id, legal_name, status)
        VALUES (:tenant_id, :organisation_id, 'Cross Tenant', 'DRAFT')
        """,
        {
            "tenant_id": second_tenant_id,
            "organisation_id": organisation_id,
        },
    )

    for column, value in (
        ("status", "SUSPENDED"),
        ("business_nature", "CONSULTING"),
        ("country_code", "in"),
        ("country_code", "IND"),
        ("display_name", "   "),
        ("email", "   "),
        ("phone", "   "),
        ("website", "   "),
        ("base_timezone", "   "),
    ):
        values: dict[str, object] = {column: value}
        if column == "status":
            await _assert_rejected(
                database_url,
                """
                INSERT INTO core.companies (tenant_id, legal_name, status)
                VALUES (:tenant_id, 'Invalid Status', :value)
                """,
                {"tenant_id": first_tenant_id, "value": value},
            )
        else:
            await _assert_rejected(
                database_url,
                f"""
                INSERT INTO core.companies
                    (tenant_id, legal_name, status, {column})
                VALUES (:tenant_id, :legal_name, 'DRAFT', :value)
                """,
                {
                    "tenant_id": first_tenant_id,
                    "legal_name": f"Invalid {column} {value}",
                    "value": values[column],
                },
            )

    await _assert_rejected(
        database_url,
        """
        INSERT INTO core.companies
            (tenant_id, legal_name, status, base_currency_code)
        VALUES (:tenant_id, 'Missing Currency', 'DRAFT', 'ZZZ')
        """,
        {"tenant_id": first_tenant_id},
    )
    await _assert_rejected(
        database_url,
        """
        INSERT INTO core.companies
            (tenant_id, legal_name, status, entity_type_id)
        VALUES (:tenant_id, 'Missing Entity Type', 'DRAFT', :entity_type_id)
        """,
        {"tenant_id": first_tenant_id, "entity_type_id": uuid4()},
    )

    await _assert_rejected(
        database_url,
        "DELETE FROM core.organisations WHERE id = :organisation_id",
        {"organisation_id": organisation_id},
    )
    await _assert_rejected(
        database_url,
        "DELETE FROM core.currencies WHERE code = 'USD'",
    )
    await _assert_rejected(
        database_url,
        "DELETE FROM core.entity_types WHERE id = :entity_type_id",
        {"entity_type_id": entity_type_id},
    )
    await _assert_rejected(
        database_url,
        "DELETE FROM core.tenants WHERE id = :tenant_id",
        {"tenant_id": first_tenant_id},
    )


def test_company_contract(migrated_database: str) -> None:
    asyncio.run(_run_company_contract_checks(migrated_database))
