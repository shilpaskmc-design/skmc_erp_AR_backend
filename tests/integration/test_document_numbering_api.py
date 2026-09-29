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


@pytest.fixture(scope="module")
def migrated_database() -> Iterator[str]:
    database_url = os.getenv("TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL API tests")
    if make_url(database_url).drivername != "postgresql+asyncpg":
        pytest.fail("TEST_DATABASE_URL must use postgresql+asyncpg")

    async def assert_empty() -> None:
        async with _connection(database_url) as connection:
            if await connection.scalar(
                text("SELECT to_regnamespace('core') IS NOT NULL")
            ):
                pytest.fail("TEST_DATABASE_URL must point to an empty database")

    asyncio.run(assert_empty())
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
            await engine.dispose()


async def _scalar(
    engine: AsyncEngine,
    sql: str,
    parameters: Mapping[str, object] | None = None,
) -> object:
    async with engine.begin() as connection:
        return await connection.scalar(text(sql), parameters or {})


async def _seed_company_and_year(
    engine: AsyncEngine,
    *,
    tenant_id: UUID | None = None,
    company_status: str = "DRAFT",
) -> tuple[UUID, UUID, UUID]:
    if tenant_id is None:
        tenant_id = await _scalar(
            engine,
            "INSERT INTO core.tenants (name, status) "
            "VALUES (:name, 'ACTIVE') RETURNING id",
            {"name": f"Tenant {uuid4()}"},
        )
    company_id = await _scalar(
        engine,
        "INSERT INTO core.companies (tenant_id, legal_name, status) "
        "VALUES (:tenant_id, :name, :status) RETURNING id",
        {
            "tenant_id": tenant_id,
            "name": f"Company {uuid4()}",
            "status": company_status,
        },
    )
    financial_year_id = await _scalar(
        engine,
        """
        INSERT INTO core.financial_years
            (company_id, start_date, end_date, display_code, status)
        VALUES
            (:company_id, '2026-04-01', '2027-03-31', 'FY26', 'OPEN')
        RETURNING id
        """,
        {"company_id": company_id},
    )
    return tenant_id, company_id, financial_year_id


async def test_document_sequence_configuration_api(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id, company_id, financial_year_id = await _seed_company_and_year(
        engine
    )
    _, other_company_id, other_financial_year_id = await _seed_company_and_year(
        engine,
        tenant_id=tenant_id,
    )
    headers = {"X-Tenant-ID": str(tenant_id)}
    payload = {
        "financial_year_id": str(financial_year_id),
        "document_type": "TI",
        "series_name": "Main",
        "format": "{PREFIX}/{FY}/{NUMBER}",
        "prefix": "INV",
        "start_number": 1,
        "next_number": 1,
        "padding": 6,
    }

    created = await client.post(
        f"/companies/{company_id}/document-sequences",
        headers=headers,
        json=payload,
    )
    duplicate = await client.post(
        f"/companies/{company_id}/document-sequences",
        headers=headers,
        json=payload,
    )
    cross_company_year = await client.post(
        f"/companies/{company_id}/document-sequences",
        headers=headers,
        json={**payload, "financial_year_id": str(other_financial_year_id)},
    )
    assert created.status_code == 201
    assert created.json()["status"] == "ACTIVE"
    assert duplicate.status_code == 409
    assert cross_company_year.status_code == 422

    sequence_id = created.json()["id"]
    listed = await client.get(
        f"/companies/{company_id}/document-sequences",
        headers=headers,
    )
    fetched = await client.get(
        f"/companies/{company_id}/document-sequences/{sequence_id}",
        headers=headers,
    )
    concealed = await client.get(
        f"/companies/{other_company_id}/document-sequences/{sequence_id}",
        headers=headers,
    )
    inactivated = await client.post(
        f"/companies/{company_id}/document-sequences/"
        f"{sequence_id}/inactivate",
        headers=headers,
    )
    assert listed.status_code == 200
    assert [row["id"] for row in listed.json()] == [sequence_id]
    assert fetched.status_code == 200
    assert concealed.status_code == 404
    assert inactivated.status_code == 200
    assert inactivated.json()["status"] == "INACTIVE"


async def test_document_sequence_rejects_inactive_company(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id, company_id, financial_year_id = await _seed_company_and_year(
        engine,
        company_status="INACTIVE",
    )
    response = await client.post(
        f"/companies/{company_id}/document-sequences",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={
            "financial_year_id": str(financial_year_id),
            "document_type": "PI",
            "series_name": "Main",
            "format": "{NUMBER}",
            "start_number": 1,
            "next_number": 1,
            "padding": 1,
        },
    )
    assert response.status_code == 409
