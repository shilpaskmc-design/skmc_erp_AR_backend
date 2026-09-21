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


REVISION = "0017_account_group_relationships"
PREVIOUS_REVISION = "0016_account_hierarchies_groups"


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

    try:
        command.upgrade(Config("alembic.ini"), PREVIOUS_REVISION)
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


async def _insert_relationship(
    database_url: str,
    *,
    company_id: UUID,
    hierarchy_id: UUID,
    child_group_id: UUID,
    parent_group_id: UUID,
    valid_from: date,
    valid_to: date | None,
) -> UUID:
    return await _scalar(
        database_url,
        "INSERT INTO core.account_group_relationships "
        "(company_id, hierarchy_id, child_group_id, parent_group_id, "
        "valid_from, valid_to) "
        "VALUES (:company_id, :hierarchy_id, :child_group_id, "
        ":parent_group_id, :valid_from, :valid_to) RETURNING id",
        {
            "company_id": company_id,
            "hierarchy_id": hierarchy_id,
            "child_group_id": child_group_id,
            "parent_group_id": parent_group_id,
            "valid_from": valid_from,
            "valid_to": valid_to,
        },
    )


async def _assert_schema_contract(database_url: str) -> None:
    assert await _scalar(
        database_url,
        "SELECT to_regclass('core.account_group_relationships') IS NOT NULL",
    )

    columns = await _rows(
        database_url,
        "SELECT column_name, data_type, is_nullable "
        "FROM information_schema.columns "
        "WHERE table_schema = 'core' "
        "AND table_name = 'account_group_relationships' "
        "ORDER BY ordinal_position",
    )
    assert columns == [
        ("id", "uuid", "NO"),
        ("company_id", "uuid", "NO"),
        ("hierarchy_id", "uuid", "NO"),
        ("child_group_id", "uuid", "NO"),
        ("parent_group_id", "uuid", "NO"),
        ("valid_from", "date", "NO"),
        ("valid_to", "date", "YES"),
        ("created_at", "timestamp with time zone", "NO"),
        ("updated_at", "timestamp with time zone", "NO"),
    ]

    constraints = dict(
        await _rows(
            database_url,
            "SELECT con.conname, con.contype::text "
            "FROM pg_constraint con "
            "JOIN pg_class rel ON rel.oid = con.conrelid "
            "JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace "
            "WHERE nsp.nspname = 'core' "
            "AND rel.relname = 'account_group_relationships'",
        )
    )
    expected_constraints = {
        "pk_account_group_relationships": "p",
        "ck_account_group_relationships_not_self_parent": "c",
        "ck_account_group_relationships_valid_range": "c",
        "fk_account_group_relationships_company_id_companies": "f",
        "fk_account_group_relationships_company_hierarchy": "f",
        "fk_account_group_relationships_child_group": "f",
        "fk_account_group_relationships_parent_group": "f",
        "ex_account_group_relationships_child_period_overlap": "x",
    }
    assert expected_constraints.items() <= constraints.items()
    assert "u" not in constraints.values()

    delete_actions = await _rows(
        database_url,
        "SELECT con.confdeltype::text "
        "FROM pg_constraint con "
        "JOIN pg_class rel ON rel.oid = con.conrelid "
        "JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace "
        "WHERE nsp.nspname = 'core' "
        "AND rel.relname = 'account_group_relationships' "
        "AND con.contype = 'f'",
    )
    assert len(delete_actions) == 4
    assert set(delete_actions) == {("a",)}

    assert await _scalar(
        database_url,
        "SELECT count(*) = 1 FROM pg_constraint con "
        "JOIN pg_class rel ON rel.oid = con.conrelid "
        "JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace "
        "WHERE nsp.nspname = 'core' AND rel.relname = 'account_groups' "
        "AND con.conname = 'uq_account_groups_company_hierarchy_id' "
        "AND con.contype = 'u'",
    )

    indexes = {
        row[0]
        for row in await _rows(
            database_url,
            "SELECT indexname FROM pg_indexes "
            "WHERE schemaname = 'core' "
            "AND tablename = 'account_group_relationships'",
        )
    }
    assert "ix_account_group_relationships_company_hierarchy_parent_dates" in indexes
    assert "ex_account_group_relationships_child_period_overlap" in indexes


async def _run_contract(database_url: str) -> dict[str, UUID]:
    await _assert_schema_contract(database_url)

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

    group_names = [
        "Parent A",
        "Parent B",
        "Parent C",
        "Valid Child",
        "Required Child",
        "Overlap Child",
        "Open Child",
        "History Child",
        "One Day Child",
        "Invalid Range Child",
        "Self Group",
    ]
    groups = {
        name: await _insert_group(
            database_url,
            company_id=company,
            hierarchy_id=hierarchy,
            group_name=name,
        )
        for name in group_names
    }
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

    valid_relationship = await _insert_relationship(
        database_url,
        company_id=company,
        hierarchy_id=hierarchy,
        child_group_id=groups["Valid Child"],
        parent_group_id=groups["Parent A"],
        valid_from=date(2026, 4, 1),
        valid_to=None,
    )
    assert isinstance(valid_relationship, UUID)
    assert await _scalar(
        database_url,
        "SELECT created_at IS NOT NULL AND updated_at IS NOT NULL "
        "FROM core.account_group_relationships WHERE id = :id",
        {"id": valid_relationship},
    )

    await _assert_rejected(
        database_url,
        "INSERT INTO core.account_group_relationships "
        "(company_id, hierarchy_id, child_group_id, valid_from) "
        "VALUES (:company_id, :hierarchy_id, :child_group_id, '2027-04-01')",
        {
            "company_id": company,
            "hierarchy_id": hierarchy,
            "child_group_id": groups["Required Child"],
        },
    )

    await _assert_rejected(
        database_url,
        "INSERT INTO core.account_group_relationships "
        "(company_id, hierarchy_id, child_group_id, parent_group_id, valid_from) "
        "VALUES (:company_id, :hierarchy_id, :child_group_id, "
        ":parent_group_id, '2027-04-01')",
        {
            "company_id": company,
            "hierarchy_id": hierarchy,
            "child_group_id": foreign_group,
            "parent_group_id": groups["Parent A"],
        },
    )
    await _assert_rejected(
        database_url,
        "INSERT INTO core.account_group_relationships "
        "(company_id, hierarchy_id, child_group_id, parent_group_id, valid_from) "
        "VALUES (:company_id, :hierarchy_id, :child_group_id, "
        ":parent_group_id, '2027-04-01')",
        {
            "company_id": company,
            "hierarchy_id": hierarchy,
            "child_group_id": groups["Required Child"],
            "parent_group_id": foreign_group,
        },
    )
    await _assert_rejected(
        database_url,
        "INSERT INTO core.account_group_relationships "
        "(company_id, hierarchy_id, child_group_id, parent_group_id, valid_from) "
        "VALUES (:company_id, :hierarchy_id, :child_group_id, "
        ":parent_group_id, '2027-04-01')",
        {
            "company_id": company,
            "hierarchy_id": hierarchy,
            "child_group_id": other_hierarchy_group,
            "parent_group_id": groups["Parent A"],
        },
    )
    await _assert_rejected(
        database_url,
        "INSERT INTO core.account_group_relationships "
        "(company_id, hierarchy_id, child_group_id, parent_group_id, valid_from) "
        "VALUES (:company_id, :hierarchy_id, :child_group_id, "
        ":parent_group_id, '2027-04-01')",
        {
            "company_id": company,
            "hierarchy_id": hierarchy,
            "child_group_id": groups["Required Child"],
            "parent_group_id": other_hierarchy_group,
        },
    )

    await _assert_rejected(
        database_url,
        "INSERT INTO core.account_group_relationships "
        "(company_id, hierarchy_id, child_group_id, parent_group_id, valid_from) "
        "VALUES (:company_id, :hierarchy_id, :group_id, :group_id, '2027-04-01')",
        {
            "company_id": company,
            "hierarchy_id": hierarchy,
            "group_id": groups["Self Group"],
        },
    )

    await _insert_relationship(
        database_url,
        company_id=company,
        hierarchy_id=hierarchy,
        child_group_id=groups["Overlap Child"],
        parent_group_id=groups["Parent A"],
        valid_from=date(2027, 4, 1),
        valid_to=date(2027, 12, 31),
    )
    await _assert_rejected(
        database_url,
        "INSERT INTO core.account_group_relationships "
        "(company_id, hierarchy_id, child_group_id, parent_group_id, "
        "valid_from, valid_to) VALUES (:company_id, :hierarchy_id, "
        ":child_group_id, :parent_group_id, '2027-07-01', '2028-03-31')",
        {
            "company_id": company,
            "hierarchy_id": hierarchy,
            "child_group_id": groups["Overlap Child"],
            "parent_group_id": groups["Parent B"],
        },
    )
    await _assert_rejected(
        database_url,
        "INSERT INTO core.account_group_relationships "
        "(company_id, hierarchy_id, child_group_id, parent_group_id, "
        "valid_from, valid_to) VALUES (:company_id, :hierarchy_id, "
        ":child_group_id, :parent_group_id, '2027-04-01', '2027-12-31')",
        {
            "company_id": company,
            "hierarchy_id": hierarchy,
            "child_group_id": groups["Overlap Child"],
            "parent_group_id": groups["Parent A"],
        },
    )

    await _insert_relationship(
        database_url,
        company_id=company,
        hierarchy_id=hierarchy,
        child_group_id=groups["Open Child"],
        parent_group_id=groups["Parent A"],
        valid_from=date(2028, 4, 1),
        valid_to=None,
    )
    await _assert_rejected(
        database_url,
        "INSERT INTO core.account_group_relationships "
        "(company_id, hierarchy_id, child_group_id, parent_group_id, "
        "valid_from, valid_to) VALUES (:company_id, :hierarchy_id, "
        ":child_group_id, :parent_group_id, '2029-04-01', '2030-03-31')",
        {
            "company_id": company,
            "hierarchy_id": hierarchy,
            "child_group_id": groups["Open Child"],
            "parent_group_id": groups["Parent B"],
        },
    )

    for parent_name, valid_from, valid_to in (
        ("Parent A", date(2026, 4, 1), date(2027, 3, 31)),
        ("Parent B", date(2027, 4, 1), date(2028, 3, 31)),
        ("Parent C", date(2028, 4, 1), None),
    ):
        await _insert_relationship(
            database_url,
            company_id=company,
            hierarchy_id=hierarchy,
            child_group_id=groups["History Child"],
            parent_group_id=groups[parent_name],
            valid_from=valid_from,
            valid_to=valid_to,
        )
    assert await _scalar(
        database_url,
        "SELECT count(*) FROM core.account_group_relationships "
        "WHERE child_group_id = :child_group_id",
        {"child_group_id": groups["History Child"]},
    ) == 3

    await _insert_relationship(
        database_url,
        company_id=company,
        hierarchy_id=hierarchy,
        child_group_id=groups["One Day Child"],
        parent_group_id=groups["Parent A"],
        valid_from=date(2027, 4, 1),
        valid_to=date(2027, 4, 1),
    )

    await _assert_rejected(
        database_url,
        "INSERT INTO core.account_group_relationships "
        "(company_id, hierarchy_id, child_group_id, parent_group_id, "
        "valid_from, valid_to) VALUES (:company_id, :hierarchy_id, "
        ":child_group_id, :parent_group_id, '2027-04-02', '2027-04-01')",
        {
            "company_id": company,
            "hierarchy_id": hierarchy,
            "child_group_id": groups["Invalid Range Child"],
            "parent_group_id": groups["Parent A"],
        },
    )

    await _assert_rejected(
        database_url,
        "DELETE FROM core.account_groups WHERE id = :group_id",
        {"group_id": groups["Parent A"]},
    )
    await _assert_rejected(
        database_url,
        "DELETE FROM core.account_groups WHERE id = :group_id",
        {"group_id": groups["Valid Child"]},
    )
    await _assert_rejected(
        database_url,
        "DELETE FROM core.account_hierarchies WHERE id = :hierarchy_id",
        {"hierarchy_id": hierarchy},
    )
    await _assert_rejected(
        database_url,
        "DELETE FROM core.companies WHERE id = :company_id",
        {"company_id": company},
    )

    return {
        "company_id": company,
        "hierarchy_id": hierarchy,
        "group_id": groups["Valid Child"],
    }


async def _assert_downgrade(
    database_url: str,
    state: Mapping[str, UUID],
) -> None:
    assert not await _scalar(
        database_url,
        "SELECT to_regclass('core.account_group_relationships') IS NOT NULL",
    )
    assert await _scalar(
        database_url,
        "SELECT to_regclass('core.account_hierarchies') IS NOT NULL",
    )
    assert await _scalar(
        database_url,
        "SELECT to_regclass('core.account_groups') IS NOT NULL",
    )
    assert not await _scalar(
        database_url,
        "SELECT EXISTS (SELECT 1 FROM pg_constraint con "
        "JOIN pg_class rel ON rel.oid = con.conrelid "
        "JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace "
        "WHERE nsp.nspname = 'core' AND rel.relname = 'account_groups' "
        "AND con.conname = 'uq_account_groups_company_hierarchy_id')",
    )

    original_group_constraints = {
        row[0]
        for row in await _rows(
            database_url,
            "SELECT con.conname FROM pg_constraint con "
            "JOIN pg_class rel ON rel.oid = con.conrelid "
            "JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace "
            "WHERE nsp.nspname = 'core' AND rel.relname = 'account_groups'",
        )
    }
    assert {
        "pk_account_groups",
        "ck_account_groups_name_not_blank",
        "ck_account_groups_code_not_blank",
        "ck_account_groups_status",
        "fk_account_groups_company_id_companies",
        "fk_account_groups_company_hierarchy",
        "uq_account_groups_company_hierarchy_name",
    } <= original_group_constraints

    original_indexes = {
        row[0]
        for row in await _rows(
            database_url,
            "SELECT indexname FROM pg_indexes WHERE schemaname = 'core' "
            "AND tablename IN ('account_groups', 'account_hierarchies')",
        )
    }
    assert "uq_account_groups_company_hierarchy_code" in original_indexes
    assert "uq_account_hierarchies_active_primary_accounting" in original_indexes

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
        "SELECT version_num FROM public.alembic_version",
    ) == PREVIOUS_REVISION
    assert await _scalar(
        database_url,
        "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'btree_gist')",
    )


async def _assert_reupgrade(database_url: str) -> None:
    await _assert_schema_contract(database_url)
    assert await _scalar(
        database_url,
        "SELECT version_num FROM public.alembic_version",
    ) == REVISION


def test_account_group_relationship_migration_contract(database_url: str) -> None:
    config = Config("alembic.ini")

    command.upgrade(config, REVISION)
    state = asyncio.run(_run_contract(database_url))

    command.downgrade(config, PREVIOUS_REVISION)
    asyncio.run(_assert_downgrade(database_url, state))

    command.upgrade(config, REVISION)
    asyncio.run(_assert_reupgrade(database_url))

    script = ScriptDirectory.from_config(config)
    assert len(script.get_heads()) == 1
