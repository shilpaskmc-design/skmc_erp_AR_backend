import asyncio
import os
from collections.abc import AsyncIterator, Iterator, Mapping
from contextlib import asynccontextmanager
from datetime import date
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from skmc_erp.config import get_settings


REVISION = "0018_gl_account_group_mappings"
PREVIOUS_REVISION = "0017_account_group_relationships"


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
    config = Config("alembic.ini")

    try:
        command.upgrade(config, PREVIOUS_REVISION)
        yield value
    finally:
        try:
            command.downgrade(config, "base")
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


async def _rows(
    database_url: str,
    sql: str,
    parameters: Mapping[str, object] | None = None,
) -> list[tuple[object, ...]]:
    async with _connection(database_url) as connection:
        async with connection.begin():
            result = await connection.execute(text(sql), parameters or {})
            return [tuple(row) for row in result.all()]


async def _assert_rejected(
    database_url: str,
    sql: str,
    parameters: Mapping[str, object] | None = None,
) -> None:
    with pytest.raises(DBAPIError):
        await _execute(database_url, sql, parameters)


async def _parent_constraint_snapshot(
    database_url: str,
) -> set[tuple[object, ...]]:
    return set(
        await _rows(
            database_url,
            "SELECT rel.relname, con.conname, con.contype::text "
            "FROM pg_constraint con "
            "JOIN pg_class rel ON rel.oid = con.conrelid "
            "JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace "
            "WHERE nsp.nspname = 'core' "
            "AND rel.relname IN "
            "('account_hierarchies', 'account_groups', 'gl_accounts')",
        )
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
        "INSERT INTO core.companies (tenant_id, legal_name, status) "
        "VALUES (:tenant_id, :name, 'DRAFT') RETURNING id",
        {"tenant_id": tenant_id, "name": f"Company {uuid4()}"},
    )


async def _insert_hierarchy(
    database_url: str,
    *,
    company_id: UUID,
    hierarchy_name: str,
) -> UUID:
    return await _scalar(
        database_url,
        "INSERT INTO core.account_hierarchies "
        "(company_id, hierarchy_name, purpose_code, is_primary, status) "
        "VALUES (:company_id, :hierarchy_name, 'ACCOUNTING', false, 'ACTIVE') "
        "RETURNING id",
        {"company_id": company_id, "hierarchy_name": hierarchy_name},
    )


async def _insert_group(
    database_url: str,
    *,
    company_id: UUID,
    hierarchy_id: UUID,
    group_name: str,
) -> UUID:
    return await _scalar(
        database_url,
        "INSERT INTO core.account_groups "
        "(company_id, hierarchy_id, group_name, group_code, status) "
        "VALUES (:company_id, :hierarchy_id, :group_name, NULL, 'ACTIVE') "
        "RETURNING id",
        {
            "company_id": company_id,
            "hierarchy_id": hierarchy_id,
            "group_name": group_name,
        },
    )


async def _insert_gl_account(
    database_url: str,
    *,
    company_id: UUID,
    account_name: str,
) -> UUID:
    return await _scalar(
        database_url,
        "INSERT INTO core.gl_accounts "
        "(company_id, account_name, valid_from, status) "
        "VALUES (:company_id, :account_name, '2026-04-01', 'ACTIVE') "
        "RETURNING id",
        {"company_id": company_id, "account_name": account_name},
    )


async def _insert_mapping(
    database_url: str,
    *,
    company_id: UUID,
    hierarchy_id: UUID,
    gl_account_id: UUID,
    account_group_id: UUID | None,
    valid_from: date,
    valid_to: date | None,
) -> UUID:
    return await _scalar(
        database_url,
        "INSERT INTO core.gl_account_group_mappings "
        "(company_id, hierarchy_id, gl_account_id, account_group_id, "
        "valid_from, valid_to) "
        "VALUES (:company_id, :hierarchy_id, :gl_account_id, "
        ":account_group_id, :valid_from, :valid_to) RETURNING id",
        {
            "company_id": company_id,
            "hierarchy_id": hierarchy_id,
            "gl_account_id": gl_account_id,
            "account_group_id": account_group_id,
            "valid_from": valid_from,
            "valid_to": valid_to,
        },
    )


async def _assert_schema_contract(database_url: str) -> None:
    assert await _scalar(
        database_url,
        "SELECT to_regclass('core.gl_account_group_mappings') IS NOT NULL",
    )

    columns = await _rows(
        database_url,
        "SELECT column_name, data_type, is_nullable, column_default "
        "FROM information_schema.columns "
        "WHERE table_schema = 'core' "
        "AND table_name = 'gl_account_group_mappings' "
        "ORDER BY ordinal_position",
    )
    assert [(row[0], row[1], row[2]) for row in columns] == [
        ("id", "uuid", "NO"),
        ("company_id", "uuid", "NO"),
        ("hierarchy_id", "uuid", "NO"),
        ("gl_account_id", "uuid", "NO"),
        ("account_group_id", "uuid", "YES"),
        ("valid_from", "date", "NO"),
        ("valid_to", "date", "YES"),
        ("created_at", "timestamp with time zone", "NO"),
        ("updated_at", "timestamp with time zone", "NO"),
    ]
    defaults = {row[0]: row[3] for row in columns}
    assert defaults == {
        "id": "gen_random_uuid()",
        "company_id": None,
        "hierarchy_id": None,
        "gl_account_id": None,
        "account_group_id": None,
        "valid_from": None,
        "valid_to": None,
        "created_at": "CURRENT_TIMESTAMP",
        "updated_at": "CURRENT_TIMESTAMP",
    }

    constraints = dict(
        await _rows(
            database_url,
            "SELECT con.conname, con.contype::text "
            "FROM pg_constraint con "
            "JOIN pg_class rel ON rel.oid = con.conrelid "
            "JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace "
            "WHERE nsp.nspname = 'core' "
            "AND rel.relname = 'gl_account_group_mappings' "
            "AND con.contype IN ('p', 'c', 'f', 'x', 'u')",
        )
    )
    assert constraints == {
        "pk_gl_account_group_mappings": "p",
        "ck_gl_account_group_mappings_valid_range": "c",
        "fk_gl_account_group_mappings_company_id_companies": "f",
        "fk_gl_account_group_mappings_company_hierarchy": "f",
        "fk_gl_account_group_mappings_company_gl_account": "f",
        "fk_gl_account_group_mappings_company_hierarchy_group": "f",
        "ex_gl_account_group_mappings_gl_hierarchy_period_overlap": "x",
    }

    foreign_key_actions = await _rows(
        database_url,
        "SELECT con.confdeltype::text, con.confmatchtype::text "
        "FROM pg_constraint con "
        "JOIN pg_class rel ON rel.oid = con.conrelid "
        "JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace "
        "WHERE nsp.nspname = 'core' "
        "AND rel.relname = 'gl_account_group_mappings' "
        "AND con.contype = 'f'",
    )
    assert len(foreign_key_actions) == 4
    assert set(foreign_key_actions) == {("a", "s")}

    exclusion_definition = await _scalar(
        database_url,
        "SELECT pg_get_constraintdef(con.oid) "
        "FROM pg_constraint con "
        "JOIN pg_class rel ON rel.oid = con.conrelid "
        "JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace "
        "WHERE nsp.nspname = 'core' "
        "AND rel.relname = 'gl_account_group_mappings' "
        "AND con.conname = "
        "'ex_gl_account_group_mappings_gl_hierarchy_period_overlap'",
    )
    assert "gl_account_id WITH =" in exclusion_definition
    assert "hierarchy_id WITH =" in exclusion_definition
    assert "daterange(valid_from, valid_to, '[]'::text) WITH &&" in (
        exclusion_definition
    )
    assert "account_group_id" not in exclusion_definition
    assert "company_id" not in exclusion_definition

    indexes = dict(
        await _rows(
            database_url,
            "SELECT indexname, indexdef FROM pg_indexes "
            "WHERE schemaname = 'core' "
            "AND tablename = 'gl_account_group_mappings'",
        )
    )
    assert set(indexes) == {
        "pk_gl_account_group_mappings",
        "ex_gl_account_group_mappings_gl_hierarchy_period_overlap",
        "ix_gl_account_group_mappings_company_hierarchy_group_dates",
    }
    assert (
        "(company_id, hierarchy_id, account_group_id, valid_from, valid_to)"
        in indexes[
            "ix_gl_account_group_mappings_company_hierarchy_group_dates"
        ]
    )


async def _run_contract(
    database_url: str,
    parent_constraints: set[tuple[object, ...]],
) -> dict[str, UUID]:
    await _assert_schema_contract(database_url)
    assert await _parent_constraint_snapshot(database_url) == parent_constraints

    company = await _seed_company(database_url)
    other_company = await _seed_company(database_url)
    hierarchy = await _insert_hierarchy(
        database_url,
        company_id=company,
        hierarchy_name="Primary Accounting",
    )
    other_hierarchy = await _insert_hierarchy(
        database_url,
        company_id=company,
        hierarchy_name="Secondary Accounting",
    )
    foreign_hierarchy = await _insert_hierarchy(
        database_url,
        company_id=other_company,
        hierarchy_name="Foreign Accounting",
    )

    group_a = await _insert_group(
        database_url,
        company_id=company,
        hierarchy_id=hierarchy,
        group_name="Group A",
    )
    group_b = await _insert_group(
        database_url,
        company_id=company,
        hierarchy_id=hierarchy,
        group_name="Group B",
    )
    group_c = await _insert_group(
        database_url,
        company_id=company,
        hierarchy_id=hierarchy,
        group_name="Group C",
    )
    delete_group = await _insert_group(
        database_url,
        company_id=company,
        hierarchy_id=hierarchy,
        group_name="Delete Protected Group",
    )
    other_hierarchy_group = await _insert_group(
        database_url,
        company_id=company,
        hierarchy_id=other_hierarchy,
        group_name="Other Hierarchy Group",
    )
    foreign_group = await _insert_group(
        database_url,
        company_id=other_company,
        hierarchy_id=foreign_hierarchy,
        group_name="Foreign Group",
    )

    relationship_id = await _scalar(
        database_url,
        "INSERT INTO core.account_group_relationships "
        "(company_id, hierarchy_id, child_group_id, parent_group_id, "
        "valid_from) VALUES (:company_id, :hierarchy_id, :child_group_id, "
        ":parent_group_id, '2026-04-01') RETURNING id",
        {
            "company_id": company,
            "hierarchy_id": hierarchy,
            "child_group_id": group_c,
            "parent_group_id": group_b,
        },
    )

    gl_names = (
        "Valid Group GL",
        "Valid Root GL",
        "Unplaced GL",
        "Cross Company Group GL",
        "Cross Hierarchy GL",
        "Invalid Hierarchy GL",
        "Group Group Overlap GL",
        "Group Root Overlap GL",
        "Root Root Overlap GL",
        "Adjacent Group Group GL",
        "Adjacent Root Group GL",
        "Adjacent Group Root GL",
        "One Day GL",
        "Open Ended GL",
        "Invalid Range GL",
        "Historical GL",
        "Delete Protected GL",
    )
    gl_accounts = {
        name: await _insert_gl_account(
            database_url,
            company_id=company,
            account_name=name,
        )
        for name in gl_names
    }
    foreign_gl = await _insert_gl_account(
        database_url,
        company_id=other_company,
        account_name="Foreign GL",
    )

    valid_group_mapping = await _insert_mapping(
        database_url,
        company_id=company,
        hierarchy_id=hierarchy,
        gl_account_id=gl_accounts["Valid Group GL"],
        account_group_id=group_a,
        valid_from=date(2026, 4, 1),
        valid_to=None,
    )
    valid_root_mapping = await _insert_mapping(
        database_url,
        company_id=company,
        hierarchy_id=hierarchy,
        gl_account_id=gl_accounts["Valid Root GL"],
        account_group_id=None,
        valid_from=date(2026, 4, 1),
        valid_to=None,
    )
    assert isinstance(valid_group_mapping, UUID)
    assert isinstance(valid_root_mapping, UUID)
    assert await _scalar(
        database_url,
        "SELECT account_group_id IS NULL "
        "AND created_at IS NOT NULL AND updated_at IS NOT NULL "
        "FROM core.gl_account_group_mappings WHERE id = :id",
        {"id": valid_root_mapping},
    )
    assert await _scalar(
        database_url,
        "SELECT count(*) FROM core.gl_account_group_mappings "
        "WHERE gl_account_id = :gl_account_id",
        {"gl_account_id": gl_accounts["Unplaced GL"]},
    ) == 0

    await _assert_rejected(
        database_url,
        "INSERT INTO core.gl_account_group_mappings "
        "(company_id, hierarchy_id, gl_account_id, account_group_id, valid_from) "
        "VALUES (:company_id, :hierarchy_id, :gl_account_id, "
        ":account_group_id, '2027-04-01')",
        {
            "company_id": company,
            "hierarchy_id": hierarchy,
            "gl_account_id": foreign_gl,
            "account_group_id": group_a,
        },
    )
    await _assert_rejected(
        database_url,
        "INSERT INTO core.gl_account_group_mappings "
        "(company_id, hierarchy_id, gl_account_id, account_group_id, valid_from) "
        "VALUES (:company_id, :hierarchy_id, :gl_account_id, "
        ":account_group_id, '2027-04-01')",
        {
            "company_id": company,
            "hierarchy_id": hierarchy,
            "gl_account_id": gl_accounts["Cross Company Group GL"],
            "account_group_id": foreign_group,
        },
    )
    await _assert_rejected(
        database_url,
        "INSERT INTO core.gl_account_group_mappings "
        "(company_id, hierarchy_id, gl_account_id, account_group_id, valid_from) "
        "VALUES (:company_id, :hierarchy_id, :gl_account_id, "
        ":account_group_id, '2027-04-01')",
        {
            "company_id": company,
            "hierarchy_id": hierarchy,
            "gl_account_id": gl_accounts["Cross Hierarchy GL"],
            "account_group_id": other_hierarchy_group,
        },
    )
    await _assert_rejected(
        database_url,
        "INSERT INTO core.gl_account_group_mappings "
        "(company_id, hierarchy_id, gl_account_id, account_group_id, valid_from) "
        "VALUES (:company_id, :hierarchy_id, :gl_account_id, NULL, "
        "'2027-04-01')",
        {
            "company_id": company,
            "hierarchy_id": uuid4(),
            "gl_account_id": gl_accounts["Invalid Hierarchy GL"],
        },
    )

    overlap_cases = (
        ("Group Group Overlap GL", group_a, group_b),
        ("Group Root Overlap GL", group_a, None),
        ("Root Root Overlap GL", None, None),
    )
    for gl_name, first_group, second_group in overlap_cases:
        await _insert_mapping(
            database_url,
            company_id=company,
            hierarchy_id=hierarchy,
            gl_account_id=gl_accounts[gl_name],
            account_group_id=first_group,
            valid_from=date(2027, 4, 1),
            valid_to=date(2027, 12, 31),
        )
        await _assert_rejected(
            database_url,
            "INSERT INTO core.gl_account_group_mappings "
            "(company_id, hierarchy_id, gl_account_id, account_group_id, "
            "valid_from, valid_to) VALUES (:company_id, :hierarchy_id, "
            ":gl_account_id, :account_group_id, '2027-07-01', '2028-03-31')",
            {
                "company_id": company,
                "hierarchy_id": hierarchy,
                "gl_account_id": gl_accounts[gl_name],
                "account_group_id": second_group,
            },
        )

    adjacent_cases = (
        ("Adjacent Group Group GL", group_a, group_b),
        ("Adjacent Root Group GL", None, group_a),
        ("Adjacent Group Root GL", group_a, None),
    )
    for gl_name, old_group, new_group in adjacent_cases:
        await _insert_mapping(
            database_url,
            company_id=company,
            hierarchy_id=hierarchy,
            gl_account_id=gl_accounts[gl_name],
            account_group_id=old_group,
            valid_from=date(2026, 4, 1),
            valid_to=date(2027, 3, 31),
        )
        await _insert_mapping(
            database_url,
            company_id=company,
            hierarchy_id=hierarchy,
            gl_account_id=gl_accounts[gl_name],
            account_group_id=new_group,
            valid_from=date(2027, 4, 1),
            valid_to=None,
        )

    await _insert_mapping(
        database_url,
        company_id=company,
        hierarchy_id=hierarchy,
        gl_account_id=gl_accounts["One Day GL"],
        account_group_id=group_a,
        valid_from=date(2027, 4, 1),
        valid_to=date(2027, 4, 1),
    )
    await _insert_mapping(
        database_url,
        company_id=company,
        hierarchy_id=hierarchy,
        gl_account_id=gl_accounts["Open Ended GL"],
        account_group_id=None,
        valid_from=date(2027, 4, 1),
        valid_to=None,
    )
    await _assert_rejected(
        database_url,
        "INSERT INTO core.gl_account_group_mappings "
        "(company_id, hierarchy_id, gl_account_id, account_group_id, "
        "valid_from, valid_to) VALUES (:company_id, :hierarchy_id, "
        ":gl_account_id, :account_group_id, '2027-04-02', '2027-04-01')",
        {
            "company_id": company,
            "hierarchy_id": hierarchy,
            "gl_account_id": gl_accounts["Invalid Range GL"],
            "account_group_id": group_a,
        },
    )

    for account_group_id, valid_from, valid_to in (
        (group_a, date(2026, 4, 1), date(2027, 3, 31)),
        (None, date(2027, 4, 1), date(2028, 3, 31)),
        (group_c, date(2028, 4, 1), None),
    ):
        await _insert_mapping(
            database_url,
            company_id=company,
            hierarchy_id=hierarchy,
            gl_account_id=gl_accounts["Historical GL"],
            account_group_id=account_group_id,
            valid_from=valid_from,
            valid_to=valid_to,
        )
    assert await _scalar(
        database_url,
        "SELECT count(*) FROM core.gl_account_group_mappings "
        "WHERE gl_account_id = :gl_account_id",
        {"gl_account_id": gl_accounts["Historical GL"]},
    ) == 3

    await _insert_mapping(
        database_url,
        company_id=company,
        hierarchy_id=hierarchy,
        gl_account_id=gl_accounts["Delete Protected GL"],
        account_group_id=delete_group,
        valid_from=date(2026, 4, 1),
        valid_to=date(2026, 4, 1),
    )
    await _assert_rejected(
        database_url,
        "DELETE FROM core.gl_accounts WHERE id = :id",
        {"id": gl_accounts["Delete Protected GL"]},
    )
    await _assert_rejected(
        database_url,
        "DELETE FROM core.account_groups WHERE id = :id",
        {"id": delete_group},
    )
    await _assert_rejected(
        database_url,
        "DELETE FROM core.account_hierarchies WHERE id = :id",
        {"id": hierarchy},
    )
    await _assert_rejected(
        database_url,
        "DELETE FROM core.companies WHERE id = :id",
        {"id": company},
    )

    return {
        "company_id": company,
        "hierarchy_id": hierarchy,
        "group_id": group_a,
        "gl_account_id": gl_accounts["Valid Group GL"],
        "relationship_id": relationship_id,
    }


async def _assert_downgrade(
    database_url: str,
    state: Mapping[str, UUID],
    parent_constraints: set[tuple[object, ...]],
) -> None:
    assert not await _scalar(
        database_url,
        "SELECT to_regclass('core.gl_account_group_mappings') IS NOT NULL",
    )
    for table_name in (
        "account_group_relationships",
        "account_hierarchies",
        "account_groups",
        "gl_accounts",
    ):
        assert await _scalar(
            database_url,
            f"SELECT to_regclass('core.{table_name}') IS NOT NULL",
        )

    assert await _parent_constraint_snapshot(database_url) == parent_constraints
    assert await _scalar(
        database_url,
        "SELECT count(*) = 1 FROM core.account_hierarchies WHERE id = :id",
        {"id": state["hierarchy_id"]},
    )
    assert await _scalar(
        database_url,
        "SELECT count(*) = 1 FROM core.account_groups WHERE id = :id",
        {"id": state["group_id"]},
    )
    assert await _scalar(
        database_url,
        "SELECT count(*) = 1 FROM core.gl_accounts WHERE id = :id",
        {"id": state["gl_account_id"]},
    )
    assert await _scalar(
        database_url,
        "SELECT count(*) = 1 FROM core.account_group_relationships "
        "WHERE id = :id",
        {"id": state["relationship_id"]},
    )
    assert await _scalar(
        database_url,
        "SELECT version_num FROM public.alembic_version",
    ) == PREVIOUS_REVISION
    assert await _scalar(
        database_url,
        "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'btree_gist')",
    )


async def _assert_reupgrade(
    database_url: str,
    parent_constraints: set[tuple[object, ...]],
) -> None:
    await _assert_schema_contract(database_url)
    assert await _parent_constraint_snapshot(database_url) == parent_constraints
    assert await _scalar(
        database_url,
        "SELECT version_num FROM public.alembic_version",
    ) == REVISION


def test_gl_account_group_mapping_migration_contract(database_url: str) -> None:
    config = Config("alembic.ini")
    parent_constraints = asyncio.run(_parent_constraint_snapshot(database_url))

    command.upgrade(config, REVISION)
    state = asyncio.run(_run_contract(database_url, parent_constraints))

    command.downgrade(config, PREVIOUS_REVISION)
    asyncio.run(_assert_downgrade(database_url, state, parent_constraints))

    command.upgrade(config, REVISION)
    asyncio.run(_assert_reupgrade(database_url, parent_constraints))

    script = ScriptDirectory.from_config(config)
    assert len(script.get_heads()) == 1
