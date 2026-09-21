import asyncio
import os
from collections.abc import AsyncIterator, Iterator, Mapping
from contextlib import asynccontextmanager
from datetime import date
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError, IntegrityError
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
        if await connection.scalar(text("SELECT to_regnamespace('core') IS NOT NULL")):
            pytest.fail("TEST_DATABASE_URL must point to a database without core schema")
        if await connection.scalar(
            text("SELECT to_regclass('public.alembic_version') IS NOT NULL")
        ):
            count = await connection.scalar(
                text("SELECT count(*) FROM public.alembic_version")
            )
            if count:
                pytest.fail("TEST_DATABASE_URL already has an applied Alembic revision")


@pytest.fixture(scope="module")
def database_url() -> Iterator[str]:
    value = os.getenv("TEST_DATABASE_URL")
    if value is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL migration tests")
    if make_url(value).drivername != "postgresql+asyncpg":
        pytest.fail("TEST_DATABASE_URL must use postgresql+asyncpg")

    asyncio.run(_assert_safe_empty_database(value))
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = value
    get_settings.cache_clear()
    command.upgrade(Config("alembic.ini"), "0011_payment_terms")
    try:
        yield value
    finally:
        try:
            command.downgrade(Config("alembic.ini"), "base")
        finally:
            if previous is None:
                os.environ.pop("DATABASE_URL", None)
            else:
                os.environ["DATABASE_URL"] = previous
            get_settings.cache_clear()


async def _execute(
    database_url: str,
    sql: str,
    parameters: Mapping[str, object] | None = None,
) -> None:
    async with _connection(database_url) as connection:
        async with connection.begin():
            await connection.execute(text(sql), parameters or {})


async def _scalar(
    database_url: str,
    sql: str,
    parameters: Mapping[str, object] | None = None,
) -> object:
    async with _connection(database_url) as connection:
        async with connection.begin():
            return await connection.scalar(text(sql), parameters or {})


async def _assert_rejected(
    database_url: str,
    sql: str,
    parameters: Mapping[str, object] | None = None,
) -> None:
    with pytest.raises((IntegrityError, DBAPIError)):
        await _execute(database_url, sql, parameters)


async def _seed_company(database_url: str) -> UUID:
    tenant_id = await _scalar(
        database_url,
        "INSERT INTO core.tenants (name, status) "
        "VALUES (:name, 'ACTIVE') RETURNING id",
        {"name": f"Tenant {uuid4()}"},
    )
    return await _scalar(
        database_url,
        "INSERT INTO core.companies (tenant_id, legal_name, status) "
        "VALUES (:tenant_id, :name, 'DRAFT') RETURNING id",
        {"tenant_id": tenant_id, "name": f"Company {uuid4()}"},
    )


async def _insert_account(
    database_url: str,
    *,
    company_id: UUID,
    account_name: str,
    account_code: str | None,
    valid_from: date,
    valid_to: date | None = None,
    status: str = "ACTIVE",
) -> UUID:
    return await _scalar(
        database_url,
        "INSERT INTO core.gl_accounts "
        "(company_id, account_code, account_name, valid_from, valid_to, status) "
        "VALUES (:company_id, :account_code, :account_name, :valid_from, "
        ":valid_to, :status) RETURNING id",
        {
            "company_id": company_id,
            "account_code": account_code,
            "account_name": account_name,
            "valid_from": valid_from,
            "valid_to": valid_to,
            "status": status,
        },
    )


async def _run_contract(database_url: str) -> None:
    assert await _scalar(
        database_url,
        "SELECT to_regclass('core.gl_accounts') IS NOT NULL",
    )
    first_company = await _seed_company(database_url)
    second_company = await _seed_company(database_url)

    first_account = await _insert_account(
        database_url,
        company_id=first_company,
        account_name="Trade Receivables",
        account_code="AR001",
        valid_from=date(2026, 4, 1),
    )
    assert isinstance(first_account, UUID)
    await _insert_account(
        database_url,
        company_id=first_company,
        account_name="Trade Receivables",
        account_code=None,
        valid_from=date(2026, 4, 1),
        status="INACTIVE",
    )
    await _insert_account(
        database_url,
        company_id=first_company,
        account_name="Another Uncoded Account",
        account_code=None,
        valid_from=date(2026, 4, 1),
    )
    await _insert_account(
        database_url,
        company_id=second_company,
        account_name="Other Company Receivables",
        account_code="AR001",
        valid_from=date(2026, 4, 1),
    )

    await _assert_rejected(
        database_url,
        "INSERT INTO core.gl_accounts "
        "(company_id, account_code, account_name, valid_from, status) "
        "VALUES (:company_id, 'AR001', 'Duplicate Code', :valid_from, 'ACTIVE')",
        {"company_id": first_company, "valid_from": date(2026, 4, 1)},
    )
    await _assert_rejected(
        database_url,
        "INSERT INTO core.gl_accounts "
        "(company_id, account_name, valid_from, valid_to, status) "
        "VALUES (:company_id, 'Invalid Range', :valid_from, :valid_to, 'ACTIVE')",
        {
            "company_id": first_company,
            "valid_from": date(2026, 4, 2),
            "valid_to": date(2026, 4, 1),
        },
    )
    for invalid_status in ("DRAFT", "SUSPENDED"):
        await _assert_rejected(
            database_url,
            "INSERT INTO core.gl_accounts "
            "(company_id, account_name, valid_from, status) "
            "VALUES (:company_id, :name, :valid_from, :status)",
            {
                "company_id": first_company,
                "name": f"Invalid {invalid_status}",
                "valid_from": date(2026, 4, 1),
                "status": invalid_status,
            },
        )
    await _assert_rejected(
        database_url,
        "DELETE FROM core.companies WHERE id = :company_id",
        {"company_id": first_company},
    )


async def _assert_downgrade(database_url: str) -> None:
    assert not await _scalar(
        database_url,
        "SELECT to_regclass('core.gl_accounts') IS NOT NULL",
    )
    assert await _scalar(
        database_url,
        "SELECT to_regclass('ar.payment_terms') IS NOT NULL",
    )
    assert await _scalar(
        database_url,
        "SELECT to_regclass('core.companies') IS NOT NULL",
    )


def test_gl_account_migration_contract(database_url: str) -> None:
    config = Config("alembic.ini")
    command.upgrade(config, "0012_gl_accounts")
    asyncio.run(_run_contract(database_url))

    command.downgrade(config, "0011_payment_terms")
    asyncio.run(_assert_downgrade(database_url))
