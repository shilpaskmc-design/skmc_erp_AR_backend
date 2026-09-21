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
    command.upgrade(Config("alembic.ini"), "0012_gl_accounts")
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


async def _seed_currency(database_url: str, code: str) -> None:
    await _execute(
        database_url,
        "INSERT INTO core.currencies (code, name, minor_units, status) "
        "VALUES (:code, :name, 2, 'ACTIVE')",
        {"code": code, "name": f"Currency {code}"},
    )


async def _seed_gl_account(database_url: str, company_id: UUID, code: str) -> UUID:
    return await _scalar(
        database_url,
        "INSERT INTO core.gl_accounts "
        "(company_id, account_code, account_name, valid_from, status) "
        "VALUES (:company_id, :code, :name, :valid_from, 'ACTIVE') RETURNING id",
        {
            "company_id": company_id,
            "code": code,
            "name": f"Bank GL {code}",
            "valid_from": date(2026, 4, 1),
        },
    )


async def _insert_bank_account(
    database_url: str,
    *,
    company_id: UUID,
    currency_code: str,
    account_number: str,
    status: str = "ACTIVE",
    gl_account_id: UUID | None = None,
    is_default: bool = False,
) -> UUID:
    return await _scalar(
        database_url,
        "INSERT INTO core.company_bank_accounts "
        "(company_id, account_holder_name, bank_name, account_number, "
        "currency_code, gl_account_id, is_default_for_billing, status) "
        "VALUES (:company_id, 'SKMC Example', 'Example Bank', "
        ":account_number, :currency_code, :gl_account_id, :is_default, "
        ":status) RETURNING id",
        {
            "company_id": company_id,
            "currency_code": currency_code,
            "account_number": account_number,
            "gl_account_id": gl_account_id,
            "is_default": is_default,
            "status": status,
        },
    )


async def _run_contract(database_url: str) -> None:
    assert await _scalar(
        database_url,
        "SELECT to_regclass('core.company_bank_accounts') IS NOT NULL",
    )
    await _seed_currency(database_url, "INR")
    await _seed_currency(database_url, "USD")
    first_company = await _seed_company(database_url)
    second_company = await _seed_company(database_url)
    first_gl = await _seed_gl_account(database_url, first_company, "BANK001")
    second_gl = await _seed_gl_account(database_url, second_company, "BANK001")

    linked_account = await _insert_bank_account(
        database_url,
        company_id=first_company,
        currency_code="INR",
        account_number="00123456789",
        gl_account_id=first_gl,
        is_default=True,
    )
    assert isinstance(linked_account, UUID)
    await _insert_bank_account(
        database_url,
        company_id=first_company,
        currency_code="USD",
        account_number="00123456789",
        gl_account_id=None,
        is_default=True,
    )
    await _insert_bank_account(
        database_url,
        company_id=first_company,
        currency_code="INR",
        account_number="00123456789",
        status="INACTIVE",
        is_default=True,
    )
    await _insert_bank_account(
        database_url,
        company_id=first_company,
        currency_code="USD",
        account_number="00123456789",
        status="INACTIVE",
    )

    await _assert_rejected(
        database_url,
        "INSERT INTO core.company_bank_accounts "
        "(company_id, account_holder_name, bank_name, account_number, "
        "currency_code, gl_account_id, status) "
        "VALUES (:company_id, 'SKMC Example', 'Example Bank', 'CROSS', "
        "'INR', :gl_account_id, 'ACTIVE')",
        {"company_id": first_company, "gl_account_id": second_gl},
    )
    await _assert_rejected(
        database_url,
        "INSERT INTO core.company_bank_accounts "
        "(company_id, account_holder_name, bank_name, account_number, "
        "currency_code, is_default_for_billing, status) "
        "VALUES (:company_id, 'SKMC Example', 'Example Bank', 'SECOND', "
        "'INR', true, 'ACTIVE')",
        {"company_id": first_company},
    )
    for invalid_status in ("DRAFT", "SUSPENDED"):
        await _assert_rejected(
            database_url,
            "INSERT INTO core.company_bank_accounts "
            "(company_id, account_holder_name, bank_name, account_number, "
            "currency_code, status) VALUES (:company_id, 'SKMC Example', "
            "'Example Bank', :number, 'INR', :status)",
            {
                "company_id": first_company,
                "number": f"INVALID-{invalid_status}",
                "status": invalid_status,
            },
        )

    await _assert_rejected(
        database_url,
        "DELETE FROM core.gl_accounts WHERE id = :gl_account_id",
        {"gl_account_id": first_gl},
    )
    await _assert_rejected(
        database_url,
        "DELETE FROM core.currencies WHERE code = 'INR'",
    )
    await _assert_rejected(
        database_url,
        "DELETE FROM core.companies WHERE id = :company_id",
        {"company_id": first_company},
    )


async def _assert_downgrade(database_url: str) -> None:
    assert not await _scalar(
        database_url,
        "SELECT to_regclass('core.company_bank_accounts') IS NOT NULL",
    )
    assert await _scalar(
        database_url,
        "SELECT to_regclass('core.gl_accounts') IS NOT NULL",
    )
    assert await _scalar(
        database_url,
        "SELECT to_regclass('ar.payment_terms') IS NOT NULL",
    )


def test_company_bank_account_migration_contract(database_url: str) -> None:
    config = Config("alembic.ini")
    command.upgrade(config, "0013_company_bank_accounts")
    asyncio.run(_run_contract(database_url))

    command.downgrade(config, "0012_gl_accounts")
    asyncio.run(_assert_downgrade(database_url))
