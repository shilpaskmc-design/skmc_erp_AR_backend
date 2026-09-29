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
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from skmc_erp.config import Settings, get_settings


@asynccontextmanager
async def _connection(url: str) -> AsyncIterator[AsyncConnection]:
    engine = create_async_engine(url)
    try:
        async with engine.connect() as connection:
            yield connection
    finally:
        await engine.dispose()


async def _assert_safe_empty(url: str) -> None:
    async with _connection(url) as connection:
        if await connection.scalar(text("SELECT to_regnamespace('core') IS NOT NULL")):
            pytest.fail("TEST_DATABASE_URL must point to a database without core schema")
        if await connection.scalar(text("SELECT to_regclass('public.alembic_version') IS NOT NULL")):
            if await connection.scalar(text("SELECT count(*) FROM public.alembic_version")):
                pytest.fail("TEST_DATABASE_URL already has an applied Alembic revision")


@pytest.fixture(scope="module")
def migrated_database() -> Iterator[str]:
    url = os.getenv("TEST_DATABASE_URL")
    if url is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL API tests")
    if make_url(url).drivername != "postgresql+asyncpg":
        pytest.fail("TEST_DATABASE_URL must use postgresql+asyncpg")
    asyncio.run(_assert_safe_empty(url))
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    get_settings.cache_clear()
    command.upgrade(Config("alembic.ini"), "head")
    try:
        yield url
    finally:
        try:
            command.downgrade(Config("alembic.ini"), "base")
        finally:
            if previous is None:
                os.environ.pop("DATABASE_URL", None)
            else:
                os.environ["DATABASE_URL"] = previous
            get_settings.cache_clear()


@pytest.fixture
async def api_context(migrated_database: str) -> AsyncGenerator[tuple[AsyncClient, AsyncEngine, FastAPI], None]:
    from skmc_erp.database import get_db_session
    from skmc_erp.main import app

    engine = create_async_engine(migrated_database)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession)

    async def override_session() -> AsyncGenerator[AsyncSession, None]:
        async with factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    settings = Settings(database_url=migrated_database, environment="development")
    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_settings] = lambda: settings
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        try:
            yield client, engine, app
        finally:
            app.dependency_overrides.clear()
            async with engine.begin() as connection:
                await connection.execute(text("TRUNCATE core.tenants CASCADE"))
            await engine.dispose()


async def _execute(engine: AsyncEngine, sql: str, params: Mapping[str, object] | None = None) -> None:
    async with engine.begin() as connection:
        await connection.execute(text(sql), params or {})


async def _scalar(engine: AsyncEngine, sql: str, params: Mapping[str, object] | None = None):
    async with engine.begin() as connection:
        return await connection.scalar(text(sql), params or {})


async def _tenant_company(engine: AsyncEngine) -> tuple[UUID, UUID]:
    tenant = await _scalar(engine, "INSERT INTO core.tenants (name, status) VALUES (:name, 'ACTIVE') RETURNING id", {"name": f"Tenant {uuid4()}"})
    company = await _scalar(engine, "INSERT INTO core.companies (tenant_id, legal_name, status) VALUES (:tenant, :name, 'DRAFT') RETURNING id", {"tenant": tenant, "name": f"Company {uuid4()}"})
    return tenant, company


async def test_document_template_list_preserves_versions_and_tenant_scope(api_context: tuple[AsyncClient, AsyncEngine, FastAPI]) -> None:
    client, engine, _ = api_context
    tenant, company = await _tenant_company(engine)
    other_tenant, _ = await _tenant_company(engine)
    branding = await _scalar(engine, "INSERT INTO ar.company_document_branding (company_id, status) VALUES (:company, 'ACTIVE') RETURNING id", {"company": company})
    for version, status_value in ((1, "INACTIVE"), (2, "ACTIVE")):
        await _execute(engine, "INSERT INTO ar.company_document_templates (company_id, branding_id, template_key, version_no, status) VALUES (:company, :branding, 'STANDARD_V1', :version, :status)", {"company": company, "branding": branding, "version": version, "status": status_value})
    response = await client.get(f"/companies/{company}/document-templates", headers={"X-Tenant-ID": str(tenant)})
    assert response.status_code == 200
    assert [item["version_no"] for item in response.json()] == [1, 2]
    assert "document_type" not in response.json()[0]
    assert "show_logo" not in response.json()[0]
    concealed = await client.get(f"/companies/{company}/document-templates", headers={"X-Tenant-ID": str(other_tenant)})
    assert concealed.status_code == 200
    assert concealed.json() == []


async def test_invoice_delivery_settings_upsert_validation_and_provider_scope(api_context: tuple[AsyncClient, AsyncEngine, FastAPI]) -> None:
    client, engine, _ = api_context
    tenant, company = await _tenant_company(engine)
    other_tenant, other_company = await _tenant_company(engine)
    provider = await _scalar(engine, "INSERT INTO core.email_provider_configs (tenant_id, company_id, provider_type, sender_identity, secret_reference, status) VALUES (:tenant, :company, 'SMTP', 'sender@example.com', 'secret/do-not-return', 'ACTIVE') RETURNING id", {"tenant": tenant, "company": company})
    other_provider = await _scalar(engine, "INSERT INTO core.email_provider_configs (tenant_id, company_id, provider_type, sender_identity, secret_reference, status) VALUES (:tenant, :company, 'SMTP', 'other@example.com', 'secret/other', 'ACTIVE') RETURNING id", {"tenant": other_tenant, "company": other_company})
    payload = {"automatic_sending_enabled": True, "email_provider_config_id": str(provider), "sender_email": "billing@example.com", "reply_to_email": "reply@example.com", "default_email_template_key": "INVOICE", "default_cc": ["finance@example.com"]}
    response = await client.put(f"/companies/{company}/invoice-delivery-settings", headers={"X-Tenant-ID": str(tenant)}, json=payload)
    assert response.status_code == 200
    assert response.json()["automatic_sending_enabled"] is True
    assert "secret_reference" not in response.json()
    second = await client.put(f"/companies/{company}/invoice-delivery-settings", headers={"X-Tenant-ID": str(tenant)}, json={**payload, "automatic_sending_enabled": False})
    assert second.status_code == 200
    assert await _scalar(engine, "SELECT count(*) FROM ar.company_invoice_delivery_settings WHERE company_id = :company", {"company": company}) == 1
    invalid_email = await client.put(f"/companies/{company}/invoice-delivery-settings", headers={"X-Tenant-ID": str(tenant)}, json={**payload, "sender_email": "not-an-email"})
    assert invalid_email.status_code == 422
    invalid_provider = await client.put(f"/companies/{company}/invoice-delivery-settings", headers={"X-Tenant-ID": str(tenant)}, json={**payload, "email_provider_config_id": str(other_provider)})
    assert invalid_provider.status_code == 422


async def test_exchange_rates_and_fx_policies(api_context: tuple[AsyncClient, AsyncEngine, FastAPI]) -> None:
    client, engine, _ = api_context
    tenant, company = await _tenant_company(engine)
    for code in ("USD", "INR"):
        await _execute(engine, "INSERT INTO core.currencies (code, name, minor_units, status) VALUES (:code, :code, 2, 'ACTIVE')", {"code": code})
    payload = {"from_currency_code": "USD", "to_currency_code": "INR", "rate": "83.25", "rate_type": "CORPORATE", "effective_from": "2026-01-01", "effective_to": "2026-06-30", "source": "MANUAL"}
    created = await client.post(f"/companies/{company}/exchange-rates", headers={"X-Tenant-ID": str(tenant)}, json=payload)
    assert created.status_code == 201
    overlap = await client.post(f"/companies/{company}/exchange-rates", headers={"X-Tenant-ID": str(tenant)}, json={**payload, "effective_from": "2026-06-30", "effective_to": "2026-12-31"})
    assert overlap.status_code == 409
    historical = await client.post(f"/companies/{company}/exchange-rates", headers={"X-Tenant-ID": str(tenant)}, json={**payload, "effective_from": "2025-01-01", "effective_to": "2025-12-31"})
    assert historical.status_code == 201
    invalid_pair = await client.post(f"/companies/{company}/exchange-rates", headers={"X-Tenant-ID": str(tenant)}, json={**payload, "to_currency_code": "USD"})
    assert invalid_pair.status_code == 422
    listed = await client.get(f"/companies/{company}/exchange-rates", headers={"X-Tenant-ID": str(tenant)})
    assert listed.status_code == 200 and len(listed.json()) == 2
    policy = await client.put(f"/companies/{company}/fx-policies/BILLING", headers={"X-Tenant-ID": str(tenant)}, json={"default_rate_type": "SPOT", "allow_user_fixed_override": True, "reason_required_for_override": True, "status": "ACTIVE"})
    assert policy.status_code == 200
    invalid_policy = await client.put(f"/companies/{company}/fx-policies/RECEIPT", headers={"X-Tenant-ID": str(tenant)}, json={"default_rate_type": "CORPORATE", "allow_user_fixed_override": False, "reason_required_for_override": True})
    assert invalid_policy.status_code == 422


async def test_reminder_policy_and_ordered_schedule_rules(api_context: tuple[AsyncClient, AsyncEngine, FastAPI]) -> None:
    client, engine, _ = api_context
    tenant, company = await _tenant_company(engine)
    policy = await client.put(f"/companies/{company}/reminders/policy", headers={"X-Tenant-ID": str(tenant)}, json={"enabled": True, "send_time": "09:30:00", "default_template_key": "REMINDER"})
    assert policy.status_code == 200
    for offset in (3, -3, 0):
        response = await client.post(f"/companies/{company}/reminders/schedule-rules", headers={"X-Tenant-ID": str(tenant)}, json={"offset_days": offset})
        assert response.status_code == 201
    duplicate = await client.post(f"/companies/{company}/reminders/schedule-rules", headers={"X-Tenant-ID": str(tenant)}, json={"offset_days": 0})
    assert duplicate.status_code == 409
    listed = await client.get(f"/companies/{company}/reminders/schedule-rules", headers={"X-Tenant-ID": str(tenant)})
    assert [item["offset_days"] for item in listed.json()] == [-3, 0, 3]
    rule_id = listed.json()[0]["id"]
    inactive = await client.post(f"/companies/{company}/reminders/schedule-rules/{rule_id}/inactivate", headers={"X-Tenant-ID": str(tenant)})
    assert inactive.status_code == 200
    assert inactive.json()["status"] == "INACTIVE"
    assert await _scalar(engine, "SELECT count(*) FROM ar.reminder_schedule_rules WHERE id = :id", {"id": UUID(rule_id)}) == 1
