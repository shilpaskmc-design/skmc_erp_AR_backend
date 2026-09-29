import asyncio
import os
from datetime import UTC, datetime
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

REVISION = "0032_company_location_codes"
PREVIOUS_REVISION = "0031_uom_and_bank_account_hardening"


async def _safe_empty(database_url: str) -> None:
    async with connection(database_url) as value:
        if await value.scalar(text("SELECT to_regnamespace('core') IS NOT NULL")):
            pytest.fail("TEST_DATABASE_URL must point to a database without core schema")


async def _seed(database_url: str) -> tuple[UUID, UUID, UUID, list[UUID]]:
    tenant_id = uuid4()
    first_company = uuid4()
    second_company = uuid4()
    location_ids = [uuid4(), uuid4(), uuid4()]
    await execute(
        database_url,
        "INSERT INTO core.tenants (id, name, status) "
        "VALUES (:id, 'Location Code Tenant', 'ACTIVE')",
        {"id": tenant_id},
    )
    for company_id, name in (
        (first_company, "First Location Code Company"),
        (second_company, "Second Location Code Company"),
    ):
        await execute(
            database_url,
            "INSERT INTO core.companies (id, tenant_id, legal_name, status) "
            "VALUES (:id, :tenant, :name, 'DRAFT')",
            {"id": company_id, "tenant": tenant_id, "name": name},
        )
    await execute(
        database_url,
        "INSERT INTO core.countries (code, name, status) "
        "VALUES ('IN', 'India', 'ACTIVE')",
    )
    for location_id, company_id, name, created_at in (
        (location_ids[0], first_company, "Later Branch", datetime(2026, 1, 2, tzinfo=UTC)),
        (location_ids[1], first_company, "Earlier Branch", datetime(2026, 1, 1, tzinfo=UTC)),
        (location_ids[2], second_company, "Other Company Branch", datetime(2026, 1, 1, tzinfo=UTC)),
    ):
        await execute(
            database_url,
            """
            INSERT INTO core.company_locations
                (id, company_id, location_name, address_line_1, city,
                 country_code, is_branch, status, created_at, updated_at)
            VALUES
                (:id, :company, :name, 'Address', 'Noida',
                 'IN', true, 'ACTIVE', :created_at, :created_at)
            """,
            {
                "id": location_id,
                "company": company_id,
                "name": name,
                "created_at": created_at,
            },
        )
    return tenant_id, first_company, second_company, location_ids


async def _exercise(
    database_url: str,
    first_company: UUID,
    second_company: UUID,
    location_ids: list[UUID],
) -> None:
    assert await scalar(
        database_url,
        "SELECT location_code FROM core.company_locations WHERE id = :id",
        {"id": location_ids[1]},
    ) == "LOC-0001"
    assert await scalar(
        database_url,
        "SELECT location_code FROM core.company_locations WHERE id = :id",
        {"id": location_ids[0]},
    ) == "LOC-0002"
    assert await scalar(
        database_url,
        "SELECT location_code FROM core.company_locations WHERE id = :id",
        {"id": location_ids[2]},
    ) == "LOC-0001"
    assert await scalar(
        database_url,
        """
        SELECT is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'core'
          AND table_name = 'company_locations'
          AND column_name = 'location_code'
        """,
    ) == "NO"

    generated_id = uuid4()
    await execute(
        database_url,
        """
        INSERT INTO core.company_locations
            (id, company_id, location_name, address_line_1, city,
             country_code, is_branch, status)
        VALUES
            (:id, :company, 'Generated Branch', 'Address', 'Noida',
             'IN', true, 'ACTIVE')
        """,
        {"id": generated_id, "company": first_company},
    )
    assert await scalar(
        database_url,
        "SELECT location_code FROM core.company_locations WHERE id = :id",
        {"id": generated_id},
    ) == "LOC-0003"

    supplied_id = uuid4()
    await execute(
        database_url,
        """
        INSERT INTO core.company_locations
            (id, company_id, location_code, location_name, address_line_1,
             city, country_code, is_branch, status)
        VALUES
            (:id, :company, ' custom_branch ', 'Supplied Branch', 'Address',
             'Noida', 'IN', true, 'ACTIVE')
        """,
        {"id": supplied_id, "company": first_company},
    )
    assert await scalar(
        database_url,
        "SELECT location_code FROM core.company_locations WHERE id = :id",
        {"id": supplied_id},
    ) == "CUSTOM_BRANCH"

    await rejected(
        database_url,
        """
        INSERT INTO core.company_locations
            (company_id, location_code, location_name, address_line_1,
             city, country_code, is_branch, status)
        VALUES
            (:company, 'CUSTOM_BRANCH', 'Duplicate', 'Address',
             'Noida', 'IN', true, 'ACTIVE')
        """,
        {"company": first_company},
    )
    await execute(
        database_url,
        """
        INSERT INTO core.company_locations
            (company_id, location_code, location_name, address_line_1,
             city, country_code, is_branch, status)
        VALUES
            (:company, 'CUSTOM_BRANCH', 'Allowed Other Company', 'Address',
             'Noida', 'IN', true, 'ACTIVE')
        """,
        {"company": second_company},
    )
    await rejected(
        database_url,
        "UPDATE core.company_locations SET location_code = 'RENAMED' WHERE id = :id",
        {"id": supplied_id},
    )


def test_company_location_code_migration_contract() -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL migration tests")
    if make_url(database_url).drivername != "postgresql+asyncpg":
        pytest.fail("TEST_DATABASE_URL must use postgresql+asyncpg")
    asyncio.run(_safe_empty(database_url))
    previous_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    get_settings.cache_clear()
    config = Config("alembic.ini")
    try:
        command.upgrade(config, PREVIOUS_REVISION)
        _, first_company, second_company, location_ids = asyncio.run(
            _seed(database_url)
        )
        command.upgrade(config, REVISION)
        assert asyncio.run(
            scalar(database_url, "SELECT version_num FROM alembic_version")
        ) == REVISION
        asyncio.run(
            _exercise(
                database_url,
                first_company,
                second_company,
                location_ids,
            )
        )
        assert len(ScriptDirectory.from_config(config).get_heads()) == 1

        command.downgrade(config, PREVIOUS_REVISION)
        assert asyncio.run(
            scalar(
                database_url,
                """
                SELECT count(*)
                FROM information_schema.columns
                WHERE table_schema = 'core'
                  AND table_name = 'company_locations'
                  AND column_name = 'location_code'
                """,
            )
        ) == 0
        assert asyncio.run(
            scalar(
                database_url,
                "SELECT count(*) FROM core.company_locations WHERE id = ANY(:ids)",
                {"ids": location_ids},
            )
        ) == len(location_ids)
    finally:
        try:
            command.downgrade(config, "base")
        finally:
            if previous_url is None:
                os.environ.pop("DATABASE_URL", None)
            else:
                os.environ["DATABASE_URL"] = previous_url
            get_settings.cache_clear()
