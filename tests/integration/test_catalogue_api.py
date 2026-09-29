import asyncio
import os
from collections.abc import AsyncGenerator, AsyncIterator, Iterator, Mapping
from contextlib import asynccontextmanager
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
def migrated_database() -> Iterator[str]:
    database_url = os.getenv("TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL API tests")
    if make_url(database_url).drivername != "postgresql+asyncpg":
        pytest.fail("TEST_DATABASE_URL must use postgresql+asyncpg")
    asyncio.run(_assert_safe_empty_database(database_url))
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    get_settings.cache_clear()
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    try:
        yield database_url
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

    test_engine = create_async_engine(migrated_database)
    factory = async_sessionmaker(bind=test_engine, class_=AsyncSession)

    async def override_db_session() -> AsyncGenerator[AsyncSession, None]:
        async with factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    settings = Settings(database_url=migrated_database, environment="development")
    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_settings] = lambda: settings
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        try:
            yield client, test_engine, app
        finally:
            app.dependency_overrides.clear()
            async with test_engine.begin() as connection:
                await connection.execute(text("TRUNCATE core.tenants CASCADE"))
                await connection.execute(text("TRUNCATE core.countries CASCADE"))
            await test_engine.dispose()


async def _execute(
    engine: AsyncEngine, sql: str, parameters: Mapping[str, object] | None = None
) -> None:
    async with engine.begin() as connection:
        await connection.execute(text(sql), parameters or {})


async def _scalar(
    engine: AsyncEngine, sql: str, parameters: Mapping[str, object] | None = None
) -> object:
    async with engine.begin() as connection:
        return await connection.scalar(text(sql), parameters or {})


async def _insert_tenant(engine: AsyncEngine) -> UUID:
    return await _scalar(
        engine,
        "INSERT INTO core.tenants (name, status) "
        "VALUES (:name, 'ACTIVE') RETURNING id",
        {"name": f"Tenant {uuid4()}"},
    )


async def _insert_company(
    engine: AsyncEngine,
    *,
    tenant_id: UUID,
    business_nature: str,
    status: str = "DRAFT",
) -> UUID:
    if not await _scalar(
        engine, "SELECT count(*) FROM core.countries WHERE code = 'IN'"
    ):
        await _execute(
            engine,
            "INSERT INTO core.countries (code, name, status) "
            "VALUES ('IN', 'India', 'ACTIVE')",
        )
    return await _scalar(
        engine,
        "INSERT INTO core.companies "
        "(tenant_id, legal_name, country_code, business_nature, status) "
        "VALUES (:tenant_id, :name, 'IN', :nature, :status) RETURNING id",
        {
            "tenant_id": tenant_id,
            "name": f"Company {uuid4()}",
            "nature": business_nature,
            "status": status,
        },
    )


async def _seed_tax(
    engine: AsyncEngine, *, company_id: UUID, classification_type: str
) -> dict[str, UUID]:
    if not await _scalar(
        engine, "SELECT count(*) FROM core.countries WHERE code = 'IN'"
    ):
        await _execute(
            engine,
            "INSERT INTO core.countries (code, name, status) "
            "VALUES ('IN', 'India', 'ACTIVE')",
        )
    tax_type_id = await _scalar(
        engine,
        "SELECT id FROM core.tax_types WHERE country_code = 'IN' AND code = 'GST'",
    )
    if tax_type_id is None:
        tax_type_id = await _scalar(
            engine,
            "INSERT INTO core.tax_types (code, name, country_code, status) "
            "VALUES ('GST', 'Goods and Services Tax', 'IN', 'ACTIVE') RETURNING id",
        )
    tax_rate_id = await _scalar(
        engine,
        "SELECT id FROM core.tax_rates WHERE tax_type_id = :tax_type_id",
        {"tax_type_id": tax_type_id},
    )
    if tax_rate_id is None:
        tax_rate_id = await _scalar(
            engine,
            "INSERT INTO core.tax_rates "
            "(tax_type_id, rate_percent, country_code, status) "
            "VALUES (:tax_type_id, 18, 'IN', 'ACTIVE') RETURNING id",
            {"tax_type_id": tax_type_id},
        )
    treatment_id = await _scalar(
        engine,
        "SELECT id FROM core.tax_treatments WHERE tax_type_id = :tax_type_id",
        {"tax_type_id": tax_type_id},
    )
    if treatment_id is None:
        treatment_id = await _scalar(
            engine,
            "INSERT INTO core.tax_treatments "
            "(code, name, tax_type_id, country_code, status) "
            "VALUES ('TAXABLE', 'Taxable', :tax_type_id, 'IN', 'ACTIVE') "
            "RETURNING id",
            {"tax_type_id": tax_type_id},
        )
    classification_id = await _scalar(
        engine,
        "INSERT INTO core.company_hsn_sac_codes "
        "(company_id, classification_type, code, description, status) "
        "VALUES (:company_id, :kind, :code, 'Classification', 'ACTIVE') "
        "RETURNING id",
        {
            "company_id": company_id,
            "kind": classification_type,
            "code": f"{classification_type}{uuid4().hex[:8]}",
        },
    )
    await _execute(
        engine,
        "INSERT INTO core.company_hsn_sac_tax_rates "
        "(company_hsn_sac_code_id, tax_rate_id, valid_from, valid_to, status) "
        "VALUES (:classification_id, :tax_rate_id, '2000-01-01', "
        "'2000-12-31', 'ACTIVE')",
        {"classification_id": classification_id, "tax_rate_id": tax_rate_id},
    )
    return {
        "classification_id": classification_id,
        "tax_rate_id": tax_rate_id,
        "treatment_id": treatment_id,
    }


async def _insert_unmapped_gst_rate(
    engine: AsyncEngine,
    *,
    rate_percent: int,
) -> UUID:
    tax_type_id = await _scalar(
        engine,
        "SELECT id FROM core.tax_types WHERE country_code = 'IN' AND code = 'GST'",
    )
    return await _scalar(
        engine,
        """
        INSERT INTO core.tax_rates
            (tax_type_id, rate_percent, country_code, status)
        VALUES
            (:tax_type_id, :rate_percent, 'IN', 'ACTIVE')
        RETURNING id
        """,
        {"tax_type_id": tax_type_id, "rate_percent": rate_percent},
    )


async def _insert_eligible_gst_rate(
    engine: AsyncEngine,
    *,
    classification_id: UUID,
    rate_percent: int,
    status: str = "ACTIVE",
) -> UUID:
    tax_rate_id = await _insert_unmapped_gst_rate(
        engine,
        rate_percent=rate_percent,
    )
    await _execute(
        engine,
        "INSERT INTO core.company_hsn_sac_tax_rates "
        "(company_hsn_sac_code_id, tax_rate_id, valid_from, status) "
        "VALUES (:classification_id, :tax_rate_id, '2001-01-01', 'ACTIVE')",
        {
            "classification_id": classification_id,
            "tax_rate_id": tax_rate_id,
        },
    )
    if status != "ACTIVE":
        await _execute(
            engine,
            "UPDATE core.tax_rates SET status = :status WHERE id = :tax_rate_id",
            {"status": status, "tax_rate_id": tax_rate_id},
        )
    return tax_rate_id


async def _insert_gst_treatment(
    engine: AsyncEngine,
    *,
    code: str,
    status: str = "ACTIVE",
) -> UUID:
    tax_type_id = await _scalar(
        engine,
        "SELECT id FROM core.tax_types WHERE country_code = 'IN' AND code = 'GST'",
    )
    return await _scalar(
        engine,
        """
        INSERT INTO core.tax_treatments
            (code, name, tax_type_id, country_code, status)
        VALUES
            (:code, :name, :tax_type_id, 'IN', :status)
        RETURNING id
        """,
        {
            "code": code,
            "name": f"Treatment {code}",
            "tax_type_id": tax_type_id,
            "status": status,
        },
    )


async def _post(
    client: AsyncClient,
    *,
    tenant_id: UUID,
    company_id: UUID,
    path: str,
    payload: dict[str, object],
):
    return await client.post(
        f"/companies/{company_id}/{path}",
        headers={"X-Tenant-ID": str(tenant_id)},
        json=payload,
    )


async def test_service_catalogue_creation_and_duplicate_rules(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = await _insert_tenant(engine)
    company_id = await _insert_company(
        engine, tenant_id=tenant_id, business_nature="SERVICES"
    )
    tax = await _seed_tax(engine, company_id=company_id, classification_type="SAC")
    category = await _post(
        client,
        tenant_id=tenant_id,
        company_id=company_id,
        path="service-categories",
        payload={"name": "Advisory", "code": "ADV"},
    )
    service = await _post(
        client,
        tenant_id=tenant_id,
        company_id=company_id,
        path="service-types",
        payload={
            "service_category_id": category.json()["id"],
            "name": "GST Advisory",
            "company_hsn_sac_code_id": str(tax["classification_id"]),
            "selected_tax_rate_id": str(tax["tax_rate_id"]),
            "base_tax_treatment_id": str(tax["treatment_id"]),
        },
    )
    duplicate = await _post(
        client,
        tenant_id=tenant_id,
        company_id=company_id,
        path="service-categories",
        payload={"name": "Advisory"},
    )
    injected = await _post(
        client,
        tenant_id=tenant_id,
        company_id=company_id,
        path="service-categories",
        payload={"name": "Injected", "status": "INACTIVE"},
    )

    assert category.status_code == 201
    assert category.json()["status"] == "ACTIVE"
    assert service.status_code == 201
    assert service.json()["status"] == "ACTIVE"
    assert duplicate.status_code == 409
    assert injected.status_code == 422
    assert await _scalar(engine, "SELECT count(*) FROM ar.service_types") == 1


async def test_goods_catalogue_creation_and_inactive_parent_rejection(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = await _insert_tenant(engine)
    company_id = await _insert_company(
        engine, tenant_id=tenant_id, business_nature="GOODS"
    )
    tax = await _seed_tax(engine, company_id=company_id, classification_type="HSN")
    category = await _post(
        client,
        tenant_id=tenant_id,
        company_id=company_id,
        path="product-categories",
        payload={"name": "Electronics"},
    )
    product = await _post(
        client,
        tenant_id=tenant_id,
        company_id=company_id,
        path="products",
        payload={
            "product_category_id": category.json()["id"],
            "name": "Laptop",
        },
    )
    sku_payload = {
        "product_id": product.json()["id"],
        "sku_code": "LAPTOP-I5-16-512",
        "name": "Laptop i5",
        "uom": "EA",
        "company_hsn_sac_code_id": str(tax["classification_id"]),
        "selected_tax_rate_id": str(tax["tax_rate_id"]),
        "base_tax_treatment_id": str(tax["treatment_id"]),
    }
    sku = await _post(
        client,
        tenant_id=tenant_id,
        company_id=company_id,
        path="skus",
        payload=sku_payload,
    )
    await _execute(
        engine,
        "UPDATE ar.products SET status = 'INACTIVE' WHERE id = :id",
        {"id": UUID(product.json()["id"])},
    )
    inactive_parent = await _post(
        client,
        tenant_id=tenant_id,
        company_id=company_id,
        path="skus",
        payload={**sku_payload, "sku_code": "ANOTHER-SKU"},
    )

    assert category.status_code == 201
    assert product.status_code == 201
    assert sku.status_code == 201
    assert sku.json()["tcs_check_required"] is False
    assert inactive_parent.status_code == 409


async def test_service_type_base_gst_nature_validation_matrix(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = await _insert_tenant(engine)
    company_id = await _insert_company(
        engine,
        tenant_id=tenant_id,
        business_nature="SERVICES",
    )
    tax = await _seed_tax(
        engine,
        company_id=company_id,
        classification_type="SAC",
    )
    category = await _post(
        client,
        tenant_id=tenant_id,
        company_id=company_id,
        path="service-categories",
        payload={"name": "GST Services"},
    )
    assert category.status_code == 201

    zero_rate_id = await _insert_eligible_gst_rate(
        engine,
        classification_id=tax["classification_id"],
        rate_percent=0,
    )
    nil_rated_id = await _insert_gst_treatment(engine, code="NIL_RATED")
    exempt_id = await _insert_gst_treatment(engine, code="EXEMPT")
    non_gst_id = await _insert_gst_treatment(engine, code="NON_GST")
    zero_rated_id = await _insert_gst_treatment(engine, code="ZERO_RATED")
    custom_id = await _insert_gst_treatment(engine, code="CUSTOM_GST")

    sequence = 0

    async def create_service(
        *,
        base_tax_treatment_id: UUID,
        selected_tax_rate_id: UUID | None,
    ):
        nonlocal sequence
        sequence += 1
        return await _post(
            client,
            tenant_id=tenant_id,
            company_id=company_id,
            path="service-types",
            payload={
                "service_category_id": category.json()["id"],
                "name": f"GST Service {sequence}",
                "company_hsn_sac_code_id": str(tax["classification_id"]),
                "base_tax_treatment_id": str(base_tax_treatment_id),
                "selected_tax_rate_id": (
                    str(selected_tax_rate_id)
                    if selected_tax_rate_id is not None
                    else None
                ),
            },
        )

    taxable = await create_service(
        base_tax_treatment_id=tax["treatment_id"],
        selected_tax_rate_id=tax["tax_rate_id"],
    )
    taxable_missing_rate = await create_service(
        base_tax_treatment_id=tax["treatment_id"],
        selected_tax_rate_id=None,
    )
    taxable_zero_rate = await create_service(
        base_tax_treatment_id=tax["treatment_id"],
        selected_tax_rate_id=zero_rate_id,
    )
    nil_rated = await create_service(
        base_tax_treatment_id=nil_rated_id,
        selected_tax_rate_id=zero_rate_id,
    )
    nil_missing_rate = await create_service(
        base_tax_treatment_id=nil_rated_id,
        selected_tax_rate_id=None,
    )
    nil_nonzero_rate = await create_service(
        base_tax_treatment_id=nil_rated_id,
        selected_tax_rate_id=tax["tax_rate_id"],
    )
    exempt = await create_service(
        base_tax_treatment_id=exempt_id,
        selected_tax_rate_id=None,
    )
    exempt_with_rate = await create_service(
        base_tax_treatment_id=exempt_id,
        selected_tax_rate_id=zero_rate_id,
    )
    non_gst = await create_service(
        base_tax_treatment_id=non_gst_id,
        selected_tax_rate_id=None,
    )
    non_gst_with_rate = await create_service(
        base_tax_treatment_id=non_gst_id,
        selected_tax_rate_id=zero_rate_id,
    )
    zero_rated = await create_service(
        base_tax_treatment_id=zero_rated_id,
        selected_tax_rate_id=None,
    )
    custom = await create_service(
        base_tax_treatment_id=custom_id,
        selected_tax_rate_id=None,
    )

    ineligible_rate_id = await _insert_unmapped_gst_rate(
        engine,
        rate_percent=12,
    )
    ineligible = await create_service(
        base_tax_treatment_id=tax["treatment_id"],
        selected_tax_rate_id=ineligible_rate_id,
    )
    inactive_rate_id = await _insert_eligible_gst_rate(
        engine,
        classification_id=tax["classification_id"],
        rate_percent=5,
        status="INACTIVE",
    )
    inactive_rate = await create_service(
        base_tax_treatment_id=tax["treatment_id"],
        selected_tax_rate_id=inactive_rate_id,
    )

    tds_type_id = await _scalar(
        engine,
        "INSERT INTO core.tax_types (code, name, country_code, status) "
        "VALUES ('TDS', 'Tax Deducted at Source', 'IN', 'ACTIVE') RETURNING id",
    )
    tds_rate_id = await _scalar(
        engine,
        "INSERT INTO core.tax_rates "
        "(tax_type_id, rate_percent, country_code, status) "
        "VALUES (:tax_type_id, 10, 'IN', 'ACTIVE') RETURNING id",
        {"tax_type_id": tds_type_id},
    )
    await _execute(
        engine,
        "INSERT INTO core.company_hsn_sac_tax_rates "
        "(company_hsn_sac_code_id, tax_rate_id, valid_from, status) "
        "VALUES (:classification_id, :tax_rate_id, '2001-01-01', 'ACTIVE')",
        {
            "classification_id": tax["classification_id"],
            "tax_rate_id": tds_rate_id,
        },
    )
    tds_treatment_id = await _scalar(
        engine,
        "INSERT INTO core.tax_treatments "
        "(code, name, tax_type_id, country_code, status) "
        "VALUES ('TAXABLE', 'TDS Taxable', :tax_type_id, 'IN', 'ACTIVE') "
        "RETURNING id",
        {"tax_type_id": tds_type_id},
    )
    non_gst_rate = await create_service(
        base_tax_treatment_id=tax["treatment_id"],
        selected_tax_rate_id=tds_rate_id,
    )
    wrong_tax_family = await create_service(
        base_tax_treatment_id=tds_treatment_id,
        selected_tax_rate_id=tds_rate_id,
    )

    await _execute(
        engine,
        "UPDATE core.tax_treatments SET status = 'INACTIVE' WHERE id = :id",
        {"id": exempt_id},
    )
    inactive_treatment = await create_service(
        base_tax_treatment_id=exempt_id,
        selected_tax_rate_id=None,
    )

    assert taxable.status_code == 201
    assert taxable.json()["base_tax_treatment_id"] == str(tax["treatment_id"])
    assert taxable.json()["selected_tax_rate_id"] == str(tax["tax_rate_id"])
    assert "tax_treatment_id" not in taxable.json()
    assert taxable_missing_rate.status_code == 422
    assert taxable_zero_rate.status_code == 201
    assert taxable_zero_rate.json()["base_tax_treatment_id"] == str(
        tax["treatment_id"]
    )
    assert nil_rated.status_code == 201
    assert nil_missing_rate.status_code == 422
    assert nil_nonzero_rate.status_code == 422
    assert exempt.status_code == 201
    assert exempt.json()["selected_tax_rate_id"] is None
    assert exempt_with_rate.status_code == 422
    assert non_gst.status_code == 201
    assert non_gst.json()["selected_tax_rate_id"] is None
    assert non_gst_with_rate.status_code == 422
    assert zero_rated.status_code == 422
    assert custom.status_code == 422
    assert ineligible.status_code == 422
    assert inactive_rate.status_code == 409
    assert non_gst_rate.status_code == 422
    assert wrong_tax_family.status_code == 422
    assert inactive_treatment.status_code == 409


async def test_sku_base_gst_nature_update_transitions_validate_final_state(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = await _insert_tenant(engine)
    company_id = await _insert_company(
        engine,
        tenant_id=tenant_id,
        business_nature="GOODS",
    )
    tax = await _seed_tax(
        engine,
        company_id=company_id,
        classification_type="HSN",
    )
    zero_rate_id = await _insert_eligible_gst_rate(
        engine,
        classification_id=tax["classification_id"],
        rate_percent=0,
    )
    nil_rated_id = await _insert_gst_treatment(engine, code="NIL_RATED")
    exempt_id = await _insert_gst_treatment(engine, code="EXEMPT")
    category = await _post(
        client,
        tenant_id=tenant_id,
        company_id=company_id,
        path="product-categories",
        payload={"name": "Devices"},
    )
    product = await _post(
        client,
        tenant_id=tenant_id,
        company_id=company_id,
        path="products",
        payload={
            "product_category_id": category.json()["id"],
            "name": "Terminal",
        },
    )
    sku = await _post(
        client,
        tenant_id=tenant_id,
        company_id=company_id,
        path="skus",
        payload={
            "product_id": product.json()["id"],
            "sku_code": "TERM-GST",
            "name": "Terminal",
            "uom": "EA",
            "company_hsn_sac_code_id": str(tax["classification_id"]),
            "base_tax_treatment_id": str(tax["treatment_id"]),
            "selected_tax_rate_id": str(tax["tax_rate_id"]),
        },
    )
    assert sku.status_code == 201
    sku_url = f"/companies/{company_id}/skus/{sku.json()['id']}"
    headers = {"X-Tenant-ID": str(tenant_id)}

    exempt_retaining_rate = await client.patch(
        sku_url,
        headers=headers,
        json={"base_tax_treatment_id": str(exempt_id)},
    )
    exempt = await client.patch(
        sku_url,
        headers=headers,
        json={
            "base_tax_treatment_id": str(exempt_id),
            "selected_tax_rate_id": None,
        },
    )
    taxable_missing_rate = await client.patch(
        sku_url,
        headers=headers,
        json={"base_tax_treatment_id": str(tax["treatment_id"])},
    )
    taxable = await client.patch(
        sku_url,
        headers=headers,
        json={
            "base_tax_treatment_id": str(tax["treatment_id"]),
            "selected_tax_rate_id": str(tax["tax_rate_id"]),
        },
    )
    nil_rated = await client.patch(
        sku_url,
        headers=headers,
        json={
            "base_tax_treatment_id": str(nil_rated_id),
            "selected_tax_rate_id": str(zero_rate_id),
        },
    )

    assert exempt_retaining_rate.status_code == 422
    assert exempt.status_code == 200
    assert exempt.json()["selected_tax_rate_id"] is None
    assert taxable_missing_rate.status_code == 422
    assert taxable.status_code == 200
    assert taxable.json()["selected_tax_rate_id"] == str(tax["tax_rate_id"])
    assert nil_rated.status_code == 200
    assert nil_rated.json()["base_tax_treatment_id"] == str(nil_rated_id)
    assert nil_rated.json()["selected_tax_rate_id"] == str(zero_rate_id)


async def test_business_nature_tenant_and_company_lifecycle_rules(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = await _insert_tenant(engine)
    other_tenant_id = await _insert_tenant(engine)
    services_company = await _insert_company(
        engine, tenant_id=tenant_id, business_nature="SERVICES"
    )
    goods_company = await _insert_company(
        engine, tenant_id=tenant_id, business_nature="GOODS"
    )
    cross_tenant_company = await _insert_company(
        engine, tenant_id=other_tenant_id, business_nature="BOTH"
    )
    inactive_company = await _insert_company(
        engine,
        tenant_id=tenant_id,
        business_nature="BOTH",
        status="INACTIVE",
    )

    wrong_service = await _post(
        client,
        tenant_id=tenant_id,
        company_id=goods_company,
        path="service-categories",
        payload={"name": "Not Allowed"},
    )
    wrong_goods = await _post(
        client,
        tenant_id=tenant_id,
        company_id=services_company,
        path="product-categories",
        payload={"name": "Not Allowed"},
    )
    hidden = []
    for company_id in (cross_tenant_company, uuid4()):
        hidden.append(
            await _post(
                client,
                tenant_id=tenant_id,
                company_id=company_id,
                path="service-categories",
                payload={"name": "Hidden"},
            )
        )
    inactive = await _post(
        client,
        tenant_id=tenant_id,
        company_id=inactive_company,
        path="service-categories",
        payload={"name": "Inactive"},
    )

    assert wrong_service.status_code == 409
    assert wrong_goods.status_code == 409
    assert [(response.status_code, response.json()) for response in hidden] == [
        (404, {"detail": "Company not found"}),
        (404, {"detail": "Company not found"}),
    ]
    assert inactive.status_code == 409
    assert await _scalar(engine, "SELECT count(*) FROM ar.service_categories") == 0
    assert await _scalar(engine, "SELECT count(*) FROM ar.product_categories") == 0


async def test_cross_company_parent_and_inactive_tax_reference_rejected(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = await _insert_tenant(engine)
    first_company = await _insert_company(
        engine, tenant_id=tenant_id, business_nature="BOTH"
    )
    second_company = await _insert_company(
        engine, tenant_id=tenant_id, business_nature="BOTH"
    )
    first_tax = await _seed_tax(
        engine, company_id=first_company, classification_type="SAC"
    )
    second_category = await _post(
        client,
        tenant_id=tenant_id,
        company_id=second_company,
        path="service-categories",
        payload={"name": "Shared Name"},
    )
    first_category = await _post(
        client,
        tenant_id=tenant_id,
        company_id=first_company,
        path="service-categories",
        payload={"name": "Shared Name"},
    )
    product_category = await _post(
        client,
        tenant_id=tenant_id,
        company_id=first_company,
        path="product-categories",
        payload={"name": "Goods for Both Company"},
    )
    common_payload = {
        "name": "Advisory",
        "company_hsn_sac_code_id": str(first_tax["classification_id"]),
        "selected_tax_rate_id": str(first_tax["tax_rate_id"]),
        "base_tax_treatment_id": str(first_tax["treatment_id"]),
    }
    cross_parent = await _post(
        client,
        tenant_id=tenant_id,
        company_id=first_company,
        path="service-types",
        payload={
            **common_payload,
            "service_category_id": second_category.json()["id"],
        },
    )
    await _execute(
        engine,
        "UPDATE core.tax_rates SET status = 'INACTIVE' WHERE id = :id",
        {"id": first_tax["tax_rate_id"]},
    )
    inactive_rate = await _post(
        client,
        tenant_id=tenant_id,
        company_id=first_company,
        path="service-types",
        payload={
            **common_payload,
            "service_category_id": first_category.json()["id"],
        },
    )

    assert second_category.status_code == 201
    assert first_category.status_code == 201
    assert product_category.status_code == 201
    assert cross_parent.status_code == 422
    assert inactive_rate.status_code == 409
    assert await _scalar(engine, "SELECT count(*) FROM ar.service_types") == 0


async def test_category_reads_updates_duplicates_and_isolation(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = await _insert_tenant(engine)
    other_tenant_id = await _insert_tenant(engine)
    company_id = await _insert_company(
        engine,
        tenant_id=tenant_id,
        business_nature="BOTH",
    )
    sibling_company_id = await _insert_company(
        engine,
        tenant_id=tenant_id,
        business_nature="BOTH",
    )
    other_company_id = await _insert_company(
        engine,
        tenant_id=other_tenant_id,
        business_nature="BOTH",
    )

    service_category = await _post(
        client,
        tenant_id=tenant_id,
        company_id=company_id,
        path="service-categories",
        payload={"name": "Advisory", "code": "ADV"},
    )
    duplicate_service_category = await _post(
        client,
        tenant_id=tenant_id,
        company_id=company_id,
        path="service-categories",
        payload={"name": "Consulting", "code": "CON"},
    )
    product_category = await _post(
        client,
        tenant_id=tenant_id,
        company_id=company_id,
        path="product-categories",
        payload={"name": "Electronics", "code": "ELEC"},
    )
    other_category = await _post(
        client,
        tenant_id=other_tenant_id,
        company_id=other_company_id,
        path="service-categories",
        payload={"name": "Other Tenant"},
    )
    assert (
        service_category.status_code
        == duplicate_service_category.status_code
        == product_category.status_code
        == other_category.status_code
        == 201
    )

    service_list = await client.get(
        f"/companies/{company_id}/service-categories",
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    service_get = await client.get(
        f"/companies/{company_id}/service-categories/"
        f"{service_category.json()['id']}",
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    product_list = await client.get(
        f"/companies/{company_id}/product-categories",
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    product_get = await client.get(
        f"/companies/{company_id}/product-categories/"
        f"{product_category.json()['id']}",
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    cross_company = await client.get(
        f"/companies/{sibling_company_id}/service-categories/"
        f"{service_category.json()['id']}",
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    cross_product_company = await client.get(
        f"/companies/{sibling_company_id}/product-categories/"
        f"{product_category.json()['id']}",
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    cross_tenant = await client.get(
        f"/companies/{other_company_id}/service-categories/"
        f"{other_category.json()['id']}",
        headers={"X-Tenant-ID": str(tenant_id)},
    )

    assert service_list.status_code == 200
    assert {item["id"] for item in service_list.json()} == {
        service_category.json()["id"],
        duplicate_service_category.json()["id"],
    }
    assert service_get.status_code == 200
    assert product_list.status_code == 200
    assert [item["id"] for item in product_list.json()] == [
        product_category.json()["id"]
    ]
    assert product_get.status_code == 200
    assert cross_company.status_code == 404
    assert cross_product_company.status_code == 404
    assert cross_tenant.status_code == 404

    updated_service = await client.patch(
        f"/companies/{company_id}/service-categories/"
        f"{service_category.json()['id']}",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={"name": "  Advisory Services  "},
    )
    updated_product = await client.patch(
        f"/companies/{company_id}/product-categories/"
        f"{product_category.json()['id']}",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={"name": "  Consumer Electronics  "},
    )
    duplicate_update = await client.patch(
        f"/companies/{company_id}/service-categories/"
        f"{service_category.json()['id']}",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={"name": "Consulting"},
    )
    second_product_category = await _post(
        client,
        tenant_id=tenant_id,
        company_id=company_id,
        path="product-categories",
        payload={"name": "Hardware"},
    )
    duplicate_product_update = await client.patch(
        f"/companies/{company_id}/product-categories/"
        f"{product_category.json()['id']}",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={"name": "Hardware"},
    )

    assert updated_service.status_code == 200
    assert updated_service.json()["name"] == "Advisory Services"
    assert updated_service.json()["code"] == "ADV"
    assert updated_product.status_code == 200
    assert updated_product.json()["name"] == "Consumer Electronics"
    assert duplicate_update.status_code == 409
    assert second_product_category.status_code == 201
    assert duplicate_product_update.status_code == 409

    for path, field_name in (
        ("service-categories", "code"),
        ("service-categories", "status"),
        ("product-categories", "code"),
        ("product-categories", "status"),
    ):
        category_id = (
            service_category.json()["id"]
            if path == "service-categories"
            else product_category.json()["id"]
        )
        rejected = await client.patch(
            f"/companies/{company_id}/{path}/{category_id}",
            headers={"X-Tenant-ID": str(tenant_id)},
            json={field_name: "not-allowed"},
        )
        assert rejected.status_code == 422


async def test_service_type_reads_updates_tax_validation_and_lifecycle(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = await _insert_tenant(engine)
    company_id = await _insert_company(
        engine,
        tenant_id=tenant_id,
        business_nature="SERVICES",
    )
    other_company_id = await _insert_company(
        engine,
        tenant_id=tenant_id,
        business_nature="SERVICES",
    )
    first_sac = await _seed_tax(
        engine,
        company_id=company_id,
        classification_type="SAC",
    )
    second_sac = await _seed_tax(
        engine,
        company_id=company_id,
        classification_type="SAC",
    )
    hsn = await _seed_tax(
        engine,
        company_id=company_id,
        classification_type="HSN",
    )
    other_sac = await _seed_tax(
        engine,
        company_id=other_company_id,
        classification_type="SAC",
    )
    eligible_rate_id = await _insert_unmapped_gst_rate(
        engine,
        rate_percent=5,
    )
    await _execute(
        engine,
        """
        INSERT INTO core.company_hsn_sac_tax_rates
            (company_hsn_sac_code_id, tax_rate_id, valid_from, status)
        VALUES
            (:classification_id, :tax_rate_id, '2001-01-01', 'ACTIVE')
        """,
        {
            "classification_id": second_sac["classification_id"],
            "tax_rate_id": eligible_rate_id,
        },
    )
    updated_treatment_id = await _insert_gst_treatment(
        engine,
        code="EXEMPT",
    )
    unmapped_rate_id = await _insert_unmapped_gst_rate(
        engine,
        rate_percent=12,
    )
    category = await _post(
        client,
        tenant_id=tenant_id,
        company_id=company_id,
        path="service-categories",
        payload={"name": "Advisory"},
    )
    service_type = await _post(
        client,
        tenant_id=tenant_id,
        company_id=company_id,
        path="service-types",
        payload={
            "service_category_id": category.json()["id"],
            "name": "GST Advisory",
            "code": "GST-ADV",
            "company_hsn_sac_code_id": str(first_sac["classification_id"]),
            "selected_tax_rate_id": str(first_sac["tax_rate_id"]),
            "base_tax_treatment_id": str(first_sac["treatment_id"]),
        },
    )
    assert service_type.status_code == 201
    service_url = (
        f"/companies/{company_id}/service-types/{service_type.json()['id']}"
    )

    listed = await client.get(
        f"/companies/{company_id}/service-types",
        params={"service_category_id": category.json()["id"]},
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    fetched = await client.get(
        service_url,
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    concealed = await client.get(
        f"/companies/{other_company_id}/service-types/"
        f"{service_type.json()['id']}",
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [
        service_type.json()["id"]
    ]
    assert fetched.status_code == 200
    assert concealed.status_code == 404

    updated = await client.patch(
        service_url,
        headers={"X-Tenant-ID": str(tenant_id)},
        json={
            "name": "  Updated Advisory  ",
            "description": "  Updated description  ",
            "uom": "  HOUR  ",
            "company_hsn_sac_code_id": str(second_sac["classification_id"]),
            "selected_tax_rate_id": None,
            "base_tax_treatment_id": str(updated_treatment_id),
            "tcs_check_required": True,
        },
    )
    wrong_kind = await client.patch(
        service_url,
        headers={"X-Tenant-ID": str(tenant_id)},
        json={"company_hsn_sac_code_id": str(hsn["classification_id"])},
    )
    cross_company = await client.patch(
        service_url,
        headers={"X-Tenant-ID": str(tenant_id)},
        json={
            "company_hsn_sac_code_id": str(other_sac["classification_id"])
        },
    )
    ineligible_rate = await client.patch(
        service_url,
        headers={"X-Tenant-ID": str(tenant_id)},
        json={"selected_tax_rate_id": str(unmapped_rate_id)},
    )

    assert updated.status_code == 200
    assert updated.json()["name"] == "Updated Advisory"
    assert updated.json()["description"] == "Updated description"
    assert updated.json()["uom"] == "HOUR"
    assert updated.json()["company_hsn_sac_code_id"] == str(
        second_sac["classification_id"]
    )
    assert updated.json()["selected_tax_rate_id"] is None
    assert updated.json()["base_tax_treatment_id"] == str(updated_treatment_id)
    assert updated.json()["tcs_check_required"] is True
    assert updated.json()["business_segment_id"] is None
    assert wrong_kind.status_code == 422
    assert cross_company.status_code == 422
    assert ineligible_rate.status_code == 422

    for field_name in (
        "code",
        "service_category_id",
        "business_segment_id",
        "status",
    ):
        rejected = await client.patch(
            service_url,
            headers={"X-Tenant-ID": str(tenant_id)},
            json={field_name: "not-allowed"},
        )
        assert rejected.status_code == 422

    active_parent_rejected = await client.post(
        f"/companies/{company_id}/service-categories/"
        f"{category.json()['id']}/inactivate",
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    inactivated = await client.post(
        f"{service_url}/inactivate",
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    reactivate = await client.post(
        f"{service_url}/activate",
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    parent_inactivate = await client.post(
        f"/companies/{company_id}/service-categories/"
        f"{category.json()['id']}/inactivate",
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    assert inactivated.status_code == 200
    assert inactivated.json()["status"] == "INACTIVE"
    assert active_parent_rejected.status_code == 409
    assert reactivate.status_code == 404
    assert parent_inactivate.status_code == 200
    assert parent_inactivate.json()["status"] == "INACTIVE"
    assert (
        await client.patch(
            service_url,
            headers={"X-Tenant-ID": str(tenant_id)},
            json={"name": "Forbidden"},
        )
    ).status_code == 409
    assert (
        await client.patch(
            f"/companies/{company_id}/service-categories/"
            f"{category.json()['id']}",
            headers={"X-Tenant-ID": str(tenant_id)},
            json={"name": "Forbidden"},
        )
    ).status_code == 409


async def test_catalogue_business_segment_assignment_current_state(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = await _insert_tenant(engine)
    company_id = await _insert_company(
        engine,
        tenant_id=tenant_id,
        business_nature="BOTH",
    )
    other_company_id = await _insert_company(
        engine,
        tenant_id=tenant_id,
        business_nature="BOTH",
    )
    sac = await _seed_tax(
        engine,
        company_id=company_id,
        classification_type="SAC",
    )
    hsn = await _seed_tax(
        engine,
        company_id=company_id,
        classification_type="HSN",
    )
    service_category = await _post(
        client,
        tenant_id=tenant_id,
        company_id=company_id,
        path="service-categories",
        payload={"name": "Advisory"},
    )
    service_type = await _post(
        client,
        tenant_id=tenant_id,
        company_id=company_id,
        path="service-types",
        payload={
            "service_category_id": service_category.json()["id"],
            "name": "GST Advisory",
            "company_hsn_sac_code_id": str(sac["classification_id"]),
            "selected_tax_rate_id": str(sac["tax_rate_id"]),
            "base_tax_treatment_id": str(sac["treatment_id"]),
        },
    )
    product_category = await _post(
        client,
        tenant_id=tenant_id,
        company_id=company_id,
        path="product-categories",
        payload={"name": "Devices"},
    )
    product = await _post(
        client,
        tenant_id=tenant_id,
        company_id=company_id,
        path="products",
        payload={
            "product_category_id": product_category.json()["id"],
            "name": "Laptop",
        },
    )
    sku = await _post(
        client,
        tenant_id=tenant_id,
        company_id=company_id,
        path="skus",
        payload={
            "product_id": product.json()["id"],
            "sku_code": "LAPTOP",
            "name": "Laptop",
            "uom": "EA",
            "company_hsn_sac_code_id": str(hsn["classification_id"]),
            "selected_tax_rate_id": str(hsn["tax_rate_id"]),
            "base_tax_treatment_id": str(hsn["treatment_id"]),
        },
    )
    assert service_type.json()["business_segment_id"] is None
    assert sku.json()["business_segment_id"] is None

    segments = []
    for name, owner_id in (
        ("Domestic", company_id),
        ("International", company_id),
        ("Other Company", other_company_id),
    ):
        segment = await _post(
            client,
            tenant_id=tenant_id,
            company_id=owner_id,
            path="business-segments",
            payload={"name": name},
        )
        assert segment.status_code == 201
        segments.append(segment.json()["id"])

    for entity_path, entity_id in (
        ("service-types", service_type.json()["id"]),
        ("skus", sku.json()["id"]),
    ):
        url = (
            f"/companies/{company_id}/{entity_path}/{entity_id}/"
            "business-segment"
        )
        for target_id in (segments[0], segments[1], None):
            response = await client.put(
                url,
                headers={"X-Tenant-ID": str(tenant_id)},
                json={"business_segment_id": target_id},
            )
            read_back = await client.get(
                f"/companies/{company_id}/{entity_path}/{entity_id}",
                headers={"X-Tenant-ID": str(tenant_id)},
            )
            assert response.status_code == 200
            assert response.json()["business_segment_id"] == target_id
            assert read_back.status_code == 200
            assert read_back.json()["business_segment_id"] == target_id
        cross_company = await client.put(
            url,
            headers={"X-Tenant-ID": str(tenant_id)},
            json={"business_segment_id": segments[2]},
        )
        assert cross_company.status_code == 422

    assigned_before_inactivation = await client.put(
        f"/companies/{company_id}/service-types/"
        f"{service_type.json()['id']}/business-segment",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={"business_segment_id": segments[0]},
    )
    segment_inactivated = await client.post(
        f"/companies/{company_id}/business-segments/"
        f"{segments[0]}/inactivate",
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    inactive_target = await client.put(
        f"/companies/{company_id}/service-types/"
        f"{service_type.json()['id']}/business-segment",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={"business_segment_id": segments[0]},
    )
    inactive_mutation = await client.patch(
        f"/companies/{company_id}/business-segments/{segments[0]}",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={"name": "Forbidden"},
    )
    assert assigned_before_inactivation.status_code == 200
    assert segment_inactivated.status_code == 200
    assert segment_inactivated.json()["status"] == "INACTIVE"
    assert inactive_target.status_code == 409
    assert inactive_mutation.status_code == 409
    assert await _scalar(
        engine,
        "SELECT business_segment_id FROM ar.service_types WHERE id = :id",
        {"id": UUID(service_type.json()["id"])},
    ) == UUID(segments[0])


async def test_product_reads_and_approved_update_fields(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = await _insert_tenant(engine)
    company_id = await _insert_company(
        engine,
        tenant_id=tenant_id,
        business_nature="GOODS",
    )
    other_company_id = await _insert_company(
        engine,
        tenant_id=tenant_id,
        business_nature="GOODS",
    )
    category = await _post(
        client,
        tenant_id=tenant_id,
        company_id=company_id,
        path="product-categories",
        payload={"name": "Electronics"},
    )
    product = await _post(
        client,
        tenant_id=tenant_id,
        company_id=company_id,
        path="products",
        payload={
            "product_category_id": category.json()["id"],
            "name": "Laptop",
            "code": "LAPTOP",
        },
    )
    assert category.status_code == product.status_code == 201
    product_url = f"/companies/{company_id}/products/{product.json()['id']}"

    listed = await client.get(
        f"/companies/{company_id}/products",
        params={"product_category_id": category.json()["id"]},
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    fetched = await client.get(
        product_url,
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    concealed = await client.get(
        f"/companies/{other_company_id}/products/{product.json()['id']}",
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    updated = await client.patch(
        product_url,
        headers={"X-Tenant-ID": str(tenant_id)},
        json={
            "name": "  Business Laptop  ",
            "description": "  Portable computer  ",
        },
    )

    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [product.json()["id"]]
    assert fetched.status_code == 200
    assert concealed.status_code == 404
    assert updated.status_code == 200
    assert updated.json()["name"] == "Business Laptop"
    assert updated.json()["description"] == "Portable computer"
    assert updated.json()["code"] == "LAPTOP"

    for field_name in (
        "code",
        "product_category_id",
        "status",
    ):
        rejected = await client.patch(
            product_url,
            headers={"X-Tenant-ID": str(tenant_id)},
            json={field_name: "not-allowed"},
        )
        assert rejected.status_code == 422

    lifecycle = await client.post(
        f"{product_url}/inactivate",
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    inactive_read = await client.get(
        product_url,
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    inactive_mutation = await client.patch(
        product_url,
        headers={"X-Tenant-ID": str(tenant_id)},
        json={"name": "Forbidden"},
    )
    reactivate = await client.post(
        f"{product_url}/activate",
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    assert lifecycle.status_code == 200
    assert lifecycle.json()["status"] == "INACTIVE"
    assert inactive_read.status_code == 200
    assert inactive_read.json()["status"] == "INACTIVE"
    assert inactive_mutation.status_code == 409
    assert reactivate.status_code == 404


async def test_sku_reads_updates_tax_validation_and_lifecycle(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = await _insert_tenant(engine)
    company_id = await _insert_company(
        engine,
        tenant_id=tenant_id,
        business_nature="GOODS",
    )
    other_company_id = await _insert_company(
        engine,
        tenant_id=tenant_id,
        business_nature="GOODS",
    )
    first_hsn = await _seed_tax(
        engine,
        company_id=company_id,
        classification_type="HSN",
    )
    second_hsn = await _seed_tax(
        engine,
        company_id=company_id,
        classification_type="HSN",
    )
    sac = await _seed_tax(
        engine,
        company_id=company_id,
        classification_type="SAC",
    )
    other_hsn = await _seed_tax(
        engine,
        company_id=other_company_id,
        classification_type="HSN",
    )
    eligible_rate_id = await _insert_unmapped_gst_rate(
        engine,
        rate_percent=12,
    )
    await _execute(
        engine,
        """
        INSERT INTO core.company_hsn_sac_tax_rates
            (company_hsn_sac_code_id, tax_rate_id, valid_from, status)
        VALUES
            (:classification_id, :tax_rate_id, '2001-01-01', 'ACTIVE')
        """,
        {
            "classification_id": second_hsn["classification_id"],
            "tax_rate_id": eligible_rate_id,
        },
    )
    updated_treatment_id = await _insert_gst_treatment(
        engine,
        code="EXEMPT",
    )
    unmapped_rate_id = await _insert_unmapped_gst_rate(
        engine,
        rate_percent=5,
    )
    category = await _post(
        client,
        tenant_id=tenant_id,
        company_id=company_id,
        path="product-categories",
        payload={"name": "Electronics"},
    )
    product = await _post(
        client,
        tenant_id=tenant_id,
        company_id=company_id,
        path="products",
        payload={
            "product_category_id": category.json()["id"],
            "name": "Laptop",
        },
    )
    sku = await _post(
        client,
        tenant_id=tenant_id,
        company_id=company_id,
        path="skus",
        payload={
            "product_id": product.json()["id"],
            "sku_code": "LAPTOP-I5",
            "name": "Laptop i5",
            "uom": "EA",
            "company_hsn_sac_code_id": str(first_hsn["classification_id"]),
            "selected_tax_rate_id": str(first_hsn["tax_rate_id"]),
            "base_tax_treatment_id": str(first_hsn["treatment_id"]),
        },
    )
    assert category.status_code == product.status_code == sku.status_code == 201
    sku_url = f"/companies/{company_id}/skus/{sku.json()['id']}"

    listed = await client.get(
        f"/companies/{company_id}/skus",
        params={"product_id": product.json()["id"]},
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    fetched = await client.get(
        sku_url,
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    concealed = await client.get(
        f"/companies/{other_company_id}/skus/{sku.json()['id']}",
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    updated = await client.patch(
        sku_url,
        headers={"X-Tenant-ID": str(tenant_id)},
        json={
            "name": "  Laptop i5 Updated  ",
            "description": "  Current catalogue description  ",
            "uom": "  UNIT  ",
            "company_hsn_sac_code_id": str(second_hsn["classification_id"]),
            "selected_tax_rate_id": None,
            "base_tax_treatment_id": str(updated_treatment_id),
            "tcs_check_required": True,
        },
    )
    wrong_kind = await client.patch(
        sku_url,
        headers={"X-Tenant-ID": str(tenant_id)},
        json={"company_hsn_sac_code_id": str(sac["classification_id"])},
    )
    cross_company = await client.patch(
        sku_url,
        headers={"X-Tenant-ID": str(tenant_id)},
        json={"company_hsn_sac_code_id": str(other_hsn["classification_id"])},
    )
    ineligible_rate = await client.patch(
        sku_url,
        headers={"X-Tenant-ID": str(tenant_id)},
        json={"selected_tax_rate_id": str(unmapped_rate_id)},
    )

    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [sku.json()["id"]]
    assert fetched.status_code == 200
    assert concealed.status_code == 404
    assert updated.status_code == 200
    assert updated.json()["name"] == "Laptop i5 Updated"
    assert updated.json()["uom"] == "UNIT"
    assert updated.json()["sku_code"] == "LAPTOP-I5"
    assert updated.json()["company_hsn_sac_code_id"] == str(
        second_hsn["classification_id"]
    )
    assert updated.json()["selected_tax_rate_id"] is None
    assert updated.json()["base_tax_treatment_id"] == str(updated_treatment_id)
    assert updated.json()["business_segment_id"] is None
    assert wrong_kind.status_code == 422
    assert cross_company.status_code == 422
    assert ineligible_rate.status_code == 422

    for field_name in (
        "sku_code",
        "product_id",
        "business_segment_id",
        "status",
    ):
        rejected = await client.patch(
            sku_url,
            headers={"X-Tenant-ID": str(tenant_id)},
            json={field_name: "not-allowed"},
        )
        assert rejected.status_code == 422

    inactivated = await client.post(
        f"{sku_url}/inactivate",
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    reactivate = await client.post(
        f"{sku_url}/activate",
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    assert inactivated.status_code == 200
    assert inactivated.json()["status"] == "INACTIVE"
    assert reactivate.status_code == 404
    assert (
        await client.patch(
            sku_url,
            headers={"X-Tenant-ID": str(tenant_id)},
            json={"name": "Forbidden"},
        )
    ).status_code == 409


async def test_goods_hierarchy_parent_inactivation_requires_inactive_children(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = await _insert_tenant(engine)
    company_id = await _insert_company(
        engine,
        tenant_id=tenant_id,
        business_nature="GOODS",
    )
    tax = await _seed_tax(
        engine,
        company_id=company_id,
        classification_type="HSN",
    )
    category = await _post(
        client,
        tenant_id=tenant_id,
        company_id=company_id,
        path="product-categories",
        payload={"name": "Devices"},
    )
    product = await _post(
        client,
        tenant_id=tenant_id,
        company_id=company_id,
        path="products",
        payload={
            "product_category_id": category.json()["id"],
            "name": "Terminal",
        },
    )
    sku = await _post(
        client,
        tenant_id=tenant_id,
        company_id=company_id,
        path="skus",
        payload={
            "product_id": product.json()["id"],
            "sku_code": "TERM-1",
            "name": "Terminal SKU",
            "uom": "EA",
            "company_hsn_sac_code_id": str(tax["classification_id"]),
            "selected_tax_rate_id": str(tax["tax_rate_id"]),
            "base_tax_treatment_id": str(tax["treatment_id"]),
        },
    )
    category_url = (
        f"/companies/{company_id}/product-categories/{category.json()['id']}"
    )
    product_url = f"/companies/{company_id}/products/{product.json()['id']}"
    sku_url = f"/companies/{company_id}/skus/{sku.json()['id']}"

    category_blocked = await client.post(
        f"{category_url}/inactivate",
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    product_blocked = await client.post(
        f"{product_url}/inactivate",
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    sku_inactivated = await client.post(
        f"{sku_url}/inactivate",
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    product_inactivated = await client.post(
        f"{product_url}/inactivate",
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    category_inactivated = await client.post(
        f"{category_url}/inactivate",
        headers={"X-Tenant-ID": str(tenant_id)},
    )

    assert category_blocked.status_code == 409
    assert product_blocked.status_code == 409
    assert sku_inactivated.status_code == 200
    assert product_inactivated.status_code == 200
    assert category_inactivated.status_code == 200
    assert product_inactivated.json()["status"] == "INACTIVE"
    assert category_inactivated.json()["status"] == "INACTIVE"

    for url in (category_url, product_url, sku_url):
        readable = await client.get(
            url,
            headers={"X-Tenant-ID": str(tenant_id)},
        )
        mutation = await client.patch(
            url,
            headers={"X-Tenant-ID": str(tenant_id)},
            json={"name": "Forbidden"},
        )
        reactivation = await client.post(
            f"{url}/activate",
            headers={"X-Tenant-ID": str(tenant_id)},
        )
        assert readable.status_code == 200
        assert readable.json()["status"] == "INACTIVE"
        assert mutation.status_code == 409
        assert reactivation.status_code == 404
