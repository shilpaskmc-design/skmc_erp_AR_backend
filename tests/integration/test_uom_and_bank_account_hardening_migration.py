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

REVISION = "0031_uom_and_bank_account_hardening"
PREVIOUS_REVISION = "0030_company_legal_name_history"
CURRENT_HEAD = "0032_company_location_codes"


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


@pytest.fixture
def database_url() -> str:
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL migration tests")
    if not url.startswith("postgresql+asyncpg://"):
        pytest.fail("TEST_DATABASE_URL must use postgresql+asyncpg")
    return url


@pytest.fixture
def alembic_config(database_url: str) -> Config:
    old_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    get_settings.cache_clear()
    config = Config("alembic.ini")
    sync_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://").replace("%", "%%")
    config.set_main_option("sqlalchemy.url", sync_url)
    yield config
    if old_url:
        os.environ["DATABASE_URL"] = old_url
    else:
        os.environ.pop("DATABASE_URL", None)
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_uom_and_bank_account_migration_lifecycle(
    database_url: str,
    alembic_config: Config,
) -> None:
    await _safe_empty(database_url)
    script = ScriptDirectory.from_config(alembic_config)

    assert script.get_current_head() == CURRENT_HEAD
    assert script.get_revision(REVISION).down_revision == PREVIOUS_REVISION

    # 1. Upgrade to PREVIOUS_REVISION
    await asyncio.to_thread(command.upgrade, alembic_config, PREVIOUS_REVISION)

    # 2. Seed existing Tenant, Company, and Bank Account BEFORE 0031
    tenant_id = uuid4()
    company_id = uuid4()
    bank_account_id = uuid4()

    await execute(
        database_url,
        "INSERT INTO core.tenants (id, name, status) VALUES (:id, 'Test Tenant', 'ACTIVE')",
        {"id": tenant_id},
    )
    await execute(
        database_url,
        """
        INSERT INTO core.companies (id, tenant_id, legal_name, country_code, status)
        VALUES (:id, :tenant_id, 'Test Company IN', 'IN', 'ACTIVE')
        """,
        {"id": company_id, "tenant_id": tenant_id},
    )
    await execute(
        database_url,
        "INSERT INTO core.currencies (code, name, symbol, minor_units, status) VALUES ('INR', 'Indian Rupee', '₹', 2, 'ACTIVE'), ('USD', 'US Dollar', '$', 2, 'ACTIVE') ON CONFLICT DO NOTHING",
    )
    await execute(
        database_url,
        """
        INSERT INTO core.company_bank_accounts (
            id, company_id, account_holder_name, bank_name, account_number, currency_code, account_type, status
        ) VALUES (
            :id, :company_id, 'Test Holder', 'Global Bank', '999888777666', 'USD', 'savings', 'ACTIVE'
        )
        """,
        {"id": bank_account_id, "company_id": company_id},
    )

    # 3. Upgrade to REVISION (0031)
    await asyncio.to_thread(command.upgrade, alembic_config, REVISION)

    # 4. Verify core.uoms content: SAC is NOT present
    uoms = await _fetch_all(
        database_url,
        "SELECT code, name, symbol, uqc_code, status FROM core.uoms ORDER BY code",
    )
    codes = [u["code"] for u in uoms]
    assert "NOS" in codes
    assert "KGS" in codes
    assert "HRS" in codes
    assert "SAC" not in codes

    # 5. Verify existing bank account: bank_country_code must NOT be backfilled and remains NULL
    bank_row = await _fetch_all(
        database_url,
        "SELECT bank_country_code, account_type FROM core.company_bank_accounts WHERE id = :id",
        {"id": bank_account_id},
    )
    assert len(bank_row) == 1
    assert bank_row[0]["bank_country_code"] is None
    assert bank_row[0]["account_type"] == "SAVINGS"  # normalized to uppercase

    # 6. Downgrade to PREVIOUS_REVISION
    await asyncio.to_thread(command.downgrade, alembic_config, PREVIOUS_REVISION)
    assert not await scalar(database_url, "SELECT to_regclass('core.uoms') IS NOT NULL")

    # 7. Clean up completely
    await asyncio.to_thread(command.downgrade, alembic_config, "base")
