import asyncio
import os
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
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


async def _assert_revision_002_removed_only_entity_type(
    database_url: str,
) -> None:
    async with _connection(database_url) as connection:
        entity_types_exists = await connection.scalar(
            text("SELECT to_regclass('core.entity_types') IS NOT NULL")
        )
        tenants_exists = await connection.scalar(
            text("SELECT to_regclass('core.tenants') IS NOT NULL")
        )
        assert not entity_types_exists
        assert tenants_exists


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

    try:
        yield database_url
    finally:
        try:
            command.downgrade(alembic_config, "0001_create_core_tenants")
            asyncio.run(
                _assert_revision_002_removed_only_entity_type(database_url)
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


async def _insert_entity_type(
    database_url: str,
    *,
    country_code: str,
    code: str,
    name: str,
    status: str | None,
    entity_type_id: UUID | None = None,
) -> dict[str, object]:
    columns = ["country_code", "code", "name"]
    values = [":country_code", ":code", ":name"]
    parameters: dict[str, object] = {
        "country_code": country_code,
        "code": code,
        "name": name,
    }

    if status is not None:
        columns.append("status")
        values.append(":status")
        parameters["status"] = status
    if entity_type_id is not None:
        columns.append("id")
        values.append(":entity_type_id")
        parameters["entity_type_id"] = entity_type_id

    statement = text(
        f"""
        INSERT INTO core.entity_types ({", ".join(columns)})
        VALUES ({", ".join(values)})
        RETURNING id, country_code, code, name, status
        """
    )

    async with _connection(database_url) as connection:
        async with connection.begin():
            result = await connection.execute(statement, parameters)
            return dict(result.mappings().one())


async def _assert_insert_rejected(
    database_url: str,
    *,
    country_code: str = "IN",
    code: str = "VALID_CODE",
    name: str = "Valid Name",
    status: str | None = "ACTIVE",
) -> None:
    with pytest.raises(DBAPIError):
        await _insert_entity_type(
            database_url,
            country_code=country_code,
            code=code,
            name=name,
            status=status,
        )


async def _run_entity_type_contract_checks(database_url: str) -> None:
    async with _connection(database_url) as connection:
        table_exists = await connection.scalar(
            text("SELECT to_regclass('core.entity_types') IS NOT NULL")
        )
        assert table_exists

        columns = set(
            (
                await connection.execute(
                    text(
                        """
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_schema = 'core'
                          AND table_name = 'entity_types'
                        """
                    )
                )
            ).scalars()
        )
        assert columns == {"id", "country_code", "code", "name", "status"}

        status_default = await connection.scalar(
            text(
                """
                SELECT column_default
                FROM information_schema.columns
                WHERE table_schema = 'core'
                  AND table_name = 'entity_types'
                  AND column_name = 'status'
                """
            )
        )
        assert status_default is None

    private_limited = await _insert_entity_type(
        database_url,
        country_code="IN",
        code="PRIVATE_LIMITED",
        name="Private Limited Company",
        status="ACTIVE",
    )
    assert isinstance(private_limited["id"], UUID)
    assert private_limited["country_code"] == "IN"
    assert private_limited["code"] == "PRIVATE_LIMITED"

    explicit_id = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    explicit_uuid = await _insert_entity_type(
        database_url,
        country_code="IN",
        code="EXPLICIT_UUID",
        name="Explicit UUID",
        status="ACTIVE",
        entity_type_id=explicit_id,
    )
    assert explicit_uuid["id"] == explicit_id

    inactive = await _insert_entity_type(
        database_url,
        country_code="IN",
        code="PUBLIC_LIMITED",
        name="Public Limited Company",
        status="INACTIVE",
    )
    assert inactive["status"] == "INACTIVE"

    for invalid_country_code in ("in", "I", "IND"):
        await _assert_insert_rejected(
            database_url,
            country_code=invalid_country_code,
            code=f"COUNTRY_{len(invalid_country_code)}",
        )

    for index, invalid_code in enumerate(
        (
            "private_limited",
            "PRIVATE LIMITED",
            "_PRIVATE",
            "PRIVATE_",
            "PRIVATE__LIMITED",
            "",
            "   ",
        )
    ):
        await _assert_insert_rejected(
            database_url,
            code=invalid_code,
            name=f"Invalid Code {index}",
        )

    await _insert_entity_type(
        database_url,
        country_code="IN",
        code="LLP",
        name="Limited Liability Partnership",
        status="ACTIVE",
    )
    await _assert_insert_rejected(
        database_url,
        country_code="IN",
        code="LLP",
        name="Duplicate LLP",
    )

    same_code_other_country = await _insert_entity_type(
        database_url,
        country_code="SG",
        code="LLP",
        name="Limited Liability Partnership",
        status="ACTIVE",
    )
    assert same_code_other_country["code"] == "LLP"

    await _assert_insert_rejected(database_url, code="BLANK_NAME", name="")
    await _assert_insert_rejected(database_url, code="SPACE_NAME", name="   ")

    await _insert_entity_type(
        database_url,
        country_code="IN",
        code="DUPLICATE_NAME_ONE",
        name="Duplicate Display Name",
        status="ACTIVE",
    )
    await _insert_entity_type(
        database_url,
        country_code="IN",
        code="DUPLICATE_NAME_TWO",
        name="Duplicate Display Name",
        status="ACTIVE",
    )

    await _assert_insert_rejected(
        database_url,
        code="INVALID_STATUS",
        status="SUSPENDED",
    )
    await _assert_insert_rejected(
        database_url,
        code="MISSING_STATUS",
        status=None,
    )


def test_entity_type_migration_contract(migrated_database: str) -> None:
    asyncio.run(_run_entity_type_contract_checks(migrated_database))
