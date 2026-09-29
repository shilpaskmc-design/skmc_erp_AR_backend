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
from sqlalchemy.exc import DBAPIError

from skmc_erp.config import get_settings
from tests.integration.company_configuration_migration_support import (
    connection,
    execute,
    scalar,
)

REVISION = "0026_company_location_versions"
PREVIOUS_REVISION = "0025_company_access_foundation"


async def _safe_empty(database_url: str) -> None:
    async with connection(database_url) as value:
        if await value.scalar(text("SELECT to_regnamespace('core') IS NOT NULL")):
            pytest.fail("TEST_DATABASE_URL must point to a database without core schema")
        if await value.scalar(
            text("SELECT to_regclass('public.alembic_version') IS NOT NULL")
        ) and await value.scalar(text("SELECT count(*) FROM public.alembic_version")):
            pytest.fail(
                "TEST_DATABASE_URL already has an applied Alembic revision"
            )


async def _fetch_all(
    database_url: str,
    sql: str,
    parameters: Mapping[str, object] | None = None,
) -> list[dict[str, object]]:
    async with connection(database_url) as value:
        result = await value.execute(text(sql), parameters or {})
        return [dict(row) for row in result.mappings().all()]


async def _rejected(
    database_url: str,
    sql: str,
    parameters: Mapping[str, object] | None = None,
) -> None:
    with pytest.raises(DBAPIError):
        await execute(database_url, sql, parameters)


async def _seed_existing_location(database_url: str) -> UUID:
    tenant_id = uuid4()
    company_id = uuid4()
    location_id = uuid4()
    await execute(
        database_url,
        "INSERT INTO core.tenants (id, name, status) "
        "VALUES (:tenant_id, 'Location Version Tenant', 'ACTIVE')",
        {"tenant_id": tenant_id},
    )
    await execute(
        database_url,
        "INSERT INTO core.companies (id, tenant_id, legal_name, status) "
        "VALUES (:company_id, :tenant_id, 'Location Version Company', 'DRAFT')",
        {"tenant_id": tenant_id, "company_id": company_id},
    )
    await execute(
        database_url,
        "INSERT INTO core.countries (code, name, status) VALUES "
        "('IN', 'India', 'ACTIVE'), ('US', 'United States', 'ACTIVE')",
    )
    await execute(
        database_url,
        """
        INSERT INTO core.country_subdivisions
            (country_code, code, name, subdivision_type, status)
        VALUES
            ('IN', 'IN-UP', 'Uttar Pradesh', 'STATE', 'ACTIVE'),
            ('US', 'US-CA', 'California', 'STATE', 'ACTIVE')
        """,
    )
    await execute(
        database_url,
        """
        INSERT INTO core.company_locations (
            id,
            company_id,
            location_name,
            address_line_1,
            address_line_2,
            city,
            district,
            subdivision_code,
            country_code,
            postal_code,
            is_branch,
            status,
            created_at,
            updated_at
        ) VALUES (
            :location_id,
            :company_id,
            'Existing Noida Branch',
            'Sector 62',
            'Tower A',
            'Noida',
            'Gautam Buddha Nagar',
            'IN-UP',
            'IN',
            '201309',
            true,
            'ACTIVE',
            '2026-04-10 08:30:00+00',
            '2026-04-10 08:30:00+00'
        )
        """,
        {
            "company_id": company_id,
            "location_id": location_id,
        },
    )
    return location_id


async def _exercise_contract(database_url: str, location_id: UUID) -> None:
    columns = await _fetch_all(
        database_url,
        """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = 'core'
          AND table_name = 'company_location_versions'
        ORDER BY ordinal_position
        """,
    )
    assert [column["column_name"] for column in columns] == [
        "id",
        "company_location_id",
        "address_line_1",
        "address_line_2",
        "city",
        "district",
        "subdivision_code",
        "country_code",
        "postal_code",
        "valid_from",
        "valid_to",
        "created_at",
    ]
    assert [column["is_nullable"] for column in columns] == [
        "NO",
        "NO",
        "NO",
        "YES",
        "NO",
        "YES",
        "YES",
        "NO",
        "YES",
        "NO",
        "YES",
        "NO",
    ]

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
          AND rel.relname = 'company_location_versions'
          AND con.contype IN ('p', 'c', 'f', 'x', 'u')
        ORDER BY con.conname
        """,
    )
    assert {row["conname"] for row in constraints} == {
        "ck_company_location_versions_address_line_1_not_blank",
        "ck_company_location_versions_address_line_2_not_blank",
        "ck_company_location_versions_city_not_blank",
        "ck_company_location_versions_country_code_format",
        "ck_company_location_versions_date_order",
        "ck_company_location_versions_district_not_blank",
        "ck_company_location_versions_postal_code_not_blank",
        "ex_company_location_versions_location_effective_range",
        "fk_company_location_versions_country_code_countries",
        "fk_company_location_versions_country_subdivision",
        "fk_company_location_versions_location_id_locations",
        "pk_company_location_versions",
    }
    definitions = {
        row["conname"]: str(row["definition"]) for row in constraints
    }
    assert {
        row["conname"]: row["confdeltype"]
        for row in constraints
        if row["contype"] == "f"
    } == {
        "fk_company_location_versions_country_code_countries": "a",
        "fk_company_location_versions_country_subdivision": "a",
        "fk_company_location_versions_location_id_locations": "a",
    }
    assert "daterange(valid_from, valid_to, '[]'::text) WITH &&" in definitions[
        "ex_company_location_versions_location_effective_range"
    ]

    indexes = await _fetch_all(
        database_url,
        """
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE schemaname = 'core'
          AND tablename = 'company_location_versions'
        ORDER BY indexname
        """,
    )
    assert {row["indexname"] for row in indexes} == {
        "ex_company_location_versions_location_effective_range",
        "ix_company_location_versions_location_valid_from",
        "pk_company_location_versions",
        "uq_company_location_versions_open_location",
    }
    open_index = next(
        str(row["indexdef"])
        for row in indexes
        if row["indexname"] == "uq_company_location_versions_open_location"
    )
    assert "UNIQUE INDEX" in open_index
    assert "WHERE (valid_to IS NULL)" in open_index

    backfill = await _fetch_all(
        database_url,
        """
        SELECT address_line_1, address_line_2, city, district,
               subdivision_code, country_code, postal_code,
               valid_from, valid_to, created_at
        FROM core.company_location_versions
        WHERE company_location_id = :location_id
        """,
        {"location_id": location_id},
    )
    assert len(backfill) == 1
    assert backfill[0]["address_line_1"] == "Sector 62"
    assert backfill[0]["address_line_2"] == "Tower A"
    assert backfill[0]["city"] == "Noida"
    assert backfill[0]["district"] == "Gautam Buddha Nagar"
    assert backfill[0]["subdivision_code"] == "IN-UP"
    assert backfill[0]["country_code"] == "IN"
    assert backfill[0]["postal_code"] == "201309"
    assert str(backfill[0]["valid_from"]) == "2026-04-10"
    assert backfill[0]["valid_to"] is None

    await execute(
        database_url,
        """
        UPDATE core.company_location_versions
        SET valid_to = '2026-04-30'
        WHERE company_location_id = :location_id
        """,
        {"location_id": location_id},
    )
    await execute(
        database_url,
        """
        INSERT INTO core.company_location_versions (
            company_location_id, address_line_1, city,
            subdivision_code, country_code, valid_from
        ) VALUES (
            :location_id, 'Sector 63', 'Noida', 'IN-UP', 'IN', '2026-05-01'
        )
        """,
        {"location_id": location_id},
    )
    await _rejected(
        database_url,
        """
        INSERT INTO core.company_location_versions (
            company_location_id, address_line_1, city,
            subdivision_code, country_code, valid_from, valid_to
        ) VALUES (
            :location_id, 'Overlap', 'Noida', 'IN-UP', 'IN',
            '2026-04-15', '2026-05-15'
        )
        """,
        {"location_id": location_id},
    )
    await _rejected(
        database_url,
        """
        INSERT INTO core.company_location_versions (
            company_location_id, address_line_1, city,
            subdivision_code, country_code, valid_from
        ) VALUES (
            :location_id, 'Second Open', 'Noida', 'IN-UP', 'IN', '2026-06-01'
        )
        """,
        {"location_id": location_id},
    )

    company_id = await scalar(
        database_url,
        "SELECT company_id FROM core.company_locations WHERE id = :id",
        {"id": location_id},
    )
    invalid_location_id = uuid4()
    await execute(
        database_url,
        """
        INSERT INTO core.company_locations (
            id, company_id, location_name, address_line_1, city,
            country_code, is_branch, status
        ) VALUES (
            :id, :company_id, 'Invalid Version Host', 'Address', 'Noida',
            'IN', true, 'ACTIVE'
        )
        """,
        {"id": invalid_location_id, "company_id": company_id},
    )
    await _rejected(
        database_url,
        """
        INSERT INTO core.company_location_versions (
            company_location_id, address_line_1, city,
            country_code, valid_from, valid_to
        ) VALUES (
            :location_id, 'Invalid Range', 'Noida', 'IN',
            '2026-06-02', '2026-06-01'
        )
        """,
        {"location_id": invalid_location_id},
    )
    await _rejected(
        database_url,
        """
        INSERT INTO core.company_location_versions (
            company_location_id, address_line_1, city,
            subdivision_code, country_code, valid_from
        ) VALUES (
            :location_id, 'Wrong Geography', 'Noida',
            'US-CA', 'IN', '2026-06-01'
        )
        """,
        {"location_id": invalid_location_id},
    )
    await _rejected(
        database_url,
        """
        INSERT INTO core.company_location_versions (
            company_location_id, address_line_1, city, country_code
        ) VALUES (
            :location_id, 'Missing Date', 'Noida', 'IN'
        )
        """,
        {"location_id": invalid_location_id},
    )
    await _rejected(
        database_url,
        """
        INSERT INTO core.company_location_versions (
            company_location_id, city, country_code, valid_from
        ) VALUES (
            :location_id, 'Noida', 'IN', '2026-06-01'
        )
        """,
        {"location_id": invalid_location_id},
    )
    await _rejected(
        database_url,
        "DELETE FROM core.company_locations WHERE id = :location_id",
        {"location_id": location_id},
    )


def test_company_location_version_migration_contract() -> None:
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
        location_id = asyncio.run(_seed_existing_location(database_url))
        command.upgrade(config, REVISION)
        assert asyncio.run(
            scalar(database_url, "SELECT version_num FROM alembic_version")
        ) == REVISION
        asyncio.run(_exercise_contract(database_url, location_id))

        command.downgrade(config, PREVIOUS_REVISION)
        assert asyncio.run(
            scalar(database_url, "SELECT version_num FROM alembic_version")
        ) == PREVIOUS_REVISION
        assert not asyncio.run(
            scalar(
                database_url,
                "SELECT to_regclass('core.company_location_versions') IS NOT NULL",
            )
        )
        assert asyncio.run(
            scalar(
                database_url,
                "SELECT count(*) FROM core.company_locations WHERE id = :id",
                {"id": location_id},
            )
        ) == 1

        command.upgrade(config, REVISION)
        assert asyncio.run(
            scalar(database_url, "SELECT version_num FROM alembic_version")
        ) == REVISION
        assert asyncio.run(
            scalar(
                database_url,
                "SELECT count(*) FROM core.company_location_versions "
                "WHERE company_location_id = :id",
                {"id": location_id},
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
