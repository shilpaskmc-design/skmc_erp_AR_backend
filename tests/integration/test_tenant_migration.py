import asyncio
import os
import re
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from datetime import datetime
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
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


async def _assert_migration_removed(database_url: str) -> None:
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
    command.upgrade(alembic_config, "0001_create_core_tenants")

    try:
        yield database_url
    finally:
        try:
            command.downgrade(alembic_config, "base")
            asyncio.run(_assert_migration_removed(database_url))
        finally:
            if previous_database_url is None:
                os.environ.pop("DATABASE_URL", None)
            else:
                os.environ["DATABASE_URL"] = previous_database_url
            get_settings.cache_clear()


async def _insert_tenant(
    database_url: str,
    *,
    name: str,
    status: str | None,
    code: str | None = None,
) -> dict[str, object]:
    columns = ["name"]
    values = [":name"]
    parameters: dict[str, str] = {"name": name}

    if status is not None:
        columns.append("status")
        values.append(":status")
        parameters["status"] = status
    if code is not None:
        columns.append("code")
        values.append(":code")
        parameters["code"] = code

    statement = text(
        f"""
        INSERT INTO core.tenants ({", ".join(columns)})
        VALUES ({", ".join(values)})
        RETURNING id, name, code, status, created_at, updated_at
        """
    )

    async with _connection(database_url) as connection:
        async with connection.begin():
            result = await connection.execute(statement, parameters)
            return dict(result.mappings().one())


async def _assert_insert_rejected(
    database_url: str,
    *,
    name: str,
    status: str | None,
    code: str | None = None,
) -> None:
    with pytest.raises(IntegrityError):
        await _insert_tenant(
            database_url,
            name=name,
            status=status,
            code=code,
        )


async def _run_tenant_contract_checks(database_url: str) -> None:
    async with _connection(database_url) as connection:
        table_exists = await connection.scalar(
            text("SELECT to_regclass('core.tenants') IS NOT NULL")
        )
        assert table_exists

        status_default = await connection.scalar(
            text(
                """
                SELECT column_default
                FROM information_schema.columns
                WHERE table_schema = 'core'
                  AND table_name = 'tenants'
                  AND column_name = 'status'
                """
            )
        )
        assert status_default is None

    first = await _insert_tenant(
        database_url,
        name="Duplicate Name Allowed",
        status="ACTIVE",
    )
    second = await _insert_tenant(
        database_url,
        name="Duplicate Name Allowed",
        status="ACTIVE",
    )

    assert isinstance(first["id"], UUID)
    assert first["id"] != second["id"]
    assert first["code"] == "TEN000001"
    assert second["code"] == "TEN000002"
    assert re.fullmatch(r"TEN\d{6,}", str(first["code"]))
    assert first["code"] != second["code"]
    assert isinstance(first["created_at"], datetime)
    assert first["created_at"].tzinfo is not None
    assert isinstance(first["updated_at"], datetime)
    assert first["updated_at"].tzinfo is not None

    for status in ("SUSPENDED", "INACTIVE"):
        tenant = await _insert_tenant(
            database_url,
            name=f"Valid {status}",
            status=status,
        )
        assert tenant["status"] == status

    await _assert_insert_rejected(database_url, name="", status="ACTIVE")
    await _assert_insert_rejected(database_url, name="   ", status="ACTIVE")
    await _assert_insert_rejected(
        database_url,
        name="Blank Code",
        status="ACTIVE",
        code="   ",
    )
    await _assert_insert_rejected(
        database_url,
        name="Invalid Status",
        status="DELETED",
    )
    await _assert_insert_rejected(
        database_url,
        name="Missing Status",
        status=None,
    )

    await _insert_tenant(
        database_url,
        name="Explicit Code One",
        status="ACTIVE",
        code="TEN_EXPLICIT",
    )
    await _assert_insert_rejected(
        database_url,
        name="Explicit Code Two",
        status="ACTIVE",
        code="TEN_EXPLICIT",
    )

    async with _connection(database_url) as connection:
        async with connection.begin():
            await connection.execute(
                text("SELECT setval('core.tenant_code_seq', 999998, true)")
            )

    six_digit = await _insert_tenant(
        database_url,
        name="Six Digit Sequence",
        status="ACTIVE",
    )
    seven_digit = await _insert_tenant(
        database_url,
        name="Seven Digit Sequence",
        status="ACTIVE",
    )
    assert six_digit["code"] == "TEN999999"
    assert seven_digit["code"] == "TEN1000000"


def test_tenant_migration_contract(migrated_database: str) -> None:
    asyncio.run(_run_tenant_contract_checks(migrated_database))
