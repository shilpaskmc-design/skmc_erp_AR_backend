import asyncio
import os
from collections.abc import Mapping
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.engine import make_url

from skmc_erp.config import get_settings
from tests.integration.company_configuration_migration_support import (
    connection,
    execute,
    rejected,
    scalar,
)


REVISION = "0030_company_legal_name_history"
PREVIOUS_REVISION = "0029_document_numbering_configuration"


async def _safe_empty(database_url: str) -> None:
    async with connection(database_url) as value:
        if await value.scalar(text("SELECT to_regnamespace('core') IS NOT NULL")):
            pytest.fail("TEST_DATABASE_URL must point to a database without core schema")
        if await value.scalar(
            text("SELECT to_regclass('public.alembic_version') IS NOT NULL")
        ) and await value.scalar(text("SELECT count(*) FROM alembic_version")):
            pytest.fail("TEST_DATABASE_URL already has an applied Alembic revision")


async def _fetch_all(
    database_url: str,
    sql: str,
    parameters: Mapping[str, object] | None = None,
) -> list[dict[str, object]]:
    async with connection(database_url) as value:
        result = await value.execute(text(sql), parameters or {})
        return [dict(row) for row in result.mappings().all()]


async def _seed_existing_company(database_url: str) -> UUID:
    tenant_id = uuid4()
    company_id = uuid4()
    await execute(
        database_url,
        "INSERT INTO core.tenants (id, name, status) "
        "VALUES (:id, 'Legal Name History Tenant', 'ACTIVE')",
        {"id": tenant_id},
    )
    await execute(
        database_url,
        """
        INSERT INTO core.companies (
            id, tenant_id, legal_name, status, created_at, updated_at
        ) VALUES (
            :id, :tenant_id, 'Original Legal Name', 'DRAFT',
            '2026-04-10 08:30:00+00', '2026-04-10 08:30:00+00'
        )
        """,
        {"id": company_id, "tenant_id": tenant_id},
    )
    return company_id


async def _exercise_contract(database_url: str, company_id: UUID) -> None:
    columns = await _fetch_all(
        database_url,
        """
        SELECT column_name, data_type, character_maximum_length,
               is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = 'core'
          AND table_name = 'company_legal_name_versions'
        ORDER BY ordinal_position
        """,
    )
    assert [
        (
            row["column_name"],
            row["data_type"],
            row["character_maximum_length"],
            row["is_nullable"],
        )
        for row in columns
    ] == [
        ("id", "uuid", None, "NO"),
        ("company_id", "uuid", None, "NO"),
        ("legal_name", "character varying", 255, "NO"),
        ("valid_from", "date", None, "NO"),
        ("valid_to", "date", None, "YES"),
        ("created_at", "timestamp with time zone", None, "NO"),
    ]
    assert "gen_random_uuid()" in str(columns[0]["column_default"])
    assert columns[1]["column_default"] is None
    assert columns[2]["column_default"] is None
    assert columns[3]["column_default"] is None
    assert columns[4]["column_default"] is None
    assert columns[5]["column_default"] == "CURRENT_TIMESTAMP"

    constraints = await _fetch_all(
        database_url,
        """
        SELECT con.conname,
               con.contype::text AS contype,
               con.confdeltype::text AS confdeltype,
               pg_get_constraintdef(con.oid) AS definition
        FROM pg_constraint con
        JOIN pg_class rel ON rel.oid = con.conrelid
        JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
        WHERE nsp.nspname = 'core'
          AND rel.relname = 'company_legal_name_versions'
          AND con.contype IN ('p', 'c', 'f', 'x', 'u')
        ORDER BY con.conname
        """,
    )
    assert {row["conname"] for row in constraints} == {
        "ck_company_legal_name_versions_date_order",
        "ck_company_legal_name_versions_legal_name_not_blank",
        "ex_company_legal_name_versions_company_effective_range",
        "fk_company_legal_name_versions_company_id_companies",
        "pk_company_legal_name_versions",
    }
    assert {
        row["conname"]: row["confdeltype"]
        for row in constraints
        if row["contype"] == "f"
    } == {
        "fk_company_legal_name_versions_company_id_companies": "a"
    }
    definitions = {
        row["conname"]: str(row["definition"]) for row in constraints
    }
    assert "daterange(valid_from, valid_to, '[]'::text) WITH &&" in definitions[
        "ex_company_legal_name_versions_company_effective_range"
    ]

    indexes = await _fetch_all(
        database_url,
        """
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE schemaname = 'core'
          AND tablename = 'company_legal_name_versions'
        ORDER BY indexname
        """,
    )
    assert {row["indexname"] for row in indexes} == {
        "ex_company_legal_name_versions_company_effective_range",
        "ix_company_legal_name_versions_company_valid_from",
        "pk_company_legal_name_versions",
        "uq_company_legal_name_versions_open_company",
    }
    open_index = next(
        str(row["indexdef"])
        for row in indexes
        if row["indexname"]
        == "uq_company_legal_name_versions_open_company"
    )
    assert "UNIQUE INDEX" in open_index
    assert "WHERE (valid_to IS NULL)" in open_index

    backfill = await _fetch_all(
        database_url,
        """
        SELECT legal_name, valid_from, valid_to, created_at
        FROM core.company_legal_name_versions
        WHERE company_id = :company_id
        """,
        {"company_id": company_id},
    )
    assert len(backfill) == 1
    assert backfill[0]["legal_name"] == "Original Legal Name"
    assert str(backfill[0]["valid_from"]) == "2026-04-10"
    assert backfill[0]["valid_to"] is None
    assert str(backfill[0]["created_at"]).startswith("2026-04-10 08:30:00")

    await execute(
        database_url,
        "UPDATE core.company_legal_name_versions SET valid_to = '2026-04-30' "
        "WHERE company_id = :company_id",
        {"company_id": company_id},
    )
    await execute(
        database_url,
        """
        INSERT INTO core.company_legal_name_versions (
            company_id, legal_name, valid_from
        ) VALUES (:company_id, 'Current Legal Name', '2026-05-01')
        """,
        {"company_id": company_id},
    )
    await rejected(
        database_url,
        """
        INSERT INTO core.company_legal_name_versions (
            company_id, legal_name, valid_from, valid_to
        ) VALUES (:company_id, 'Overlap', '2026-04-15', '2026-05-15')
        """,
        {"company_id": company_id},
    )
    await rejected(
        database_url,
        "INSERT INTO core.company_legal_name_versions "
        "(company_id, valid_from, valid_to) "
        "VALUES (:company_id, '2026-06-01', '2026-06-01')",
        {"company_id": company_id},
    )
    await rejected(
        database_url,
        "INSERT INTO core.company_legal_name_versions "
        "(company_id, legal_name, valid_to) "
        "VALUES (:company_id, 'Missing Start', '2026-06-01')",
        {"company_id": company_id},
    )
    await rejected(
        database_url,
        """
        INSERT INTO core.company_legal_name_versions (
            company_id, legal_name, valid_from
        ) VALUES (:company_id, 'Second Open', '2026-06-01')
        """,
        {"company_id": company_id},
    )
    await rejected(
        database_url,
        """
        INSERT INTO core.company_legal_name_versions (
            company_id, legal_name, valid_from, valid_to
        ) VALUES (:company_id, 'Bad Range', '2026-06-02', '2026-06-01')
        """,
        {"company_id": company_id},
    )
    await rejected(
        database_url,
        """
        INSERT INTO core.company_legal_name_versions (
            company_id, legal_name, valid_from, valid_to
        ) VALUES (:company_id, '   ', '2026-06-01', '2026-06-01')
        """,
        {"company_id": company_id},
    )
    await rejected(
        database_url,
        """
        INSERT INTO core.company_legal_name_versions (
            company_id, legal_name, valid_from
        ) VALUES (:company_id, 'Missing Company', '2026-06-01')
        """,
        {"company_id": uuid4()},
    )
    await rejected(
        database_url,
        "DELETE FROM core.companies WHERE id = :company_id",
        {"company_id": company_id},
    )


def test_company_legal_name_history_migration_contract() -> None:
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
        command.upgrade(config, PREVIOUS_REVISION)
        company_id = asyncio.run(_seed_existing_company(database_url))
        command.upgrade(config, REVISION)
        assert asyncio.run(
            scalar(database_url, "SELECT version_num FROM alembic_version")
        ) == REVISION
        asyncio.run(_exercise_contract(database_url, company_id))

        command.downgrade(config, PREVIOUS_REVISION)
        assert asyncio.run(
            scalar(database_url, "SELECT version_num FROM alembic_version")
        ) == PREVIOUS_REVISION
        assert not asyncio.run(
            scalar(
                database_url,
                "SELECT to_regclass('core.company_legal_name_versions') "
                "IS NOT NULL",
            )
        )
        assert asyncio.run(
            scalar(
                database_url,
                "SELECT count(*) FROM core.companies WHERE id = :id",
                {"id": company_id},
            )
        ) == 1

        command.upgrade(config, REVISION)
        assert asyncio.run(
            scalar(database_url, "SELECT version_num FROM alembic_version")
        ) == REVISION
        assert asyncio.run(
            scalar(
                database_url,
                "SELECT count(*) FROM core.company_legal_name_versions "
                "WHERE company_id = :id",
                {"id": company_id},
            )
        ) == 1
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
