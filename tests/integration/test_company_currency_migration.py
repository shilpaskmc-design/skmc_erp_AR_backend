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


REVISION = "0014_company_currency_configuration"
PREVIOUS_REVISION = "0013_company_bank_accounts"


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
            pytest.fail(
                "TEST_DATABASE_URL must point to a database without core schema"
            )
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
    command.upgrade(Config("alembic.ini"), PREVIOUS_REVISION)
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
    # PostgreSQL may report a VARCHAR length/type failure before a CHECK failure.
    with pytest.raises(DBAPIError):
        await _execute(database_url, sql, parameters)


async def _seed_currency(database_url: str, code: str) -> None:
    await _execute(
        database_url,
        "INSERT INTO core.currencies (code, name, minor_units, status) "
        "VALUES (:code, :name, 2, 'ACTIVE')",
        {"code": code, "name": f"Currency {code}"},
    )


async def _seed_company(
    database_url: str,
    *,
    base_currency_code: str,
) -> UUID:
    tenant_id = await _scalar(
        database_url,
        "INSERT INTO core.tenants (name, status) "
        "VALUES (:name, 'ACTIVE') RETURNING id",
        {"name": f"Tenant {uuid4()}"},
    )
    return await _scalar(
        database_url,
        "INSERT INTO core.companies "
        "(tenant_id, legal_name, base_currency_code, status) "
        "VALUES (:tenant_id, :name, :currency, 'DRAFT') RETURNING id",
        {
            "tenant_id": tenant_id,
            "name": f"Company {uuid4()}",
            "currency": base_currency_code,
        },
    )


async def _insert_ar_currency(
    database_url: str,
    *,
    company_id: UUID,
    currency_code: str,
    billing_enabled: bool,
    receipt_enabled: bool,
    is_default_billing: bool = False,
    is_default_receipt: bool = False,
    status: str = "ACTIVE",
) -> UUID:
    return await _scalar(
        database_url,
        "INSERT INTO ar.company_ar_currencies "
        "(company_id, currency_code, billing_enabled, receipt_enabled, "
        "is_default_billing, is_default_receipt, status) "
        "VALUES (:company_id, :currency_code, :billing_enabled, "
        ":receipt_enabled, :is_default_billing, :is_default_receipt, "
        ":status) RETURNING id",
        {
            "company_id": company_id,
            "currency_code": currency_code,
            "billing_enabled": billing_enabled,
            "receipt_enabled": receipt_enabled,
            "is_default_billing": is_default_billing,
            "is_default_receipt": is_default_receipt,
            "status": status,
        },
    )


async def _run_contract(database_url: str) -> None:
    assert await _scalar(
        database_url,
        "SELECT to_regclass('core.company_reporting_currencies') IS NOT NULL",
    )
    assert await _scalar(
        database_url,
        "SELECT to_regclass('ar.company_ar_currencies') IS NOT NULL",
    )
    assert await _scalar(
        database_url,
        "SELECT character_maximum_length FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = 'alembic_version' "
        "AND column_name = 'version_num'",
    ) == 255
    assert await _scalar(
        database_url,
        "SELECT version_num FROM public.alembic_version",
    ) == REVISION

    for code in ("INR", "USD", "EUR", "GBP", "JPY"):
        await _seed_currency(database_url, code)
    first_company = await _seed_company(
        database_url,
        base_currency_code="INR",
    )
    second_company = await _seed_company(
        database_url,
        base_currency_code="USD",
    )

    await _execute(
        database_url,
        "INSERT INTO core.company_reporting_currencies "
        "(company_id, currency_code, status) "
        "VALUES (:company_id, 'USD', 'ACTIVE')",
        {"company_id": first_company},
    )
    await _execute(
        database_url,
        "INSERT INTO core.company_reporting_currencies "
        "(company_id, currency_code, status) "
        "VALUES (:company_id, 'USD', 'ACTIVE')",
        {"company_id": second_company},
    )
    await _assert_rejected(
        database_url,
        "INSERT INTO core.company_reporting_currencies "
        "(company_id, currency_code, status) "
        "VALUES (:company_id, 'USD', 'ACTIVE')",
        {"company_id": first_company},
    )
    await _assert_rejected(
        database_url,
        "INSERT INTO core.company_reporting_currencies "
        "(company_id, currency_code) VALUES (:company_id, 'EUR')",
        {"company_id": first_company},
    )
    await _assert_rejected(
        database_url,
        "INSERT INTO core.company_reporting_currencies "
        "(company_id, currency_code, status) "
        "VALUES (:company_id, 'EUR', 'THIS_STATUS_IS_TOO_LONG')",
        {"company_id": first_company},
    )
    await _assert_rejected(
        database_url,
        "INSERT INTO core.company_reporting_currencies "
        "(company_id, currency_code, status) "
        "VALUES (:company_id, 'AUD', 'ACTIVE')",
        {"company_id": first_company},
    )
    await _assert_rejected(
        database_url,
        "INSERT INTO core.company_reporting_currencies "
        "(company_id, currency_code, status) "
        "VALUES (:company_id, 'EUR', 'ACTIVE')",
        {"company_id": uuid4()},
    )

    first_default = await _insert_ar_currency(
        database_url,
        company_id=first_company,
        currency_code="INR",
        billing_enabled=True,
        receipt_enabled=False,
        is_default_billing=True,
    )
    assert isinstance(first_default, UUID)
    await _insert_ar_currency(
        database_url,
        company_id=first_company,
        currency_code="USD",
        billing_enabled=False,
        receipt_enabled=True,
        is_default_receipt=True,
    )
    await _insert_ar_currency(
        database_url,
        company_id=first_company,
        currency_code="EUR",
        billing_enabled=True,
        receipt_enabled=True,
    )
    await _insert_ar_currency(
        database_url,
        company_id=first_company,
        currency_code="JPY",
        billing_enabled=True,
        receipt_enabled=False,
        is_default_billing=True,
        status="INACTIVE",
    )
    await _insert_ar_currency(
        database_url,
        company_id=second_company,
        currency_code="INR",
        billing_enabled=True,
        receipt_enabled=True,
        is_default_billing=True,
        is_default_receipt=True,
    )

    await _assert_rejected(
        database_url,
        "INSERT INTO ar.company_ar_currencies "
        "(company_id, currency_code, billing_enabled, receipt_enabled, status) "
        "VALUES (:company_id, 'GBP', false, false, 'ACTIVE')",
        {"company_id": first_company},
    )
    await _assert_rejected(
        database_url,
        "INSERT INTO ar.company_ar_currencies "
        "(company_id, currency_code, billing_enabled, receipt_enabled, "
        "is_default_billing, status) "
        "VALUES (:company_id, 'GBP', false, true, true, 'ACTIVE')",
        {"company_id": first_company},
    )
    await _assert_rejected(
        database_url,
        "INSERT INTO ar.company_ar_currencies "
        "(company_id, currency_code, billing_enabled, receipt_enabled, "
        "is_default_receipt, status) "
        "VALUES (:company_id, 'GBP', true, false, true, 'ACTIVE')",
        {"company_id": first_company},
    )
    await _assert_rejected(
        database_url,
        "INSERT INTO ar.company_ar_currencies "
        "(company_id, currency_code, billing_enabled, receipt_enabled, "
        "is_default_billing, status) "
        "VALUES (:company_id, 'GBP', true, false, true, 'ACTIVE')",
        {"company_id": first_company},
    )
    await _assert_rejected(
        database_url,
        "INSERT INTO ar.company_ar_currencies "
        "(company_id, currency_code, billing_enabled, receipt_enabled, "
        "is_default_receipt, status) "
        "VALUES (:company_id, 'GBP', false, true, true, 'ACTIVE')",
        {"company_id": first_company},
    )
    await _assert_rejected(
        database_url,
        "INSERT INTO ar.company_ar_currencies "
        "(company_id, currency_code, billing_enabled, receipt_enabled, status) "
        "VALUES (:company_id, 'INR', true, false, 'ACTIVE')",
        {"company_id": first_company},
    )
    await _assert_rejected(
        database_url,
        "INSERT INTO ar.company_ar_currencies "
        "(company_id, currency_code, billing_enabled, receipt_enabled, status) "
        "VALUES (:company_id, 'AUD', true, false, 'ACTIVE')",
        {"company_id": first_company},
    )
    await _assert_rejected(
        database_url,
        "INSERT INTO ar.company_ar_currencies "
        "(company_id, currency_code, billing_enabled, receipt_enabled) "
        "VALUES (:company_id, 'GBP', true, false)",
        {"company_id": first_company},
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
        "SELECT to_regclass('core.company_reporting_currencies') IS NOT NULL",
    )
    assert not await _scalar(
        database_url,
        "SELECT to_regclass('ar.company_ar_currencies') IS NOT NULL",
    )
    assert await _scalar(
        database_url,
        "SELECT to_regclass('core.company_bank_accounts') IS NOT NULL",
    )
    assert await _scalar(
        database_url,
        "SELECT version_num FROM public.alembic_version",
    ) == PREVIOUS_REVISION


async def _assert_reupgrade(database_url: str) -> None:
    assert await _scalar(
        database_url,
        "SELECT to_regclass('core.company_reporting_currencies') IS NOT NULL",
    )
    assert await _scalar(
        database_url,
        "SELECT to_regclass('ar.company_ar_currencies') IS NOT NULL",
    )
    assert await _scalar(
        database_url,
        "SELECT version_num FROM public.alembic_version",
    ) == REVISION


def test_company_currency_migration_contract(database_url: str) -> None:
    config = Config("alembic.ini")
    command.upgrade(config, REVISION)
    asyncio.run(_run_contract(database_url))

    command.downgrade(config, PREVIOUS_REVISION)
    asyncio.run(_assert_downgrade(database_url))

    command.upgrade(config, REVISION)
    asyncio.run(_assert_reupgrade(database_url))
