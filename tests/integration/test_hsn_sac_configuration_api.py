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


@pytest.fixture(scope="module")
def migrated_database() -> Iterator[str]:
    url = os.getenv("TEST_DATABASE_URL")
    if url is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL API tests")
    if make_url(url).drivername != "postgresql+asyncpg":
        pytest.fail("TEST_DATABASE_URL must use postgresql+asyncpg")
    async def safe() -> None:
        async with _connection(url) as connection:
            if await connection.scalar(text("SELECT to_regnamespace('core') IS NOT NULL")):
                pytest.fail("TEST_DATABASE_URL must point to an empty database")
            if await connection.scalar(
                text("SELECT to_regclass('public.alembic_version') IS NOT NULL")
            ):
                if await connection.scalar(
                    text("SELECT count(*) FROM public.alembic_version")
                ):
                    pytest.fail(
                        "TEST_DATABASE_URL already has an applied Alembic revision"
                    )
    asyncio.run(safe())
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    get_settings.cache_clear()
    command.upgrade(Config("alembic.ini"), "head")
    try:
        yield url
    finally:
        command.downgrade(Config("alembic.ini"), "base")
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
    factory = async_sessionmaker(engine, class_=AsyncSession)
    async def session_override() -> AsyncGenerator[AsyncSession, None]:
        async with factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
    app.dependency_overrides[get_db_session] = session_override
    app.dependency_overrides[get_settings] = lambda: Settings(database_url=migrated_database, environment="development")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        try:
            yield client, engine, app
        finally:
            app.dependency_overrides.clear()
            async with engine.begin() as connection:
                await connection.execute(text("TRUNCATE core.tenants CASCADE"))
                await connection.execute(text("TRUNCATE core.countries CASCADE"))
            await engine.dispose()


async def _scalar(engine: AsyncEngine, sql: str, params: Mapping[str, object] | None = None):
    async with engine.begin() as connection:
        return await connection.scalar(text(sql), params or {})


async def _execute(engine: AsyncEngine, sql: str, params: Mapping[str, object] | None = None) -> None:
    async with engine.begin() as connection:
        await connection.execute(text(sql), params or {})


async def _company(engine: AsyncEngine) -> tuple[UUID, UUID]:
    tenant = await _scalar(engine, "INSERT INTO core.tenants (name, status) VALUES (:name, 'ACTIVE') RETURNING id", {"name": str(uuid4())})
    company = await _scalar(engine, "INSERT INTO core.companies (tenant_id, legal_name, status) VALUES (:tenant, :name, 'DRAFT') RETURNING id", {"tenant": tenant, "name": str(uuid4())})
    return tenant, company


async def test_hsn_sac_code_lifecycle_and_isolation(api_context: tuple[AsyncClient, AsyncEngine, FastAPI]) -> None:
    client, engine, _ = api_context
    tenant, company = await _company(engine)
    other_tenant, _ = await _company(engine)
    headers = {"X-Tenant-ID": str(tenant)}
    hsn = await client.post(f"/companies/{company}/hsn-sac-codes", headers=headers, json={"classification_type": "HSN", "code": "0012", "description": "Goods"})
    sac = await client.post(f"/companies/{company}/hsn-sac-codes", headers=headers, json={"classification_type": "SAC", "code": "9983", "description": "Services"})
    assert hsn.status_code == sac.status_code == 201
    duplicate = await client.post(f"/companies/{company}/hsn-sac-codes", headers=headers, json={"classification_type": "HSN", "code": "0012", "description": "Duplicate"})
    assert duplicate.status_code == 409
    code_id = hsn.json()["id"]
    assert (await client.patch(f"/companies/{company}/hsn-sac-codes/{code_id}", headers=headers, json={"code": "99"})).status_code == 422
    updated = await client.patch(f"/companies/{company}/hsn-sac-codes/{code_id}", headers=headers, json={"description": "Updated goods"})
    assert updated.status_code == 200 and updated.json()["code"] == "0012"
    assert (await client.post(f"/companies/{company}/hsn-sac-codes/{code_id}/inactivate", headers=headers)).json()["status"] == "INACTIVE"
    assert (await client.post(f"/companies/{company}/hsn-sac-codes/{code_id}/activate", headers=headers)).status_code == 404
    assert (await client.patch(f"/companies/{company}/hsn-sac-codes/{code_id}", headers=headers, json={"description": "Forbidden"})).status_code == 409
    listed = await client.get(f"/companies/{company}/hsn-sac-codes", headers=headers)
    assert len(listed.json()) == 2
    concealed = await client.get(f"/companies/{company}/hsn-sac-codes/{code_id}", headers={"X-Tenant-ID": str(other_tenant)})
    assert concealed.status_code == 404


async def test_hsn_sac_tax_rate_history_overlap_end_and_inactive_rate(api_context: tuple[AsyncClient, AsyncEngine, FastAPI]) -> None:
    client, engine, _ = api_context
    tenant, company = await _company(engine)
    _, other_company = await _company(engine)
    headers = {"X-Tenant-ID": str(tenant)}
    await _execute(engine, "INSERT INTO core.countries (code, name, status) VALUES ('IN', 'India', 'ACTIVE')")
    tax_type = await _scalar(engine, "INSERT INTO core.tax_types (code, name, country_code, status) VALUES ('GST', 'GST', 'IN', 'ACTIVE') RETURNING id")
    rate = await _scalar(engine, "INSERT INTO core.tax_rates (tax_type_id, rate_percent, country_code, status) VALUES (:type, 18, 'IN', 'INACTIVE') RETURNING id", {"type": tax_type})
    code = await client.post(f"/companies/{company}/hsn-sac-codes", headers=headers, json={"classification_type": "HSN", "code": "8471", "description": "Computers"})
    code_id = code.json()["id"]
    path = f"/companies/{company}/hsn-sac-codes/{code_id}/tax-rates"
    assert (await client.post(path, headers=headers, json={"tax_rate_id": str(rate), "valid_from": "2026-02-01", "valid_to": "2026-01-31"})).status_code == 422
    assert (await client.post(path, headers=headers, json={"tax_rate_id": str(uuid4()), "valid_from": "2026-01-01"})).status_code == 422
    wrong_company_path = f"/companies/{other_company}/hsn-sac-codes/{code_id}/tax-rates"
    assert (await client.post(wrong_company_path, headers=headers, json={"tax_rate_id": str(rate), "valid_from": "2026-01-01"})).status_code == 404
    first = await client.post(path, headers=headers, json={"tax_rate_id": str(rate), "valid_from": "2025-01-01", "valid_to": "2025-12-31"})
    assert first.status_code == 201
    overlap = await client.post(path, headers=headers, json={"tax_rate_id": str(rate), "valid_from": "2025-12-31", "valid_to": "2026-01-31"})
    assert overlap.status_code == 409
    second = await client.post(path, headers=headers, json={"tax_rate_id": str(rate), "valid_from": "2026-01-01"})
    assert second.status_code == 201
    mapping_id = second.json()["id"]
    invalid_end = await client.post(f"{path}/{mapping_id}/end", headers=headers, json={"end_date": "2025-12-31"})
    assert invalid_end.status_code == 422
    ended = await client.post(f"{path}/{mapping_id}/end", headers=headers, json={"end_date": "2026-12-31"})
    assert ended.status_code == 200
    inactive = await client.post(f"{path}/{mapping_id}/inactivate", headers=headers)
    assert inactive.status_code == 200 and inactive.json()["status"] == "INACTIVE"
    history = await client.get(path, headers=headers)
    assert len(history.json()) == 2
    assert await _scalar(engine, "SELECT count(*) FROM core.company_hsn_sac_tax_rates WHERE company_hsn_sac_code_id = :id", {"id": UUID(code_id)}) == 2
