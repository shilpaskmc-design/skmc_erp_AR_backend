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
    command.upgrade(Config("alembic.ini"), "0010_cost_center_configuration")
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


async def _insert_term(
    database_url: str,
    *,
    company_id: UUID,
    name: str,
    code: str,
    term_type: str,
    credit_days: int,
    status: str = "ACTIVE",
    is_default: bool | None = None,
) -> UUID:
    columns = "company_id, name, code, term_type, credit_days, status"
    values = ":company_id, :name, :code, :term_type, :credit_days, :status"
    parameters: dict[str, object] = {
        "company_id": company_id,
        "name": name,
        "code": code,
        "term_type": term_type,
        "credit_days": credit_days,
        "status": status,
    }
    if is_default is not None:
        columns += ", is_default"
        values += ", :is_default"
        parameters["is_default"] = is_default
    return await _scalar(
        database_url,
        f"INSERT INTO ar.payment_terms ({columns}) VALUES ({values}) RETURNING id",
        parameters,
    )


async def _run_contract(database_url: str) -> None:
    assert await _scalar(
        database_url,
        "SELECT to_regclass('ar.payment_terms') IS NOT NULL",
    )
    first_company = await _seed_company(database_url)
    second_company = await _seed_company(database_url)

    immediate_id = await _insert_term(
        database_url,
        company_id=first_company,
        name="Immediate",
        code="IMMEDIATE",
        term_type="IMMEDIATE",
        credit_days=0,
    )
    assert isinstance(immediate_id, UUID)
    assert not await _scalar(
        database_url,
        "SELECT is_default FROM ar.payment_terms WHERE id = :id",
        {"id": immediate_id},
    )
    await _insert_term(
        database_url,
        company_id=first_company,
        name="Net 30",
        code="NET30",
        term_type="NET_DAYS",
        credit_days=30,
        is_default=True,
    )
    await _insert_term(
        database_url,
        company_id=first_company,
        name="Net 30",
        code="NET32767",
        term_type="NET_DAYS",
        credit_days=32767,
    )
    await _insert_term(
        database_url,
        company_id=second_company,
        name="Net 30",
        code="NET30",
        term_type="NET_DAYS",
        credit_days=30,
        is_default=True,
    )

    invalid_cases = (
        {
            "name": "   ",
            "code": "BLANK_NAME",
            "term_type": "NET_DAYS",
            "credit_days": 1,
        },
        {
            "name": "Immediate Invalid",
            "code": "IMM1",
            "term_type": "IMMEDIATE",
            "credit_days": 1,
        },
        {
            "name": "Net Zero",
            "code": "NET0",
            "term_type": "NET_DAYS",
            "credit_days": 0,
        },
        {
            "name": "Invalid Type",
            "code": "INVALID_TYPE",
            "term_type": "END_OF_MONTH",
            "credit_days": 30,
        },
        {
            "name": "Invalid Status",
            "code": "INVALID_STATUS",
            "term_type": "NET_DAYS",
            "credit_days": 30,
            "status": "DRAFT",
        },
        {
            "name": "Inactive Default",
            "code": "INACTIVE_DEFAULT",
            "term_type": "NET_DAYS",
            "credit_days": 30,
            "status": "INACTIVE",
            "is_default": True,
        },
        {
            "name": "Second Default",
            "code": "SECOND_DEFAULT",
            "term_type": "NET_DAYS",
            "credit_days": 45,
            "is_default": True,
        },
        {
            "name": "Duplicate Code",
            "code": "NET30",
            "term_type": "NET_DAYS",
            "credit_days": 45,
        },
    )
    for case in invalid_cases:
        await _assert_rejected(
            database_url,
            "INSERT INTO ar.payment_terms "
            "(company_id, name, code, term_type, credit_days, status, is_default) "
            "VALUES (:company_id, :name, :code, :term_type, :credit_days, "
            ":status, :is_default)",
            {
                "company_id": first_company,
                "status": "ACTIVE",
                "is_default": False,
                **case,
            },
        )

    await _assert_rejected(
        database_url,
        "INSERT INTO ar.payment_terms "
        "(company_id, name, code, term_type, credit_days, status) "
        "VALUES (:company_id, 'Missing Company', 'MISSING', 'IMMEDIATE', 0, "
        "'ACTIVE')",
        {"company_id": uuid4()},
    )


async def _assert_downgrade(database_url: str) -> None:
    assert not await _scalar(
        database_url,
        "SELECT to_regclass('ar.payment_terms') IS NOT NULL",
    )
    assert await _scalar(
        database_url,
        "SELECT to_regclass('core.company_cost_center_settings') IS NOT NULL",
    )
    assert await _scalar(
        database_url,
        "SELECT to_regclass('ar.service_types') IS NOT NULL",
    )


def test_payment_term_migration_contract(database_url: str) -> None:
    config = Config("alembic.ini")
    command.upgrade(config, "0011_payment_terms")
    asyncio.run(_run_contract(database_url))

    command.downgrade(config, "0010_cost_center_configuration")
    asyncio.run(_assert_downgrade(database_url))
