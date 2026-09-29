import asyncio
import os
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
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


async def _assert_empty(database_url: str) -> None:
    async with _connection(database_url) as connection:
        if await connection.scalar(text("SELECT to_regnamespace('core') IS NOT NULL")):
            pytest.fail("TEST_DATABASE_URL must point to an empty database")


@pytest.fixture(scope="module")
def database_url() -> Iterator[str]:
    value = os.getenv("TEST_DATABASE_URL")
    if value is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL migration tests")
    if make_url(value).drivername != "postgresql+asyncpg":
        pytest.fail("TEST_DATABASE_URL must use postgresql+asyncpg")
    asyncio.run(_assert_empty(value))
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = value
    get_settings.cache_clear()
    config = Config("alembic.ini")
    command.upgrade(config, "0033_catalogue_base_gst_nature")
    command.upgrade(config, "0034_company_identifier_foundation")
    try:
        yield value
    finally:
        try:
            command.downgrade(config, "0033_catalogue_base_gst_nature")
            asyncio.run(_assert_identifier_tables_absent(value))
            command.downgrade(config, "base")
        finally:
            if previous is None:
                os.environ.pop("DATABASE_URL", None)
            else:
                os.environ["DATABASE_URL"] = previous
            get_settings.cache_clear()


async def _assert_identifier_tables_absent(database_url: str) -> None:
    async with _connection(database_url) as connection:
        for table in (
            "company_identifier_types",
            "company_identifiers",
            "entity_type_identifier_rules",
        ):
            assert not await connection.scalar(
                text(f"SELECT to_regclass('core.{table}') IS NOT NULL")
            )
        assert await connection.scalar(
            text("SELECT to_regclass('core.companies') IS NOT NULL")
        )


async def _exercise_contract(database_url: str) -> None:
    async with _connection(database_url) as connection:
        async with connection.begin():
            tables = await connection.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'core' AND table_name IN "
                    "('company_identifier_types', 'company_identifiers', "
                    "'entity_type_identifier_rules') ORDER BY table_name"
                )
            )
            assert [row[0] for row in tables] == [
                "company_identifier_types",
                "company_identifiers",
                "entity_type_identifier_rules",
            ]
            await connection.execute(
                text(
                    "INSERT INTO core.countries (code, name, status) "
                    "VALUES ('IN', 'India', 'ACTIVE')"
                )
            )
            pan_type_id = await connection.scalar(
                text(
                    "INSERT INTO core.company_identifier_types "
                    "(country_code, code, name, status) "
                    "VALUES ('IN', 'PAN', 'Permanent Account Number', 'ACTIVE') "
                    "RETURNING id"
                )
            )
            tenant_id = await connection.scalar(
                text(
                    "INSERT INTO core.tenants (name, status) "
                    "VALUES ('Identifiers Tenant', 'ACTIVE') RETURNING id"
                )
            )
            entity_type_id = await connection.scalar(
                text(
                    "INSERT INTO core.entity_types "
                    "(country_code, code, name, status) "
                    "VALUES ('IN', 'PRIVATE_LIMITED', 'Private Limited', 'ACTIVE') "
                    "RETURNING id"
                )
            )
            company_id = await connection.scalar(
                text(
                    "INSERT INTO core.companies "
                    "(tenant_id, legal_name, entity_type_id, country_code, status) "
                    "VALUES (:tenant, 'Identifier Company', :entity, 'IN', 'DRAFT') "
                    "RETURNING id"
                ),
                {"tenant": tenant_id, "entity": entity_type_id},
            )
            await connection.execute(
                text(
                    "INSERT INTO core.company_identifiers "
                    "(company_id, identifier_type_id, identifier_value, status) "
                    "VALUES (:company, :type, 'ABCDE1234F', 'ACTIVE')"
                ),
                {"company": company_id, "type": pan_type_id},
            )
            await connection.execute(
                text(
                    "INSERT INTO core.entity_type_identifier_rules "
                    "(entity_type_id, identifier_type_id, requirement_level) "
                    "VALUES (:entity, :type, 'REQUIRED')"
                ),
                {"entity": entity_type_id, "type": pan_type_id},
            )

    async with _connection(database_url) as connection:
        with pytest.raises(DBAPIError):
            async with connection.begin():
                await connection.execute(
                    text(
                        "INSERT INTO core.company_identifier_types "
                        "(country_code, code, name, status) "
                        "VALUES ('IN', 'PAN', 'Duplicate PAN', 'ACTIVE')"
                    )
                )


def test_0034_is_single_head_and_enforces_identifier_contract(
    database_url: str,
) -> None:
    script = ScriptDirectory.from_config(Config("alembic.ini"))
    assert script.get_heads() == ["0034_company_identifier_foundation"]
    asyncio.run(_exercise_contract(database_url))
