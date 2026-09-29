import asyncio
import os
from collections.abc import AsyncIterator, Iterator, Mapping
from contextlib import asynccontextmanager
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.engine import make_url
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


async def _rows(
    database_url: str,
    sql: str,
    parameters: Mapping[str, object] | None = None,
) -> list[tuple[object, ...]]:
    async with _connection(database_url) as connection:
        async with connection.begin():
            result = await connection.execute(text(sql), parameters or {})
            return list(result.fetchall())


async def _seed_pre_0033_catalogue(
    database_url: str,
) -> dict[str, UUID]:
    await _execute(
        database_url,
        "INSERT INTO core.countries (code, name, status) "
        "VALUES ('IN', 'India', 'ACTIVE')",
    )
    tenant_id = await _scalar(
        database_url,
        "INSERT INTO core.tenants (name, status) "
        "VALUES ('Migration Tenant', 'ACTIVE') RETURNING id",
    )
    company_id = await _scalar(
        database_url,
        "INSERT INTO core.companies "
        "(tenant_id, legal_name, country_code, business_nature, status) "
        "VALUES (:tenant_id, 'Migration Company', 'IN', 'BOTH', 'DRAFT') "
        "RETURNING id",
        {"tenant_id": tenant_id},
    )
    tax_type_id = await _scalar(
        database_url,
        "INSERT INTO core.tax_types (code, name, country_code, status) "
        "VALUES ('GST', 'Goods and Services Tax', 'IN', 'ACTIVE') RETURNING id",
    )
    rate_id = await _scalar(
        database_url,
        "INSERT INTO core.tax_rates "
        "(tax_type_id, rate_percent, country_code, status) "
        "VALUES (:tax_type_id, 18, 'IN', 'ACTIVE') RETURNING id",
        {"tax_type_id": tax_type_id},
    )
    taxable_id = await _scalar(
        database_url,
        "INSERT INTO core.tax_treatments "
        "(code, name, tax_type_id, country_code, status) "
        "VALUES ('TAXABLE', 'Taxable', :tax_type_id, 'IN', 'ACTIVE') "
        "RETURNING id",
        {"tax_type_id": tax_type_id},
    )
    custom_id = await _scalar(
        database_url,
        "INSERT INTO core.tax_treatments "
        "(code, name, tax_type_id, country_code, status) "
        "VALUES ('CUSTOM_GST', 'Custom GST', :tax_type_id, 'IN', 'ACTIVE') "
        "RETURNING id",
        {"tax_type_id": tax_type_id},
    )
    sac_id = await _scalar(
        database_url,
        "INSERT INTO core.company_hsn_sac_codes "
        "(company_id, classification_type, code, description, status) "
        "VALUES (:company_id, 'SAC', '9983', 'Services', 'ACTIVE') RETURNING id",
        {"company_id": company_id},
    )
    hsn_id = await _scalar(
        database_url,
        "INSERT INTO core.company_hsn_sac_codes "
        "(company_id, classification_type, code, description, status) "
        "VALUES (:company_id, 'HSN', '8471', 'Goods', 'ACTIVE') RETURNING id",
        {"company_id": company_id},
    )
    for classification_id in (sac_id, hsn_id):
        await _execute(
            database_url,
            "INSERT INTO core.company_hsn_sac_tax_rates "
            "(company_hsn_sac_code_id, tax_rate_id, valid_from, status) "
            "VALUES (:classification_id, :rate_id, '2000-01-01', 'ACTIVE')",
            {"classification_id": classification_id, "rate_id": rate_id},
        )

    service_category_id = await _scalar(
        database_url,
        "INSERT INTO ar.service_categories (company_id, name, status) "
        "VALUES (:company_id, 'Services', 'ACTIVE') RETURNING id",
        {"company_id": company_id},
    )
    service_type_id = await _scalar(
        database_url,
        "INSERT INTO ar.service_types "
        "(company_id, service_category_id, name, company_hsn_sac_code_id, "
        "selected_tax_rate_id, tax_treatment_id, status) "
        "VALUES (:company_id, :category_id, 'Consulting', :classification_id, "
        ":rate_id, :treatment_id, 'ACTIVE') RETURNING id",
        {
            "company_id": company_id,
            "category_id": service_category_id,
            "classification_id": sac_id,
            "rate_id": rate_id,
            "treatment_id": taxable_id,
        },
    )
    product_category_id = await _scalar(
        database_url,
        "INSERT INTO ar.product_categories (company_id, name, status) "
        "VALUES (:company_id, 'Products', 'ACTIVE') RETURNING id",
        {"company_id": company_id},
    )
    product_id = await _scalar(
        database_url,
        "INSERT INTO ar.products "
        "(company_id, product_category_id, name, status) "
        "VALUES (:company_id, :category_id, 'Laptop', 'ACTIVE') RETURNING id",
        {"company_id": company_id, "category_id": product_category_id},
    )
    sku_id = await _scalar(
        database_url,
        "INSERT INTO ar.skus "
        "(company_id, product_id, sku_code, name, uom, "
        "company_hsn_sac_code_id, selected_tax_rate_id, tax_treatment_id, status) "
        "VALUES (:company_id, :product_id, 'LAPTOP', 'Laptop', 'EA', "
        ":classification_id, :rate_id, :treatment_id, 'ACTIVE') RETURNING id",
        {
            "company_id": company_id,
            "product_id": product_id,
            "classification_id": hsn_id,
            "rate_id": rate_id,
            "treatment_id": taxable_id,
        },
    )
    return {
        "service_type_id": service_type_id,
        "sku_id": sku_id,
        "rate_id": rate_id,
        "taxable_id": taxable_id,
        "custom_id": custom_id,
    }


async def _assert_0033_contract(
    database_url: str,
    seeded: dict[str, UUID],
) -> None:
    columns = await _rows(
        database_url,
        "SELECT table_name, column_name, is_nullable "
        "FROM information_schema.columns "
        "WHERE table_schema = 'ar' "
        "AND table_name IN ('service_types', 'skus') "
        "AND column_name IN "
        "('tax_treatment_id', 'base_tax_treatment_id', 'selected_tax_rate_id') "
        "ORDER BY table_name, column_name",
    )
    assert columns == [
        ("service_types", "base_tax_treatment_id", "NO"),
        ("service_types", "selected_tax_rate_id", "YES"),
        ("skus", "base_tax_treatment_id", "NO"),
        ("skus", "selected_tax_rate_id", "YES"),
    ]
    assert await _scalar(
        database_url,
        "SELECT base_tax_treatment_id FROM ar.service_types WHERE id = :id",
        {"id": seeded["service_type_id"]},
    ) == seeded["taxable_id"]
    assert await _scalar(
        database_url,
        "SELECT base_tax_treatment_id FROM ar.skus WHERE id = :id",
        {"id": seeded["sku_id"]},
    ) == seeded["taxable_id"]
    constraints = await _rows(
        database_url,
        "SELECT constraint_name, table_name "
        "FROM information_schema.table_constraints "
        "WHERE constraint_schema = 'ar' "
        "AND constraint_type = 'FOREIGN KEY' "
        "AND constraint_name IN "
        "('fk_service_types_base_tax_treatment', "
        " 'fk_skus_base_tax_treatment') "
        "ORDER BY constraint_name",
    )
    assert constraints == [
        ("fk_service_types_base_tax_treatment", "service_types"),
        ("fk_skus_base_tax_treatment", "skus"),
    ]


def test_catalogue_base_gst_nature_migration_contract(database_url: str) -> None:
    config = Config("alembic.ini")
    assert ScriptDirectory.from_config(config).get_current_head() == (
        "0033_catalogue_base_gst_nature"
    )

    command.upgrade(config, "0032_company_location_codes")
    seeded = asyncio.run(_seed_pre_0033_catalogue(database_url))

    asyncio.run(
        _execute(
            database_url,
            "UPDATE ar.service_types SET tax_treatment_id = :custom_id "
            "WHERE id = :id",
            {
                "custom_id": seeded["custom_id"],
                "id": seeded["service_type_id"],
            },
        )
    )
    with pytest.raises(RuntimeError, match="Base GST Nature"):
        command.upgrade(config, "0033_catalogue_base_gst_nature")
    asyncio.run(
        _execute(
            database_url,
            "UPDATE ar.service_types SET tax_treatment_id = :taxable_id "
            "WHERE id = :id",
            {
                "taxable_id": seeded["taxable_id"],
                "id": seeded["service_type_id"],
            },
        )
    )

    command.upgrade(config, "0033_catalogue_base_gst_nature")
    asyncio.run(_assert_0033_contract(database_url, seeded))

    asyncio.run(
        _execute(
            database_url,
            "UPDATE ar.service_types SET selected_tax_rate_id = NULL WHERE id = :id",
            {"id": seeded["service_type_id"]},
        )
    )
    with pytest.raises(RuntimeError, match="previous schema requires NOT NULL"):
        command.downgrade(config, "0032_company_location_codes")
    asyncio.run(
        _execute(
            database_url,
            "UPDATE ar.service_types SET selected_tax_rate_id = :rate_id "
            "WHERE id = :id",
            {"rate_id": seeded["rate_id"], "id": seeded["service_type_id"]},
        )
    )

    command.downgrade(config, "0032_company_location_codes")
    old_columns = asyncio.run(
        _rows(
            database_url,
            "SELECT table_name, column_name, is_nullable "
            "FROM information_schema.columns "
            "WHERE table_schema = 'ar' "
            "AND table_name IN ('service_types', 'skus') "
            "AND column_name IN "
            "('tax_treatment_id', 'base_tax_treatment_id', 'selected_tax_rate_id') "
            "ORDER BY table_name, column_name",
        )
    )
    assert old_columns == [
        ("service_types", "selected_tax_rate_id", "NO"),
        ("service_types", "tax_treatment_id", "NO"),
        ("skus", "selected_tax_rate_id", "NO"),
        ("skus", "tax_treatment_id", "NO"),
    ]
    assert asyncio.run(
        _scalar(
            database_url,
            "SELECT tax_treatment_id FROM ar.service_types WHERE id = :id",
            {"id": seeded["service_type_id"]},
        )
    ) == seeded["taxable_id"]

    command.upgrade(config, "0033_catalogue_base_gst_nature")
    asyncio.run(_assert_0033_contract(database_url, seeded))
