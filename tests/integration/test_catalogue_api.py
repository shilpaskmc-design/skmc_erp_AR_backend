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
            "tax_treatment_id": str(tax["treatment_id"]),
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
        "tax_treatment_id": str(tax["treatment_id"]),
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
        "tax_treatment_id": str(first_tax["treatment_id"]),
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
