import asyncio
import os
from collections.abc import AsyncIterator, Iterator, Mapping
from contextlib import asynccontextmanager
from datetime import date
from uuid import UUID

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
    database_url: str, sql: str, parameters: Mapping[str, object] | None = None
) -> None:
    async with _connection(database_url) as connection:
        async with connection.begin():
            await connection.execute(text(sql), parameters or {})


async def _scalar(
    database_url: str, sql: str, parameters: Mapping[str, object] | None = None
) -> object:
    async with _connection(database_url) as connection:
        async with connection.begin():
            return await connection.scalar(text(sql), parameters or {})


async def _assert_rejected(
    database_url: str, sql: str, parameters: Mapping[str, object]
) -> None:
    with pytest.raises((IntegrityError, DBAPIError)):
        await _execute(database_url, sql, parameters)


async def _seed_company(database_url: str, suffix: str) -> tuple[UUID, UUID]:
    tenant_id = await _scalar(
        database_url,
        "INSERT INTO core.tenants (name, code, status) "
        "VALUES (:name, :code, 'ACTIVE') RETURNING id",
        {"name": f"Tenant {suffix}", "code": f"TENANT_{suffix}"},
    )
    company_id = await _scalar(
        database_url,
        "INSERT INTO core.companies "
        "(tenant_id, legal_name, business_nature, status) "
        "VALUES (:tenant_id, :name, 'BOTH', 'DRAFT') RETURNING id",
        {"tenant_id": tenant_id, "name": f"Company {suffix}"},
    )
    return tenant_id, company_id


async def _assert_tax_reference_absent(database_url: str) -> None:
    assert await _scalar(
        database_url, "SELECT to_regclass('core.tax_types') IS NULL"
    )


async def _run_tax_reference_contract(database_url: str) -> tuple[UUID, UUID]:
    for table_name in (
        "tax_types",
        "company_hsn_sac_codes",
        "tax_rates",
        "company_hsn_sac_tax_rates",
        "tax_treatments",
    ):
        assert await _scalar(
            database_url,
            "SELECT to_regclass(:name) IS NOT NULL",
            {"name": f"core.{table_name}"},
        )

    await _execute(
        database_url,
        "INSERT INTO core.countries (code, name, status) "
        "VALUES ('IN', 'India', 'ACTIVE')",
    )
    _, first_company = await _seed_company(database_url, "A")
    _, second_company = await _seed_company(database_url, "B")
    tax_type_id = await _scalar(
        database_url,
        "INSERT INTO core.tax_types (code, name, country_code, status) "
        "VALUES ('GST', 'Goods and Services Tax', 'IN', 'ACTIVE') RETURNING id",
    )
    tax_rate_id = await _scalar(
        database_url,
        "INSERT INTO core.tax_rates "
        "(tax_type_id, rate_percent, country_code, status) "
        "VALUES (:tax_type_id, 18, 'IN', 'ACTIVE') RETURNING id",
        {"tax_type_id": tax_type_id},
    )
    hsn_id = await _scalar(
        database_url,
        "INSERT INTO core.company_hsn_sac_codes "
        "(company_id, classification_type, code, description, status) "
        "VALUES (:company_id, 'HSN', '8471', 'Computers', 'ACTIVE') RETURNING id",
        {"company_id": first_company},
    )
    await _execute(
        database_url,
        "INSERT INTO core.tax_treatments "
        "(code, name, tax_type_id, country_code, status) "
        "VALUES ('TAXABLE', 'Taxable', :tax_type_id, 'IN', 'ACTIVE')",
        {"tax_type_id": tax_type_id},
    )
    await _assert_rejected(
        database_url,
        "INSERT INTO core.tax_rates "
        "(tax_type_id, rate_percent, country_code, status) "
        "VALUES (:tax_type_id, 101, 'IN', 'ACTIVE')",
        {"tax_type_id": tax_type_id},
    )
    mapping_sql = (
        "INSERT INTO core.company_hsn_sac_tax_rates "
        "(company_hsn_sac_code_id, tax_rate_id, valid_from, valid_to, status) "
        "VALUES (:hsn_id, :rate_id, :valid_from, :valid_to, 'ACTIVE')"
    )
    await _execute(
        database_url,
        mapping_sql,
        {
            "hsn_id": hsn_id,
            "rate_id": tax_rate_id,
            "valid_from": date(2026, 1, 1),
            "valid_to": date(2026, 12, 31),
        },
    )
    await _assert_rejected(
        database_url,
        mapping_sql,
        {
            "hsn_id": hsn_id,
            "rate_id": tax_rate_id,
            "valid_from": date(2026, 6, 1),
            "valid_to": None,
        },
    )
    return first_company, second_company


async def _run_catalogue_contract(
    database_url: str,
    *,
    first_company: UUID,
    second_company: UUID,
) -> None:
    assert await _scalar(database_url, "SELECT to_regnamespace('ar') IS NOT NULL")
    for table_name in (
        "service_categories",
        "service_types",
        "product_categories",
        "products",
        "skus",
    ):
        assert await _scalar(
            database_url,
            "SELECT to_regclass(:name) IS NOT NULL",
            {"name": f"ar.{table_name}"},
        )
    assert not await _scalar(
        database_url,
        "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
        "WHERE table_schema = 'ar' AND column_name = 'business_segment_id')",
    )

    category_id = await _scalar(
        database_url,
        "INSERT INTO ar.product_categories (company_id, name, status) "
        "VALUES (:company_id, 'Electronics', 'ACTIVE') RETURNING id",
        {"company_id": first_company},
    )
    await _assert_rejected(
        database_url,
        "INSERT INTO ar.products "
        "(company_id, product_category_id, name, status) "
        "VALUES (:company_id, :category_id, 'Laptop', 'ACTIVE')",
        {"company_id": second_company, "category_id": category_id},
    )
    await _assert_rejected(
        database_url,
        "INSERT INTO ar.product_categories (company_id, name, status) "
        "VALUES (:company_id, 'Electronics', 'ACTIVE')",
        {"company_id": first_company},
    )
    await _execute(
        database_url,
        "INSERT INTO ar.product_categories (company_id, name, status) "
        "VALUES (:company_id, 'Electronics', 'ACTIVE')",
        {"company_id": second_company},
    )


async def _assert_catalogue_removed_only(database_url: str) -> None:
    assert await _scalar(database_url, "SELECT to_regnamespace('ar') IS NULL")
    assert await _scalar(
        database_url, "SELECT to_regclass('core.tax_types') IS NOT NULL"
    )


async def _assert_tax_reference_removed_only(database_url: str) -> None:
    assert await _scalar(
        database_url, "SELECT to_regclass('core.tax_types') IS NULL"
    )
    assert await _scalar(
        database_url,
        "SELECT to_regclass('core.company_gst_registrations') IS NOT NULL",
    )


def test_tax_and_catalogue_migration_contract(database_url: str) -> None:
    config = Config("alembic.ini")

    command.upgrade(config, "0007_core_company_gst_registrations")
    asyncio.run(_assert_tax_reference_absent(database_url))

    command.upgrade(config, "0008_tax_reference")
    first_company, second_company = asyncio.run(
        _run_tax_reference_contract(database_url)
    )

    command.upgrade(config, "0009_catalogue")
    asyncio.run(
        _run_catalogue_contract(
            database_url,
            first_company=first_company,
            second_company=second_company,
        )
    )

    command.downgrade(config, "0008_tax_reference")
    asyncio.run(_assert_catalogue_removed_only(database_url))

    command.downgrade(config, "0007_core_company_gst_registrations")
    asyncio.run(_assert_tax_reference_removed_only(database_url))
