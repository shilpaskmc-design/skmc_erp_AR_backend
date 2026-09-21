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

    command.upgrade(Config("alembic.ini"), "0015_exchange_rates_fx_policies")

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
        {
            "tenant_id": tenant_id,
            "name": f"Company {uuid4()}",
        },
    )


async def _insert_hierarchy(
    database_url: str,
    *,
    company_id: UUID,
    hierarchy_name: str,
    purpose_code: str = "ACCOUNTING",
    is_primary: bool = False,
    status: str = "ACTIVE",
) -> UUID:
    return await _scalar(
        database_url,
        "INSERT INTO core.account_hierarchies "
        "(company_id, hierarchy_name, purpose_code, is_primary, status) "
        "VALUES (:company_id, :hierarchy_name, :purpose_code, "
        ":is_primary, :status) RETURNING id",
        {
            "company_id": company_id,
            "hierarchy_name": hierarchy_name,
            "purpose_code": purpose_code,
            "is_primary": is_primary,
            "status": status,
        },
    )


async def _insert_group(
    database_url: str,
    *,
    company_id: UUID,
    hierarchy_id: UUID,
    group_name: str,
    group_code: str | None,
    status: str = "ACTIVE",
) -> UUID:
    return await _scalar(
        database_url,
        "INSERT INTO core.account_groups "
        "(company_id, hierarchy_id, group_name, group_code, status) "
        "VALUES (:company_id, :hierarchy_id, :group_name, "
        ":group_code, :status) RETURNING id",
        {
            "company_id": company_id,
            "hierarchy_id": hierarchy_id,
            "group_name": group_name,
            "group_code": group_code,
            "status": status,
        },
    )


async def _run_contract(database_url: str) -> None:
    assert await _scalar(
        database_url,
        "SELECT to_regclass('core.account_hierarchies') IS NOT NULL",
    )
    assert await _scalar(
        database_url,
        "SELECT to_regclass('core.account_groups') IS NOT NULL",
    )

    first_company = await _seed_company(database_url)
    second_company = await _seed_company(database_url)

    primary_hierarchy = await _insert_hierarchy(
        database_url,
        company_id=first_company,
        hierarchy_name="Primary Accounting",
        is_primary=True,
    )
    assert isinstance(primary_hierarchy, UUID)

    inactive_primary = await _insert_hierarchy(
        database_url,
        company_id=first_company,
        hierarchy_name="Historical Accounting",
        is_primary=True,
        status="INACTIVE",
    )
    assert isinstance(inactive_primary, UUID)

    second_company_hierarchy = await _insert_hierarchy(
        database_url,
        company_id=second_company,
        hierarchy_name="Primary Accounting",
        is_primary=True,
    )
    assert isinstance(second_company_hierarchy, UUID)

    await _assert_rejected(
        database_url,
        "INSERT INTO core.account_hierarchies "
        "(company_id, hierarchy_name, purpose_code, is_primary, status) "
        "VALUES (:company_id, 'Second Active Primary', 'ACCOUNTING', "
        "true, 'ACTIVE')",
        {"company_id": first_company},
    )

    await _assert_rejected(
        database_url,
        "INSERT INTO core.account_hierarchies "
        "(company_id, hierarchy_name, purpose_code, is_primary, status) "
        "VALUES (:company_id, 'Management', 'MANAGEMENT', false, 'ACTIVE')",
        {"company_id": first_company},
    )

    await _assert_rejected(
        database_url,
        "INSERT INTO core.account_hierarchies "
        "(company_id, hierarchy_name, purpose_code, is_primary, status) "
        "VALUES (:company_id, '   ', 'ACCOUNTING', false, 'ACTIVE')",
        {"company_id": first_company},
    )

    await _assert_rejected(
        database_url,
        "INSERT INTO core.account_hierarchies "
        "(company_id, hierarchy_name, purpose_code, is_primary, status) "
        "VALUES (:company_id, 'Invalid Status', 'ACCOUNTING', false, 'DRAFT')",
        {"company_id": first_company},
    )

    await _assert_rejected(
        database_url,
        "INSERT INTO core.account_hierarchies "
        "(company_id, hierarchy_name, purpose_code, is_primary, status) "
        "VALUES (:company_id, 'Primary Accounting', 'ACCOUNTING', "
        "false, 'INACTIVE')",
        {"company_id": first_company},
    )

    receivables_group = await _insert_group(
        database_url,
        company_id=first_company,
        hierarchy_id=primary_hierarchy,
        group_name="Receivables",
        group_code="AR",
    )
    assert isinstance(receivables_group, UUID)

    await _insert_group(
        database_url,
        company_id=first_company,
        hierarchy_id=primary_hierarchy,
        group_name="Uncoded Group One",
        group_code=None,
    )

    await _insert_group(
        database_url,
        company_id=first_company,
        hierarchy_id=primary_hierarchy,
        group_name="Uncoded Group Two",
        group_code=None,
    )

    await _assert_rejected(
        database_url,
        "INSERT INTO core.account_groups "
        "(company_id, hierarchy_id, group_name, group_code, status) "
        "VALUES (:company_id, :hierarchy_id, 'Receivables', "
        "'AR-OTHER', 'ACTIVE')",
        {
            "company_id": first_company,
            "hierarchy_id": primary_hierarchy,
        },
    )

    await _assert_rejected(
        database_url,
        "INSERT INTO core.account_groups "
        "(company_id, hierarchy_id, group_name, group_code, status) "
        "VALUES (:company_id, :hierarchy_id, 'Other Receivables', "
        "'AR', 'ACTIVE')",
        {
            "company_id": first_company,
            "hierarchy_id": primary_hierarchy,
        },
    )

    await _assert_rejected(
        database_url,
        "INSERT INTO core.account_groups "
        "(company_id, hierarchy_id, group_name, group_code, status) "
        "VALUES (:company_id, :hierarchy_id, '   ', "
        "'BLANK-NAME', 'ACTIVE')",
        {
            "company_id": first_company,
            "hierarchy_id": primary_hierarchy,
        },
    )

    await _assert_rejected(
        database_url,
        "INSERT INTO core.account_groups "
        "(company_id, hierarchy_id, group_name, group_code, status) "
        "VALUES (:company_id, :hierarchy_id, 'Blank Code', "
        "'   ', 'ACTIVE')",
        {
            "company_id": first_company,
            "hierarchy_id": primary_hierarchy,
        },
    )

    await _assert_rejected(
        database_url,
        "INSERT INTO core.account_groups "
        "(company_id, hierarchy_id, group_name, group_code, status) "
        "VALUES (:company_id, :hierarchy_id, 'Invalid Status Group', "
        "'INVALID-STATUS', 'DRAFT')",
        {
            "company_id": first_company,
            "hierarchy_id": primary_hierarchy,
        },
    )

    # Same-company composite FK must prevent Company A from using
    # a hierarchy owned by Company B.
    await _assert_rejected(
        database_url,
        "INSERT INTO core.account_groups "
        "(company_id, hierarchy_id, group_name, group_code, status) "
        "VALUES (:company_id, :hierarchy_id, 'Cross Company', "
        "'CROSS', 'ACTIVE')",
        {
            "company_id": first_company,
            "hierarchy_id": second_company_hierarchy,
        },
    )

    # Restrictive deletion: a hierarchy referenced by a group cannot disappear.
    await _assert_rejected(
        database_url,
        "DELETE FROM core.account_hierarchies WHERE id = :hierarchy_id",
        {"hierarchy_id": primary_hierarchy},
    )

    # Restrictive deletion also protects the owning Company.
    await _assert_rejected(
        database_url,
        "DELETE FROM core.companies WHERE id = :company_id",
        {"company_id": first_company},
    )


async def _assert_downgrade(database_url: str) -> None:
    assert not await _scalar(
        database_url,
        "SELECT to_regclass('core.account_groups') IS NOT NULL",
    )
    assert not await _scalar(
        database_url,
        "SELECT to_regclass('core.account_hierarchies') IS NOT NULL",
    )

    # 0015 objects must remain after downgrading only 0016.
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
        "SELECT to_regclass('core.gl_accounts') IS NOT NULL",
    )


def test_account_hierarchy_migration_contract(database_url: str) -> None:
    config = Config("alembic.ini")

    command.upgrade(config, "0016_account_hierarchies_groups")
    asyncio.run(_run_contract(database_url))

    command.downgrade(config, "0015_exchange_rates_fx_policies")
    asyncio.run(_assert_downgrade(database_url))