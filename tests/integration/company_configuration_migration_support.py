import asyncio
import os
from collections.abc import Awaitable, Callable, Mapping
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
async def connection(database_url: str):
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as value:
            yield value
    finally:
        await engine.dispose()


async def execute(database_url: str, sql: str, parameters: Mapping[str, object] | None = None) -> None:
    async with connection(database_url) as value:
        async with value.begin():
            await value.execute(text(sql), parameters or {})


async def scalar(database_url: str, sql: str, parameters: Mapping[str, object] | None = None):
    async with connection(database_url) as value:
        async with value.begin():
            return await value.scalar(text(sql), parameters or {})


async def rejected(database_url: str, sql: str, parameters: Mapping[str, object] | None = None) -> None:
    with pytest.raises(DBAPIError):
        await execute(database_url, sql, parameters)


async def seed_company(database_url: str):
    tenant_id = await scalar(
        database_url,
        "INSERT INTO core.tenants (name, status) VALUES ('Migration Tenant', 'ACTIVE') RETURNING id",
    )
    company_id = await scalar(
        database_url,
        "INSERT INTO core.companies (tenant_id, legal_name, status) VALUES (:tenant, 'Migration Company', 'DRAFT') RETURNING id",
        {"tenant": tenant_id},
    )
    return tenant_id, company_id


async def _safe_empty(database_url: str) -> None:
    async with connection(database_url) as value:
        if await value.scalar(text("SELECT to_regnamespace('core') IS NOT NULL")):
            pytest.fail("TEST_DATABASE_URL must point to a database without core schema")
        if await value.scalar(text("SELECT to_regclass('public.alembic_version') IS NOT NULL")):
            if await value.scalar(text("SELECT count(*) FROM public.alembic_version")):
                pytest.fail("TEST_DATABASE_URL already has an applied Alembic revision")


def run_migration_case(
    revision: str,
    previous_revision: str,
    created_tables: tuple[str, ...],
    exercise: Callable[[str], Awaitable[None]],
) -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL migration tests")
    if make_url(database_url).drivername != "postgresql+asyncpg":
        pytest.fail("TEST_DATABASE_URL must use postgresql+asyncpg")

    asyncio.run(_safe_empty(database_url))
    old_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    get_settings.cache_clear()
    config = Config("alembic.ini")
    try:
        command.upgrade(config, previous_revision)
        command.upgrade(config, revision)
        assert asyncio.run(scalar(database_url, "SELECT version_num FROM public.alembic_version")) == revision
        for table in created_tables:
            assert asyncio.run(scalar(database_url, "SELECT to_regclass(:table) IS NOT NULL", {"table": table}))
        asyncio.run(exercise(database_url))
        command.downgrade(config, previous_revision)
        assert asyncio.run(scalar(database_url, "SELECT version_num FROM public.alembic_version")) == previous_revision
        for table in created_tables:
            assert not asyncio.run(scalar(database_url, "SELECT to_regclass(:table) IS NOT NULL", {"table": table}))
        command.upgrade(config, revision)
        assert asyncio.run(scalar(database_url, "SELECT version_num FROM public.alembic_version")) == revision
        assert len(ScriptDirectory.from_config(config).get_heads()) == 1
    finally:
        try:
            command.downgrade(config, "base")
        finally:
            if old_url is None:
                os.environ.pop("DATABASE_URL", None)
            else:
                os.environ["DATABASE_URL"] = old_url
            get_settings.cache_clear()
