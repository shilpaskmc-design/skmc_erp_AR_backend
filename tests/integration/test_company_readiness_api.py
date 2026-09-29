import asyncio
import os
from collections.abc import AsyncGenerator, AsyncIterator, Iterator, Mapping
from contextlib import asynccontextmanager
from datetime import date
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from skmc_erp.config import Settings, get_settings


@asynccontextmanager
async def _connection(database_url: str) -> AsyncIterator[AsyncConnection]:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            yield connection
    finally:
        await engine.dispose()


async def _assert_empty(database_url: str) -> None:
    async with _connection(database_url) as connection:
        if await connection.scalar(text("SELECT to_regnamespace('core') IS NOT NULL")):
            pytest.fail("TEST_DATABASE_URL must point to an empty database")


@pytest.fixture(scope="module")
def migrated_database() -> Iterator[str]:
    value = os.getenv("TEST_DATABASE_URL")
    if value is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL API tests")
    if make_url(value).drivername != "postgresql+asyncpg":
        pytest.fail("TEST_DATABASE_URL must use postgresql+asyncpg")
    asyncio.run(_assert_empty(value))
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = value
    get_settings.cache_clear()
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    try:
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


@pytest.fixture
async def api_context(
    migrated_database: str,
) -> AsyncGenerator[tuple[AsyncClient, AsyncEngine, FastAPI], None]:
    from skmc_erp.database import get_db_session
    from skmc_erp.main import app

    engine = create_async_engine(migrated_database)
    factory = async_sessionmaker(engine, class_=AsyncSession)

    async def session_override() -> AsyncGenerator[AsyncSession, None]:
        async with factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db_session] = session_override
    app.dependency_overrides[get_settings] = lambda: Settings(
        database_url=migrated_database,
        environment="development",
    )
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        try:
            yield client, engine, app
        finally:
            app.dependency_overrides.clear()
            async with engine.begin() as connection:
                await connection.execute(text("TRUNCATE core.tenants CASCADE"))
                await connection.execute(
                    text(
                        "TRUNCATE core.company_identifier_types, "
                        "core.entity_types, core.gst_registration_types, "
                        "core.uoms, core.tax_treatments, core.tax_rates, "
                        "core.tax_types, core.country_subdivisions, "
                        "core.currencies, core.countries CASCADE"
                    )
                )
            await engine.dispose()


async def _execute(
    engine: AsyncEngine,
    sql: str,
    parameters: Mapping[str, object] | None = None,
) -> None:
    async with engine.begin() as connection:
        await connection.execute(text(sql), parameters or {})


async def _scalar(
    engine: AsyncEngine,
    sql: str,
    parameters: Mapping[str, object] | None = None,
) -> object:
    async with engine.begin() as connection:
        return await connection.scalar(text(sql), parameters or {})


async def _seed_ready_company(
    engine: AsyncEngine,
    *,
    business_nature: str = "BOTH",
) -> dict[str, UUID]:
    today = date.today()
    ids: dict[str, UUID] = {}
    await _execute(
        engine,
        "INSERT INTO core.countries (code, name, status) "
        "VALUES ('IN', 'India', 'ACTIVE')",
    )
    await _execute(
        engine,
        "INSERT INTO core.currencies (code, name, minor_units, status) "
        "VALUES ('INR', 'Indian Rupee', 2, 'ACTIVE')",
    )
    await _execute(
        engine,
        "INSERT INTO core.uoms (code, name, status) "
        "VALUES ('NOS', 'Numbers', 'ACTIVE') "
        "ON CONFLICT (code) DO UPDATE SET status = 'ACTIVE'",
    )
    await _execute(
        engine,
        "INSERT INTO core.country_subdivisions "
        "(country_code, code, name, subdivision_type, gst_state_code, status) "
        "VALUES ('IN', 'IN-UP', 'Uttar Pradesh', 'STATE', '09', 'ACTIVE')",
    )
    ids["tenant"] = await _scalar(
        engine,
        "INSERT INTO core.tenants (name, status) "
        "VALUES (:name, 'ACTIVE') RETURNING id",
        {"name": f"Tenant {uuid4()}"},
    )
    ids["entity_type"] = await _scalar(
        engine,
        "INSERT INTO core.entity_types (country_code, code, name, status) "
        "VALUES ('IN', 'PRIVATE_LIMITED', 'Private Limited', 'ACTIVE') "
        "RETURNING id",
    )
    ids["pan_type"] = await _scalar(
        engine,
        "INSERT INTO core.company_identifier_types "
        "(country_code, code, name, status) "
        "VALUES ('IN', 'PAN', 'Permanent Account Number', 'ACTIVE') RETURNING id",
    )
    ids["cin_type"] = await _scalar(
        engine,
        "INSERT INTO core.company_identifier_types "
        "(country_code, code, name, status) "
        "VALUES ('IN', 'CIN', 'Corporate Identity Number', 'ACTIVE') RETURNING id",
    )
    await _execute(
        engine,
        "INSERT INTO core.entity_type_identifier_rules "
        "(entity_type_id, identifier_type_id, requirement_level) "
        "VALUES (:entity, :cin, 'REQUIRED')",
        {"entity": ids["entity_type"], "cin": ids["cin_type"]},
    )
    ids["company"] = await _scalar(
        engine,
        "INSERT INTO core.companies "
        "(tenant_id, legal_name, entity_type_id, country_code, base_timezone, "
        "base_currency_code, business_nature, status) "
        "VALUES (:tenant, 'Ready Company', :entity, 'IN', 'Asia/Kolkata', "
        "'INR', :nature, 'DRAFT') RETURNING id",
        {
            "tenant": ids["tenant"],
            "entity": ids["entity_type"],
            "nature": business_nature,
        },
    )
    for type_key, value in (("pan_type", "ABCDE1234F"), ("cin_type", "CIN123")):
        await _execute(
            engine,
            "INSERT INTO core.company_identifiers "
            "(company_id, identifier_type_id, identifier_value, status) "
            "VALUES (:company, :type, :value, 'ACTIVE')",
            {
                "company": ids["company"],
                "type": ids[type_key],
                "value": value,
            },
        )
    await _execute(
        engine,
        "INSERT INTO core.company_fiscal_settings "
        "(company_id, fiscal_year_pattern, start_month, start_day) "
        "VALUES (:company, 'JAN_DEC', 1, 1)",
        {"company": ids["company"]},
    )
    ids["financial_year"] = await _scalar(
        engine,
        "INSERT INTO core.financial_years "
        "(company_id, start_date, end_date, display_code, status) "
        "VALUES (:company, :start, :end, :code, 'OPEN') RETURNING id",
        {
            "company": ids["company"],
            "start": date(today.year, 1, 1),
            "end": date(today.year, 12, 31),
            "code": str(today.year),
        },
    )
    ids["gst_type"] = await _scalar(
        engine,
        "INSERT INTO core.gst_registration_types (code, name, status) "
        "VALUES ('REGULAR', 'Regular', 'ACTIVE') RETURNING id",
    )
    ids["gst"] = await _scalar(
        engine,
        "INSERT INTO core.company_gst_registrations "
        "(company_id, gstin, gst_registration_type_id, subdivision_code, "
        "valid_from, status) VALUES "
        "(:company, '09ABCDE1234F1Z5', :type, 'IN-UP', '2020-01-01', 'ACTIVE') "
        "RETURNING id",
        {"company": ids["company"], "type": ids["gst_type"]},
    )
    ids["location"] = await _scalar(
        engine,
        "INSERT INTO core.company_locations "
        "(company_id, location_code, location_name, address_line_1, city, "
        "subdivision_code, country_code, gst_registration_id, "
        "is_registered_office, is_billing_office, status) VALUES "
        "(:company, 'LOC-0001', 'Registered Office', '1 Main Road', 'Noida', "
        "'IN-UP', 'IN', :gst, true, true, 'ACTIVE') RETURNING id",
        {"company": ids["company"], "gst": ids["gst"]},
    )
    ids["tax_type"] = await _scalar(
        engine,
        "INSERT INTO core.tax_types (code, name, country_code, status) "
        "VALUES ('GST', 'Goods and Services Tax', 'IN', 'ACTIVE') RETURNING id",
    )
    ids["tax_rate"] = await _scalar(
        engine,
        "INSERT INTO core.tax_rates "
        "(tax_type_id, rate_percent, country_code, status) "
        "VALUES (:type, 18, 'IN', 'ACTIVE') RETURNING id",
        {"type": ids["tax_type"]},
    )
    ids["zero_rate"] = await _scalar(
        engine,
        "INSERT INTO core.tax_rates "
        "(tax_type_id, rate_percent, country_code, status) "
        "VALUES (:type, 0, 'IN', 'ACTIVE') RETURNING id",
        {"type": ids["tax_type"]},
    )
    for code in ("TAXABLE", "NIL_RATED", "EXEMPT", "NON_GST"):
        ids[code.lower()] = await _scalar(
            engine,
            "INSERT INTO core.tax_treatments "
            "(code, name, tax_type_id, country_code, status) "
            "VALUES (:code, :code, :type, 'IN', 'ACTIVE') RETURNING id",
            {"code": code, "type": ids["tax_type"]},
        )
    for classification, code, key in (
        ("SAC", "9983", "sac"),
        ("HSN", "8471", "hsn"),
    ):
        ids[key] = await _scalar(
            engine,
            "INSERT INTO core.company_hsn_sac_codes "
            "(company_id, classification_type, code, description, status) "
            "VALUES (:company, :classification, :code, :description, 'ACTIVE') "
            "RETURNING id",
            {
                "company": ids["company"],
                "classification": classification,
                "code": code,
                "description": classification,
            },
        )
        for rate_key in ("tax_rate", "zero_rate"):
            await _execute(
                engine,
                "INSERT INTO core.company_hsn_sac_tax_rates "
                "(company_hsn_sac_code_id, tax_rate_id, valid_from, status) "
                "VALUES (:classification, :rate, '2020-01-01', 'ACTIVE')",
                {"classification": ids[key], "rate": ids[rate_key]},
            )
    ids["service_category"] = await _scalar(
        engine,
        "INSERT INTO ar.service_categories (company_id, name, status) "
        "VALUES (:company, 'Services', 'ACTIVE') RETURNING id",
        {"company": ids["company"]},
    )
    ids["service"] = await _scalar(
        engine,
        "INSERT INTO ar.service_types "
        "(company_id, service_category_id, name, uom, company_hsn_sac_code_id, "
        "selected_tax_rate_id, base_tax_treatment_id, status) VALUES "
        "(:company, :category, 'Consulting', NULL, :sac, :rate, :treatment, "
        "'ACTIVE') RETURNING id",
        {
            "company": ids["company"],
            "category": ids["service_category"],
            "sac": ids["sac"],
            "rate": ids["tax_rate"],
            "treatment": ids["taxable"],
        },
    )
    ids["product_category"] = await _scalar(
        engine,
        "INSERT INTO ar.product_categories (company_id, name, status) "
        "VALUES (:company, 'Products', 'ACTIVE') RETURNING id",
        {"company": ids["company"]},
    )
    ids["product"] = await _scalar(
        engine,
        "INSERT INTO ar.products "
        "(company_id, product_category_id, name, status) "
        "VALUES (:company, :category, 'Laptop', 'ACTIVE') RETURNING id",
        {"company": ids["company"], "category": ids["product_category"]},
    )
    ids["sku"] = await _scalar(
        engine,
        "INSERT INTO ar.skus "
        "(company_id, product_id, sku_code, name, uom, "
        "company_hsn_sac_code_id, selected_tax_rate_id, "
        "base_tax_treatment_id, status) VALUES "
        "(:company, :product, 'LAPTOP', 'Laptop', 'NOS', :hsn, :rate, "
        ":treatment, 'ACTIVE') RETURNING id",
        {
            "company": ids["company"],
            "product": ids["product"],
            "hsn": ids["hsn"],
            "rate": ids["tax_rate"],
            "treatment": ids["taxable"],
        },
    )
    await _execute(
        engine,
        "INSERT INTO ar.payment_terms "
        "(company_id, name, code, term_type, credit_days, is_default, status) "
        "VALUES (:company, 'Immediate', 'IMMEDIATE', 'IMMEDIATE', 0, true, "
        "'ACTIVE')",
        {"company": ids["company"]},
    )
    await _execute(
        engine,
        "INSERT INTO core.company_bank_accounts "
        "(company_id, bank_country_code, account_holder_name, bank_name, "
        "account_number, currency_code, account_type, is_default_for_billing, "
        "status) VALUES "
        "(:company, 'IN', 'Ready Company', 'Ready Bank', '1234567890', 'INR', "
        "'CURRENT', true, 'ACTIVE')",
        {"company": ids["company"]},
    )
    for document_type in ("PI", "TI", "CN", "DN"):
        await _execute(
            engine,
            "INSERT INTO ar.document_sequences "
            "(id, company_id, financial_year_id, document_type, series_name, "
            "format, start_number, next_number, padding, status, created_at, "
            "updated_at) VALUES "
            "(:id, :company, :fy, :document_type, 'Main', '{NUMBER}', 1, 1, "
            "6, 'ACTIVE', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            {
                "id": uuid4(),
                "company": ids["company"],
                "fy": ids["financial_year"],
                "document_type": document_type,
            },
        )
    await _execute(
        engine,
        "INSERT INTO ar.company_document_templates "
        "(company_id, document_type, template_key, version_no, status) "
        "VALUES (:company, NULL, 'STANDARD', 1, 'ACTIVE')",
        {"company": ids["company"]},
    )
    return ids


def _codes(payload: dict[str, object]) -> set[str]:
    return {check["code"] for check in payload["blocking_checks"]}


async def test_fully_configured_company_is_ready_and_activates_idempotently(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    ids = await _seed_ready_company(engine)
    headers = {"X-Tenant-ID": str(ids["tenant"])}

    before = await client.get(
        f"/companies/{ids['company']}/readiness", headers=headers
    )
    activated = await client.post(
        f"/companies/{ids['company']}/activate", headers=headers
    )
    repeated = await client.post(
        f"/companies/{ids['company']}/activate", headers=headers
    )

    assert before.status_code == 200
    assert before.json()["ready_for_activation"] is True
    assert before.json()["blocking_checks"] == []
    assert activated.status_code == 200
    assert activated.json()["status"] == "ACTIVE"
    assert repeated.status_code == 200
    assert repeated.json()["status"] == "ACTIVE"


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        (
            "UPDATE core.company_identifiers SET status = 'INACTIVE' "
            "WHERE identifier_type_id = :pan_type",
            "MISSING_PAN",
        ),
        (
            "UPDATE core.company_identifiers SET status = 'INACTIVE' "
            "WHERE identifier_type_id = :cin_type",
            "MISSING_REQUIRED_ENTITY_IDENTIFIER",
        ),
        (
            "UPDATE core.company_locations SET is_registered_office = false",
            "MISSING_REGISTERED_OFFICE",
        ),
        (
            "DELETE FROM core.company_fiscal_settings WHERE company_id = :company",
            "MISSING_FISCAL_SETTINGS",
        ),
        (
            "UPDATE core.financial_years SET status = 'DRAFT' "
            "WHERE id = :financial_year",
            "MISSING_CURRENT_FINANCIAL_YEAR",
        ),
        (
            "UPDATE core.currencies SET status = 'INACTIVE' WHERE code = 'INR'",
            "COMPANY_BASE_CURRENCY",
        ),
        (
            "UPDATE core.company_gst_registrations SET status = 'INACTIVE' "
            "WHERE id = :gst",
            "MISSING_GST_REGISTRATION",
        ),
        (
            "UPDATE core.company_locations SET gst_registration_id = NULL",
            "MISSING_GST_LOCATION_MAPPING",
        ),
        (
            "UPDATE ar.service_types SET status = 'INACTIVE' WHERE id = :service",
            "MISSING_SERVICE_CATALOGUE",
        ),
        (
            "UPDATE ar.skus SET status = 'INACTIVE' WHERE id = :sku",
            "MISSING_SKU_CATALOGUE",
        ),
        (
            "UPDATE ar.payment_terms SET is_default = false "
            "WHERE company_id = :company",
            "MISSING_DEFAULT_PAYMENT_TERM",
        ),
        (
            "UPDATE core.company_bank_accounts SET is_default_for_billing = false "
            "WHERE company_id = :company",
            "MISSING_DEFAULT_BILLING_BANK",
        ),
        (
            "UPDATE ar.document_sequences SET status = 'INACTIVE' "
            "WHERE company_id = :company AND document_type = 'PI'",
            "MISSING_PI_NUMBERING",
        ),
        (
            "UPDATE ar.document_sequences SET status = 'INACTIVE' "
            "WHERE company_id = :company AND document_type = 'TI'",
            "MISSING_TI_NUMBERING",
        ),
        (
            "UPDATE ar.document_sequences SET status = 'INACTIVE' "
            "WHERE company_id = :company AND document_type = 'CN'",
            "MISSING_CN_NUMBERING",
        ),
        (
            "UPDATE ar.document_sequences SET status = 'INACTIVE' "
            "WHERE company_id = :company AND document_type = 'DN'",
            "MISSING_DN_NUMBERING",
        ),
        (
            "UPDATE ar.company_document_templates SET status = 'INACTIVE' "
            "WHERE company_id = :company",
            "MISSING_DOCUMENT_PRESENTATION",
        ),
    ],
)
async def test_each_required_configuration_blocks_readiness(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
    mutation: str,
    expected_code: str,
) -> None:
    client, engine, _ = api_context
    ids = await _seed_ready_company(engine)
    await _execute(engine, mutation, ids)
    response = await client.get(
        f"/companies/{ids['company']}/readiness",
        headers={"X-Tenant-ID": str(ids["tenant"])},
    )
    assert response.status_code == 200
    assert response.json()["ready_for_activation"] is False
    assert expected_code in _codes(response.json())


@pytest.mark.parametrize(
    ("business_nature", "inactive_table", "expected_code"),
    [
        ("SERVICES", "ar.service_types", "MISSING_SERVICE_CATALOGUE"),
        ("GOODS", "ar.skus", "MISSING_SKU_CATALOGUE"),
        ("BOTH", "ar.service_types", "MISSING_SERVICE_CATALOGUE"),
        ("BOTH", "ar.skus", "MISSING_SKU_CATALOGUE"),
    ],
)
async def test_business_nature_requires_its_catalogue_paths(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
    business_nature: str,
    inactive_table: str,
    expected_code: str,
) -> None:
    client, engine, _ = api_context
    ids = await _seed_ready_company(engine, business_nature=business_nature)
    await _execute(
        engine,
        f"UPDATE {inactive_table} SET status = 'INACTIVE' WHERE company_id = :company",
        ids,
    )
    response = await client.get(
        f"/companies/{ids['company']}/readiness",
        headers={"X-Tenant-ID": str(ids["tenant"])},
    )
    assert expected_code in _codes(response.json())


@pytest.mark.parametrize(
    "mutation",
    [
        "UPDATE core.company_hsn_sac_codes SET status = 'INACTIVE' "
        "WHERE id = :sac",
        "UPDATE core.uoms SET status = 'INACTIVE' WHERE code = 'NOS'",
        "UPDATE ar.service_types SET selected_tax_rate_id = NULL "
        "WHERE id = :service",
        "UPDATE ar.service_types SET base_tax_treatment_id = :nil_rated, "
        "selected_tax_rate_id = :tax_rate WHERE id = :service",
        "UPDATE ar.service_types SET base_tax_treatment_id = :exempt, "
        "selected_tax_rate_id = :tax_rate WHERE id = :service",
        "UPDATE ar.service_types SET base_tax_treatment_id = :non_gst, "
        "selected_tax_rate_id = :tax_rate WHERE id = :service",
    ],
)
async def test_incomplete_active_catalogue_items_block(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
    mutation: str,
) -> None:
    client, engine, _ = api_context
    ids = await _seed_ready_company(engine)
    await _execute(engine, mutation, ids)
    response = await client.get(
        f"/companies/{ids['company']}/readiness",
        headers={"X-Tenant-ID": str(ids["tenant"])},
    )
    assert "INCOMPLETE_ACTIVE_CATALOGUE_ITEM" in _codes(response.json())


async def test_service_uom_is_optional_and_non_blockers_are_absent(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    ids = await _seed_ready_company(engine, business_nature="SERVICES")
    response = await client.get(
        f"/companies/{ids['company']}/readiness",
        headers={"X-Tenant-ID": str(ids["tenant"])},
    )
    assert response.json()["ready_for_activation"] is True
    # The fixture intentionally has no Accounting/GL mappings, Cost Centers,
    # email, reminders, Team membership, LUT, FX rates, or FX policies.
    assert response.json()["blocking_checks"] == []


async def test_dynamic_llpin_rule_blocks_without_hardcoded_entity_name(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    ids = await _seed_ready_company(engine)
    llpin_type = await _scalar(
        engine,
        "INSERT INTO core.company_identifier_types "
        "(country_code, code, name, status) "
        "VALUES ('IN', 'LLPIN', 'LLP Identification Number', 'ACTIVE') "
        "RETURNING id",
    )
    await _execute(
        engine,
        "INSERT INTO core.entity_type_identifier_rules "
        "(entity_type_id, identifier_type_id, requirement_level) "
        "VALUES (:entity_type, :llpin, 'REQUIRED')",
        {"entity_type": ids["entity_type"], "llpin": llpin_type},
    )
    response = await client.get(
        f"/companies/{ids['company']}/readiness",
        headers={"X-Tenant-ID": str(ids["tenant"])},
    )
    failed = next(
        check
        for check in response.json()["blocking_checks"]
        if check["code"] == "MISSING_REQUIRED_ENTITY_IDENTIFIER"
    )
    assert "LLPIN" in failed["message"]


async def test_cross_tenant_is_concealed_for_both_endpoints(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    ids = await _seed_ready_company(engine)
    other_tenant = await _scalar(
        engine,
        "INSERT INTO core.tenants (name, status) "
        "VALUES (:name, 'ACTIVE') RETURNING id",
        {"name": f"Other {uuid4()}"},
    )
    headers = {"X-Tenant-ID": str(other_tenant)}
    readiness = await client.get(
        f"/companies/{ids['company']}/readiness", headers=headers
    )
    activation = await client.post(
        f"/companies/{ids['company']}/activate", headers=headers
    )
    assert readiness.status_code == 404
    assert activation.status_code == 404


async def test_failed_activation_returns_same_blockers_without_mutation(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    ids = await _seed_ready_company(engine)
    await _execute(
        engine,
        "UPDATE core.company_identifiers SET status = 'INACTIVE' "
        "WHERE identifier_type_id = :pan_type",
        ids,
    )
    headers = {"X-Tenant-ID": str(ids["tenant"])}
    preview = await client.get(
        f"/companies/{ids['company']}/readiness", headers=headers
    )
    activation = await client.post(
        f"/companies/{ids['company']}/activate", headers=headers
    )
    stored_status = await _scalar(
        engine,
        "SELECT status FROM core.companies WHERE id = :company",
        ids,
    )
    assert activation.status_code == 409
    assert activation.json()["detail"]["blocking_checks"] == preview.json()[
        "blocking_checks"
    ]
    assert stored_status == "DRAFT"


async def test_inactive_is_terminal_and_patch_cannot_mutate_status(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    ids = await _seed_ready_company(engine)
    await _execute(
        engine,
        "UPDATE core.companies SET status = 'INACTIVE' WHERE id = :company",
        ids,
    )
    headers = {"X-Tenant-ID": str(ids["tenant"])}
    activation = await client.post(
        f"/companies/{ids['company']}/activate", headers=headers
    )
    patch = await client.patch(
        f"/companies/{ids['company']}",
        headers=headers,
        json={"status": "ACTIVE"},
    )
    assert activation.status_code == 409
    assert "COMPANY_INACTIVE" in {
        check["code"]
        for check in activation.json()["detail"]["blocking_checks"]
    }
    assert patch.status_code == 422
