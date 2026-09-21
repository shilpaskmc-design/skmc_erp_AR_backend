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
    command.upgrade(Config("alembic.ini"), "0009_catalogue")
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
        "INSERT INTO core.companies "
        "(tenant_id, legal_name, business_nature, status) "
        "VALUES (:tenant_id, :name, 'BOTH', 'DRAFT') RETURNING id",
        {"tenant_id": tenant_id, "name": f"Company {uuid4()}"},
    )


async def _seed_catalogue_leaves(
    database_url: str,
    *,
    company_id: UUID,
) -> tuple[list[UUID], list[UUID]]:
    if not await _scalar(
        database_url,
        "SELECT count(*) FROM core.countries WHERE code = 'IN'",
    ):
        await _execute(
            database_url,
            "INSERT INTO core.countries (code, name, status) "
            "VALUES ('IN', 'India', 'ACTIVE')",
        )
    tax_type_id = await _scalar(
        database_url,
        "INSERT INTO core.tax_types (code, name, country_code, status) "
        "VALUES (:code, 'Goods and Services Tax', 'IN', 'ACTIVE') RETURNING id",
        {"code": f"GST{uuid4().hex[:6].upper()}"},
    )
    tax_rate_id = await _scalar(
        database_url,
        "INSERT INTO core.tax_rates "
        "(tax_type_id, rate_percent, country_code, status) "
        "VALUES (:tax_type_id, 18, 'IN', 'ACTIVE') RETURNING id",
        {"tax_type_id": tax_type_id},
    )
    tax_treatment_id = await _scalar(
        database_url,
        "INSERT INTO core.tax_treatments "
        "(code, name, tax_type_id, country_code, status) "
        "VALUES (:code, 'Taxable', :tax_type_id, 'IN', 'ACTIVE') RETURNING id",
        {
            "code": f"TAXABLE{uuid4().hex[:6].upper()}",
            "tax_type_id": tax_type_id,
        },
    )
    sac_id = await _scalar(
        database_url,
        "INSERT INTO core.company_hsn_sac_codes "
        "(company_id, classification_type, code, description, status) "
        "VALUES (:company_id, 'SAC', :code, 'Service', 'ACTIVE') RETURNING id",
        {"company_id": company_id, "code": uuid4().hex[:8]},
    )
    hsn_id = await _scalar(
        database_url,
        "INSERT INTO core.company_hsn_sac_codes "
        "(company_id, classification_type, code, description, status) "
        "VALUES (:company_id, 'HSN', :code, 'Goods', 'ACTIVE') RETURNING id",
        {"company_id": company_id, "code": uuid4().hex[:8]},
    )
    service_category_id = await _scalar(
        database_url,
        "INSERT INTO ar.service_categories (company_id, name, status) "
        "VALUES (:company_id, :name, 'ACTIVE') RETURNING id",
        {"company_id": company_id, "name": f"Services {uuid4()}"},
    )
    product_category_id = await _scalar(
        database_url,
        "INSERT INTO ar.product_categories (company_id, name, status) "
        "VALUES (:company_id, :name, 'ACTIVE') RETURNING id",
        {"company_id": company_id, "name": f"Goods {uuid4()}"},
    )
    product_id = await _scalar(
        database_url,
        "INSERT INTO ar.products "
        "(company_id, product_category_id, name, status) "
        "VALUES (:company_id, :category_id, :name, 'ACTIVE') RETURNING id",
        {
            "company_id": company_id,
            "category_id": product_category_id,
            "name": f"Product {uuid4()}",
        },
    )

    service_ids: list[UUID] = []
    sku_ids: list[UUID] = []
    for position in range(2):
        service_ids.append(
            await _scalar(
                database_url,
                "INSERT INTO ar.service_types "
                "(company_id, service_category_id, name, "
                "company_hsn_sac_code_id, selected_tax_rate_id, "
                "tax_treatment_id, status) "
                "VALUES (:company_id, :category_id, :name, :classification_id, "
                ":tax_rate_id, :treatment_id, 'ACTIVE') RETURNING id",
                {
                    "company_id": company_id,
                    "category_id": service_category_id,
                    "name": f"Service {position} {uuid4()}",
                    "classification_id": sac_id,
                    "tax_rate_id": tax_rate_id,
                    "treatment_id": tax_treatment_id,
                },
            )
        )
        sku_ids.append(
            await _scalar(
                database_url,
                "INSERT INTO ar.skus "
                "(company_id, product_id, sku_code, name, uom, "
                "company_hsn_sac_code_id, selected_tax_rate_id, "
                "tax_treatment_id, status) "
                "VALUES (:company_id, :product_id, :sku_code, :name, 'EA', "
                ":classification_id, :tax_rate_id, :treatment_id, 'ACTIVE') "
                "RETURNING id",
                {
                    "company_id": company_id,
                    "product_id": product_id,
                    "sku_code": f"SKU-{uuid4()}",
                    "name": f"SKU {position}",
                    "classification_id": hsn_id,
                    "tax_rate_id": tax_rate_id,
                    "treatment_id": tax_treatment_id,
                },
            )
        )
    return service_ids, sku_ids


async def _run_contract(database_url: str) -> None:
    for table_name in (
        "cost_center_locations",
        "cost_center_business_segments",
        "cost_center_teams",
        "teams",
        "company_cost_center_settings",
    ):
        assert await _scalar(
            database_url,
            "SELECT to_regclass(:name) IS NOT NULL",
            {"name": f"core.{table_name}"},
        )
    assert not await _scalar(
        database_url,
        "SELECT to_regclass('core.team_memberships') IS NOT NULL",
    )
    assert not await _scalar(
        database_url,
        "SELECT to_regclass('core.cost_centers') IS NOT NULL",
    )

    first_company = await _seed_company(database_url)
    second_company = await _seed_company(database_url)

    await _execute(
        database_url,
        "INSERT INTO core.company_cost_center_settings "
        "(company_id, cost_center_reporting_enabled) VALUES (:company_id, true)",
        {"company_id": first_company},
    )
    await _execute(
        database_url,
        "INSERT INTO core.company_cost_center_settings (company_id) "
        "VALUES (:company_id)",
        {"company_id": second_company},
    )
    await _assert_rejected(
        database_url,
        "UPDATE core.company_cost_center_settings "
        "SET business_segment_enabled = true WHERE company_id = :company_id",
        {"company_id": second_company},
    )

    segment_id = await _scalar(
        database_url,
        "INSERT INTO core.cost_center_business_segments "
        "(company_id, name, code, status) "
        "VALUES (:company_id, 'Advisory', 'ADV', 'ACTIVE') RETURNING id",
        {"company_id": first_company},
    )
    other_segment_id = await _scalar(
        database_url,
        "INSERT INTO core.cost_center_business_segments "
        "(company_id, name, code, status) "
        "VALUES (:company_id, 'Advisory', 'ADV', 'ACTIVE') RETURNING id",
        {"company_id": second_company},
    )
    assert isinstance(segment_id, UUID)
    await _assert_rejected(
        database_url,
        "INSERT INTO core.cost_center_business_segments "
        "(company_id, name, status) VALUES (:company_id, '   ', 'ACTIVE')",
        {"company_id": first_company},
    )
    await _assert_rejected(
        database_url,
        "INSERT INTO core.cost_center_business_segments "
        "(company_id, name, status) VALUES (:company_id, 'Advisory', 'ACTIVE')",
        {"company_id": first_company},
    )

    service_ids, sku_ids = await _seed_catalogue_leaves(
        database_url,
        company_id=first_company,
    )
    for table_name, ids in (("service_types", service_ids), ("skus", sku_ids)):
        assert await _scalar(
            database_url,
            f"SELECT count(*) FROM ar.{table_name} "
            "WHERE id = ANY(:ids) AND business_segment_id IS NULL",
            {"ids": ids},
        ) == 2
        await _execute(
            database_url,
            f"UPDATE ar.{table_name} SET business_segment_id = :segment_id "
            "WHERE id = ANY(:ids)",
            {"segment_id": segment_id, "ids": ids},
        )
        assert await _scalar(
            database_url,
            f"SELECT count(*) FROM ar.{table_name} "
            "WHERE business_segment_id = :segment_id",
            {"segment_id": segment_id},
        ) == 2
        await _assert_rejected(
            database_url,
            f"UPDATE ar.{table_name} SET business_segment_id = :segment_id "
            "WHERE id = :id",
            {"segment_id": other_segment_id, "id": ids[0]},
        )

    first_bucket = await _scalar(
        database_url,
        "INSERT INTO core.cost_center_teams "
        "(company_id, name, status) "
        "VALUES (:company_id, 'Regulatory Operations', 'ACTIVE') RETURNING id",
        {"company_id": first_company},
    )
    second_bucket = await _scalar(
        database_url,
        "INSERT INTO core.cost_center_teams "
        "(company_id, name, status) "
        "VALUES (:company_id, 'Other Bucket', 'ACTIVE') RETURNING id",
        {"company_id": second_company},
    )
    for team_name in ("BIS Team", "AEO Team"):
        await _execute(
            database_url,
            "INSERT INTO core.teams "
            "(company_id, cost_center_team_id, name, status) "
            "VALUES (:company_id, :bucket_id, :name, 'ACTIVE')",
            {
                "company_id": first_company,
                "bucket_id": first_bucket,
                "name": team_name,
            },
        )
    await _execute(
        database_url,
        "INSERT INTO core.teams (company_id, name, status) "
        "VALUES (:company_id, 'Unassigned Team', 'ACTIVE')",
        {"company_id": first_company},
    )
    assert await _scalar(
        database_url,
        "SELECT count(*) FROM core.teams WHERE cost_center_team_id = :bucket_id",
        {"bucket_id": first_bucket},
    ) == 2
    await _assert_rejected(
        database_url,
        "INSERT INTO core.teams "
        "(company_id, cost_center_team_id, name, status) "
        "VALUES (:company_id, :bucket_id, 'Cross Company', 'ACTIVE')",
        {"company_id": first_company, "bucket_id": second_bucket},
    )

    location_bucket = await _scalar(
        database_url,
        "INSERT INTO core.cost_center_locations "
        "(company_id, name, status) "
        "VALUES (:company_id, 'Noida Operations', 'ACTIVE') RETURNING id",
        {"company_id": first_company},
    )
    other_location_bucket = await _scalar(
        database_url,
        "INSERT INTO core.cost_center_locations "
        "(company_id, name, status) "
        "VALUES (:company_id, 'Other Location', 'ACTIVE') RETURNING id",
        {"company_id": second_company},
    )
    for position in range(2):
        await _execute(
            database_url,
            "INSERT INTO core.company_locations "
            "(company_id, location_name, address_line_1, city, country_code, "
            "cost_center_location_id, is_branch, status) "
            "VALUES (:company_id, :name, 'Address', 'Noida', 'IN', "
            ":bucket_id, true, 'ACTIVE')",
            {
                "company_id": first_company,
                "name": f"Noida {position}",
                "bucket_id": location_bucket,
            },
        )
    await _execute(
        database_url,
        "INSERT INTO core.company_locations "
        "(company_id, location_name, address_line_1, city, country_code, "
        "is_branch, status) "
        "VALUES (:company_id, 'Unassigned', 'Address', 'Noida', 'IN', "
        "true, 'ACTIVE')",
        {"company_id": first_company},
    )
    assert await _scalar(
        database_url,
        "SELECT count(*) FROM core.company_locations "
        "WHERE cost_center_location_id = :bucket_id",
        {"bucket_id": location_bucket},
    ) == 2
    await _assert_rejected(
        database_url,
        "INSERT INTO core.company_locations "
        "(company_id, location_name, address_line_1, city, country_code, "
        "cost_center_location_id, is_branch, status) "
        "VALUES (:company_id, 'Cross Company', 'Address', 'Noida', 'IN', "
        ":bucket_id, true, 'ACTIVE')",
        {"company_id": first_company, "bucket_id": other_location_bucket},
    )


async def _assert_downgrade_removed_only_cost_center_objects(
    database_url: str,
) -> None:
    for table_name in (
        "cost_center_locations",
        "cost_center_business_segments",
        "cost_center_teams",
        "teams",
        "company_cost_center_settings",
    ):
        assert not await _scalar(
            database_url,
            "SELECT to_regclass(:name) IS NOT NULL",
            {"name": f"core.{table_name}"},
        )
    for table_name, column_name in (
        ("service_types", "business_segment_id"),
        ("skus", "business_segment_id"),
        ("company_locations", "cost_center_location_id"),
    ):
        assert not await _scalar(
            database_url,
            "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = :schema AND table_name = :table_name "
            "AND column_name = :column_name)",
            {
                "schema": "ar" if table_name != "company_locations" else "core",
                "table_name": table_name,
                "column_name": column_name,
            },
        )
    assert await _scalar(
        database_url,
        "SELECT to_regclass('ar.service_types') IS NOT NULL",
    )
    assert await _scalar(
        database_url,
        "SELECT to_regclass('core.company_locations') IS NOT NULL",
    )


def test_cost_center_migration_contract(database_url: str) -> None:
    config = Config("alembic.ini")
    command.upgrade(config, "0010_cost_center_configuration")
    asyncio.run(_run_contract(database_url))

    command.downgrade(config, "0009_catalogue")
    asyncio.run(_assert_downgrade_removed_only_cost_center_objects(database_url))
