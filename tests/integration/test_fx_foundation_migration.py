import asyncio
import os
from collections.abc import AsyncIterator, Iterator, Mapping
from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from skmc_erp.config import get_settings


REVISION = "0015_exchange_rates_fx_policies"
PREVIOUS_REVISION = "0014_company_currency_configuration"


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
    with pytest.raises(DBAPIError):
        await _execute(database_url, sql, parameters)


async def _seed_currency(database_url: str, code: str) -> None:
    await _execute(
        database_url,
        "INSERT INTO core.currencies (code, name, minor_units, status) "
        "VALUES (:code, :name, 2, 'ACTIVE')",
        {"code": code, "name": f"Currency {code}"},
    )


async def _seed_company(database_url: str) -> UUID:
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
        "VALUES (:tenant_id, :name, 'INR', 'DRAFT') RETURNING id",
        {"tenant_id": tenant_id, "name": f"Company {uuid4()}"},
    )


async def _insert_rate(
    database_url: str,
    *,
    company_id: UUID,
    from_currency: str,
    to_currency: str,
    rate_type: str,
    effective_from: date,
    effective_to: date | None,
    status: str = "ACTIVE",
) -> UUID:
    return await _scalar(
        database_url,
        "INSERT INTO core.exchange_rates "
        "(company_id, from_currency_code, to_currency_code, rate, "
        "rate_type, effective_from, effective_to, source, status) "
        "VALUES (:company_id, :from_currency, :to_currency, :rate, "
        ":rate_type, :effective_from, :effective_to, 'Treasury', :status) "
        "RETURNING id",
        {
            "company_id": company_id,
            "from_currency": from_currency,
            "to_currency": to_currency,
            "rate": Decimal("83.125000000001"),
            "rate_type": rate_type,
            "effective_from": effective_from,
            "effective_to": effective_to,
            "status": status,
        },
    )


async def _insert_policy(
    database_url: str,
    *,
    company_id: UUID,
    purpose: str,
    default_rate_type: str,
    allow_override: bool = False,
    reason_required: bool = False,
    status: str = "ACTIVE",
) -> UUID:
    return await _scalar(
        database_url,
        "INSERT INTO ar.fx_policies "
        "(company_id, purpose, default_rate_type, "
        "allow_user_fixed_override, reason_required_for_override, status) "
        "VALUES (:company_id, :purpose, :default_rate_type, "
        ":allow_override, :reason_required, :status) RETURNING id",
        {
            "company_id": company_id,
            "purpose": purpose,
            "default_rate_type": default_rate_type,
            "allow_override": allow_override,
            "reason_required": reason_required,
            "status": status,
        },
    )


async def _run_contract(database_url: str) -> None:
    assert await _scalar(
        database_url,
        "SELECT to_regclass('core.exchange_rates') IS NOT NULL",
    )
    assert await _scalar(
        database_url,
        "SELECT to_regclass('ar.fx_policies') IS NOT NULL",
    )
    assert await _scalar(
        database_url,
        "SELECT EXISTS (SELECT 1 FROM pg_extension "
        "WHERE extname = 'btree_gist')",
    )
    assert await _scalar(
        database_url,
        "SELECT version_num FROM public.alembic_version",
    ) == REVISION

    for code in ("INR", "USD", "EUR", "GBP"):
        await _seed_currency(database_url, code)
    first_company = await _seed_company(database_url)
    second_company = await _seed_company(database_url)

    first_rate = await _insert_rate(
        database_url,
        company_id=first_company,
        from_currency="USD",
        to_currency="INR",
        rate_type="CORPORATE",
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 1, 31),
    )
    assert isinstance(first_rate, UUID)
    await _insert_rate(
        database_url,
        company_id=first_company,
        from_currency="USD",
        to_currency="INR",
        rate_type="CORPORATE",
        effective_from=date(2026, 2, 1),
        effective_to=date(2026, 2, 28),
    )
    await _insert_rate(
        database_url,
        company_id=first_company,
        from_currency="USD",
        to_currency="INR",
        rate_type="SPOT",
        effective_from=date(2026, 1, 15),
        effective_to=None,
    )
    await _insert_rate(
        database_url,
        company_id=first_company,
        from_currency="INR",
        to_currency="USD",
        rate_type="CORPORATE",
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 1, 31),
    )
    await _insert_rate(
        database_url,
        company_id=second_company,
        from_currency="USD",
        to_currency="INR",
        rate_type="CORPORATE",
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 1, 31),
    )
    await _insert_rate(
        database_url,
        company_id=first_company,
        from_currency="USD",
        to_currency="INR",
        rate_type="CORPORATE",
        effective_from=date(2026, 1, 15),
        effective_to=date(2026, 2, 15),
        status="INACTIVE",
    )

    await _assert_rejected(
        database_url,
        "INSERT INTO core.exchange_rates "
        "(company_id, from_currency_code, to_currency_code, rate, "
        "rate_type, effective_from, effective_to, status) "
        "VALUES (:company_id, 'USD', 'INR', 83, 'CORPORATE', "
        ":start_date, :end_date, 'ACTIVE')",
        {
            "company_id": first_company,
            "start_date": date(2026, 1, 31),
            "end_date": date(2026, 2, 10),
        },
    )
    await _assert_rejected(
        database_url,
        "INSERT INTO core.exchange_rates "
        "(company_id, from_currency_code, to_currency_code, rate, "
        "rate_type, effective_from, status) "
        "VALUES (:company_id, 'USD', 'INR', 84, 'SPOT', "
        ":effective_from, 'ACTIVE')",
        {"company_id": first_company, "effective_from": date(2027, 1, 1)},
    )
    invalid_rate_sql = (
        "INSERT INTO core.exchange_rates "
        "(company_id, from_currency_code, to_currency_code, rate, "
        "rate_type, effective_from, status) "
        "VALUES (:company_id, :from_currency, :to_currency, :rate, "
        ":rate_type, :effective_from, :status)"
    )
    for parameters in (
        {
            "company_id": first_company,
            "from_currency": "EUR",
            "to_currency": "INR",
            "rate": Decimal("0"),
            "rate_type": "CORPORATE",
            "effective_from": date(2026, 1, 1),
            "status": "ACTIVE",
        },
        {
            "company_id": first_company,
            "from_currency": "EUR",
            "to_currency": "INR",
            "rate": Decimal("-1"),
            "rate_type": "CORPORATE",
            "effective_from": date(2026, 1, 1),
            "status": "ACTIVE",
        },
        {
            "company_id": first_company,
            "from_currency": "EUR",
            "to_currency": "EUR",
            "rate": Decimal("1"),
            "rate_type": "CORPORATE",
            "effective_from": date(2026, 1, 1),
            "status": "ACTIVE",
        },
        {
            "company_id": first_company,
            "from_currency": "EUR",
            "to_currency": "INR",
            "rate": Decimal("90"),
            "rate_type": "USER_FIXED",
            "effective_from": date(2026, 1, 1),
            "status": "ACTIVE",
        },
        {
            "company_id": first_company,
            "from_currency": "EUR",
            "to_currency": "INR",
            "rate": Decimal("90"),
            "rate_type": "CORPORATE",
            "effective_from": date(2026, 1, 1),
            "status": "DRAFT",
        },
        {
            "company_id": first_company,
            "from_currency": "AUD",
            "to_currency": "INR",
            "rate": Decimal("55"),
            "rate_type": "CORPORATE",
            "effective_from": date(2026, 1, 1),
            "status": "ACTIVE",
        },
        {
            "company_id": uuid4(),
            "from_currency": "EUR",
            "to_currency": "INR",
            "rate": Decimal("90"),
            "rate_type": "CORPORATE",
            "effective_from": date(2026, 1, 1),
            "status": "ACTIVE",
        },
    ):
        await _assert_rejected(database_url, invalid_rate_sql, parameters)
    await _assert_rejected(
        database_url,
        "INSERT INTO core.exchange_rates "
        "(company_id, from_currency_code, to_currency_code, rate, "
        "rate_type, effective_from, effective_to, status) "
        "VALUES (:company_id, 'EUR', 'INR', 90, 'CORPORATE', "
        ":start_date, :end_date, 'ACTIVE')",
        {
            "company_id": first_company,
            "start_date": date(2026, 2, 1),
            "end_date": date(2026, 1, 31),
        },
    )
    await _assert_rejected(
        database_url,
        "INSERT INTO core.exchange_rates "
        "(company_id, from_currency_code, to_currency_code, "
        "rate_type, effective_from, status) "
        "VALUES (:company_id, 'EUR', 'INR', 'CORPORATE', "
        ":effective_from, 'ACTIVE')",
        {"company_id": first_company, "effective_from": date(2026, 1, 1)},
    )

    first_policy = await _insert_policy(
        database_url,
        company_id=first_company,
        purpose="BILLING",
        default_rate_type="CORPORATE",
        allow_override=True,
        reason_required=True,
    )
    assert isinstance(first_policy, UUID)
    await _insert_policy(
        database_url,
        company_id=first_company,
        purpose="RECEIPT",
        default_rate_type="SPOT",
    )
    await _insert_policy(
        database_url,
        company_id=first_company,
        purpose="REPORTING",
        default_rate_type="CORPORATE",
        status="INACTIVE",
    )
    await _insert_policy(
        database_url,
        company_id=second_company,
        purpose="BILLING",
        default_rate_type="SPOT",
    )

    await _assert_rejected(
        database_url,
        "INSERT INTO ar.fx_policies "
        "(company_id, purpose, default_rate_type, status) "
        "VALUES (:company_id, 'BILLING', 'SPOT', 'ACTIVE')",
        {"company_id": first_company},
    )
    invalid_policy_sql = (
        "INSERT INTO ar.fx_policies "
        "(company_id, purpose, default_rate_type, "
        "allow_user_fixed_override, reason_required_for_override, status) "
        "VALUES (:company_id, :purpose, :rate_type, :allow_override, "
        ":reason_required, :status)"
    )
    for parameters in (
        {
            "company_id": second_company,
            "purpose": "SETTLEMENT",
            "rate_type": "SPOT",
            "allow_override": False,
            "reason_required": False,
            "status": "ACTIVE",
        },
        {
            "company_id": second_company,
            "purpose": "REPORTING",
            "rate_type": "USER_FIXED",
            "allow_override": False,
            "reason_required": False,
            "status": "ACTIVE",
        },
        {
            "company_id": second_company,
            "purpose": "REPORTING",
            "rate_type": "SPOT",
            "allow_override": False,
            "reason_required": True,
            "status": "ACTIVE",
        },
        {
            "company_id": second_company,
            "purpose": "REPORTING",
            "rate_type": "SPOT",
            "allow_override": False,
            "reason_required": False,
            "status": "DRAFT",
        },
        {
            "company_id": uuid4(),
            "purpose": "BILLING",
            "rate_type": "SPOT",
            "allow_override": False,
            "reason_required": False,
            "status": "ACTIVE",
        },
    ):
        await _assert_rejected(database_url, invalid_policy_sql, parameters)
    await _assert_rejected(
        database_url,
        "INSERT INTO ar.fx_policies (company_id, purpose, status) "
        "VALUES (:company_id, 'REPORTING', 'ACTIVE')",
        {"company_id": second_company},
    )

    await _assert_rejected(
        database_url,
        "DELETE FROM core.currencies WHERE code = 'USD'",
    )
    await _assert_rejected(
        database_url,
        "DELETE FROM core.companies WHERE id = :company_id",
        {"company_id": first_company},
    )


async def _assert_downgrade(database_url: str) -> None:
    assert not await _scalar(
        database_url,
        "SELECT to_regclass('core.exchange_rates') IS NOT NULL",
    )
    assert not await _scalar(
        database_url,
        "SELECT to_regclass('ar.fx_policies') IS NOT NULL",
    )
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
    ) == PREVIOUS_REVISION


async def _assert_reupgrade(database_url: str) -> None:
    assert await _scalar(
        database_url,
        "SELECT to_regclass('core.exchange_rates') IS NOT NULL",
    )
    assert await _scalar(
        database_url,
        "SELECT to_regclass('ar.fx_policies') IS NOT NULL",
    )
    assert await _scalar(
        database_url,
        "SELECT version_num FROM public.alembic_version",
    ) == REVISION


def test_fx_foundation_migration_contract(database_url: str) -> None:
    config = Config("alembic.ini")
    command.upgrade(config, REVISION)
    asyncio.run(_run_contract(database_url))

    command.downgrade(config, PREVIOUS_REVISION)
    asyncio.run(_assert_downgrade(database_url))

    command.upgrade(config, REVISION)
    asyncio.run(_assert_reupgrade(database_url))
