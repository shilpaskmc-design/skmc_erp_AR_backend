import asyncio
import os
from datetime import date
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy.engine import make_url

from skmc_erp.config import get_settings
from tests.integration.company_configuration_migration_support import (
    execute,
    rejected,
    scalar,
    seed_company,
)

REVISION = "0028_revenue_gl_mapping_enhancement"
PREVIOUS_REVISION = "0027_company_document_presentation"


async def _seed_test_masters(url: str) -> dict[str, UUID]:
    tenant_id, company_id = await seed_company(url)
    _, other_company_id = await seed_company(url)

    gl_account_id = await scalar(
        url,
        "INSERT INTO core.gl_accounts (company_id, account_code, account_name, valid_from, status) "
        "VALUES (:c, '4101', 'Sales Revenue', '2026-01-01', 'ACTIVE') RETURNING id",
        {"c": company_id},
    )
    other_gl_account_id = await scalar(
        url,
        "INSERT INTO core.gl_accounts (company_id, account_code, account_name, valid_from, status) "
        "VALUES (:c, '4101', 'Other Revenue', '2026-01-01', 'ACTIVE') RETURNING id",
        {"c": other_company_id},
    )

    cat_id = await scalar(
        url,
        "INSERT INTO ar.service_categories (company_id, name, status) "
        "VALUES (:c, 'Consulting Cat', 'ACTIVE') RETURNING id",
        {"c": company_id},
    )
    hsn_sac_id = await scalar(
        url,
        "INSERT INTO core.company_hsn_sac_codes "
        "(company_id, classification_type, code, description, status) "
        "VALUES (:c, 'SAC', '998311', 'IT consulting services', 'ACTIVE') "
        "RETURNING id",
        {"c": company_id},
    )
    country_id = await scalar(
        url,
        "INSERT INTO core.countries (code, name, status) "
        "VALUES ('IN', 'India', 'ACTIVE') RETURNING code",
    )
    tax_type_id = await scalar(
        url,
        "INSERT INTO core.tax_types (code, name, country_code, status) "
        "VALUES ('GST', 'Goods and Services Tax', 'IN', 'ACTIVE') RETURNING id",
    )
    tax_rate_id = await scalar(
        url,
        "INSERT INTO core.tax_rates "
        "(tax_type_id, rate_percent, country_code, status) "
        "VALUES (:tax_type, 18.00, 'IN', 'ACTIVE') RETURNING id",
        {"tax_type": tax_type_id},
    )
    tax_treatment_id = await scalar(
        url,
        "INSERT INTO core.tax_treatments "
        "(code, name, tax_type_id, country_code, status) "
        "VALUES ('TAXABLE', 'Taxable', :tax_type, 'IN', 'ACTIVE') RETURNING id",
        {"tax_type": tax_type_id},
    )

    service_type_id = await scalar(
        url,
        "INSERT INTO ar.service_types ("
        "  company_id, service_category_id, name, company_hsn_sac_code_id, "
        "  selected_tax_rate_id, tax_treatment_id, status"
        ") VALUES ("
        "  :c, :cat, 'IT Consulting', :sac, :tr, :tt, 'ACTIVE'"
        ") RETURNING id",
        {
            "c": company_id,
            "cat": cat_id,
            "sac": hsn_sac_id,
            "tr": tax_rate_id,
            "tt": tax_treatment_id,
        },
    )

    prod_cat_id = await scalar(
        url,
        "INSERT INTO ar.product_categories (company_id, name, status) "
        "VALUES (:c, 'Hardware Cat', 'ACTIVE') RETURNING id",
        {"c": company_id},
    )
    prod_id = await scalar(
        url,
        "INSERT INTO ar.products (company_id, product_category_id, name, status) "
        "VALUES (:c, :cat, 'Hardware Prod', 'ACTIVE') RETURNING id",
        {"c": company_id, "cat": prod_cat_id},
    )
    sku_id = await scalar(
        url,
        "INSERT INTO ar.skus ("
        "  company_id, product_id, sku_code, name, uom, company_hsn_sac_code_id, "
        "  selected_tax_rate_id, tax_treatment_id, status"
        ") VALUES ("
        "  :c, :p, 'SKU-001', 'Server Rack', 'NOS', :sac, :tr, :tt, 'ACTIVE'"
        ") RETURNING id",
        {
            "c": company_id,
            "p": prod_id,
            "sac": hsn_sac_id,
            "tr": tax_rate_id,
            "tt": tax_treatment_id,
        },
    )

    location_id = await scalar(
        url,
        "INSERT INTO core.company_locations ("
        "  company_id, location_name, address_line_1, city, country_code, is_branch, status"
        ") VALUES ("
        "  :c, 'Noida Branch', 'Sector 62', 'Noida', 'IN', true, 'ACTIVE'"
        ") RETURNING id",
        {"c": company_id},
    )

    # Masters for other company
    other_cat_id = await scalar(
        url,
        "INSERT INTO ar.service_categories (company_id, name, status) "
        "VALUES (:c, 'Other Consulting Cat', 'ACTIVE') RETURNING id",
        {"c": other_company_id},
    )
    other_hsn_sac_id = await scalar(
        url,
        "INSERT INTO core.company_hsn_sac_codes "
        "(company_id, classification_type, code, description, status) "
        "VALUES (:c, 'SAC', '998311', 'Other IT consulting services', "
        "'ACTIVE') RETURNING id",
        {"c": other_company_id},
    )
    other_service_type_id = await scalar(
        url,
        "INSERT INTO ar.service_types ("
        "  company_id, service_category_id, name, company_hsn_sac_code_id, "
        "  selected_tax_rate_id, tax_treatment_id, status"
        ") VALUES ("
        "  :c, :cat, 'Other Consulting', :sac, :tr, :tt, 'ACTIVE'"
        ") RETURNING id",
        {
            "c": other_company_id,
            "cat": other_cat_id,
            "sac": other_hsn_sac_id,
            "tr": tax_rate_id,
            "tt": tax_treatment_id,
        },
    )

    return {
        "tenant_id": tenant_id,
        "company_id": company_id,
        "other_company_id": other_company_id,
        "gl_account_id": gl_account_id,
        "other_gl_account_id": other_gl_account_id,
        "service_type_id": service_type_id,
        "other_service_type_id": other_service_type_id,
        "sku_id": sku_id,
        "location_id": location_id,
    }


async def _exercise(url: str, m: dict[str, UUID]) -> None:
    company_id = m["company_id"]
    gl_account_id = m["gl_account_id"]
    service_type_id = m["service_type_id"]
    sku_id = m["sku_id"]
    location_id = m["location_id"]

    # Verify column existence and absence of company_hsn_sac_code_id
    assert await scalar(
        url,
        "SELECT count(*) = 0 FROM information_schema.columns "
        "WHERE table_schema = 'ar' AND table_name = 'revenue_gl_mappings' AND column_name = 'company_hsn_sac_code_id'",
    )
    assert await scalar(
        url,
        "SELECT is_nullable = 'YES' FROM information_schema.columns "
        "WHERE table_schema = 'ar' AND table_name = 'revenue_gl_mappings' AND column_name = 'supply_type_code'",
    )

    # 1. Reject both service_type_id and sku_id
    await rejected(
        url,
        "INSERT INTO ar.revenue_gl_mappings (company_id, service_type_id, sku_id, gl_account_id, valid_from, status) "
        "VALUES (:c, :st, :sku, :gl, '2026-01-01', 'ACTIVE')",
        {"c": company_id, "st": service_type_id, "sku": sku_id, "gl": gl_account_id},
    )

    # 2. Reject neither service_type_id nor sku_id
    await rejected(
        url,
        "INSERT INTO ar.revenue_gl_mappings (company_id, gl_account_id, valid_from, status) "
        "VALUES (:c, :gl, '2026-01-01', 'ACTIVE')",
        {"c": company_id, "gl": gl_account_id},
    )

    # 3. Reject cross-company FK references
    await rejected(
        url,
        "INSERT INTO ar.revenue_gl_mappings (company_id, service_type_id, gl_account_id, valid_from, status) "
        "VALUES (:c, :st, :gl, '2026-01-01', 'ACTIVE')",
        {"c": company_id, "st": m["other_service_type_id"], "gl": gl_account_id},
    )
    await rejected(
        url,
        "INSERT INTO ar.revenue_gl_mappings (company_id, service_type_id, gl_account_id, valid_from, status) "
        "VALUES (:c, :st, :gl, '2026-01-01', 'ACTIVE')",
        {"c": company_id, "st": service_type_id, "gl": m["other_gl_account_id"]},
    )

    # 4. Create valid Service Type item-only mapping
    m1_id = await scalar(
        url,
        "INSERT INTO ar.revenue_gl_mappings (company_id, service_type_id, gl_account_id, valid_from, status) "
        "VALUES (:c, :st, :gl, '2026-01-01', 'ACTIVE') RETURNING id",
        {"c": company_id, "st": service_type_id, "gl": gl_account_id},
    )
    assert m1_id is not None

    # 5. Create valid Service Type + Supply + Location mapping (coexists with item-only)
    m2_id = await scalar(
        url,
        "INSERT INTO ar.revenue_gl_mappings (company_id, service_type_id, supply_type_code, company_location_id, gl_account_id, valid_from, status) "
        "VALUES (:c, :st, 'B2B', :loc, :gl, '2026-01-01', 'ACTIVE') RETURNING id",
        {"c": company_id, "st": service_type_id, "loc": location_id, "gl": gl_account_id},
    )
    assert m2_id is not None

    # 6. Reject same criteria tuple overlap
    await rejected(
        url,
        "INSERT INTO ar.revenue_gl_mappings (company_id, service_type_id, supply_type_code, company_location_id, gl_account_id, valid_from, status) "
        "VALUES (:c, :st, 'B2B', :loc, :gl, '2026-06-01', 'ACTIVE')",
        {"c": company_id, "st": service_type_id, "loc": location_id, "gl": gl_account_id},
    )

    # 7. Create valid SKU mapping
    sku_m_id = await scalar(
        url,
        "INSERT INTO ar.revenue_gl_mappings (company_id, sku_id, gl_account_id, valid_from, status) "
        "VALUES (:c, :sku, :gl, '2026-01-01', 'ACTIVE') RETURNING id",
        {"c": company_id, "sku": sku_id, "gl": gl_account_id},
    )
    assert sku_m_id is not None


async def _safe_empty(url: str) -> None:
    assert not await scalar(url, "SELECT to_regnamespace('core') IS NOT NULL")
    if await scalar(
        url, "SELECT to_regclass('public.alembic_version') IS NOT NULL"
    ):
        assert await scalar(url, "SELECT count(*) FROM alembic_version") == 0


def test_revenue_gl_mapping_migration_contract() -> None:
    url = os.getenv("TEST_DATABASE_URL")
    if url is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL migration tests")
    if make_url(url).drivername != "postgresql+asyncpg":
        pytest.fail("TEST_DATABASE_URL must use postgresql+asyncpg")

    asyncio.run(_safe_empty(url))
    old_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    get_settings.cache_clear()
    config = Config("alembic.ini")
    try:
        command.upgrade(config, PREVIOUS_REVISION)
        m = asyncio.run(_seed_test_masters(url))
        command.upgrade(config, REVISION)
        assert (
            asyncio.run(
                scalar(url, "SELECT version_num FROM alembic_version")
            )
            == REVISION
        )
        asyncio.run(_exercise(url, m))

        command.downgrade(config, PREVIOUS_REVISION)
        assert (
            asyncio.run(
                scalar(url, "SELECT version_num FROM alembic_version")
            )
            == PREVIOUS_REVISION
        )

        command.upgrade(config, REVISION)
        assert (
            asyncio.run(
                scalar(url, "SELECT version_num FROM alembic_version")
            )
            == REVISION
        )
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
