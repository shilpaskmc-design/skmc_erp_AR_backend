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
        if await connection.scalar(
            text("SELECT to_regnamespace('core') IS NOT NULL")
        ):
            pytest.fail(
                "TEST_DATABASE_URL must point to a database without core schema"
            )
        version_table_exists = await connection.scalar(
            text(
                "SELECT to_regclass('public.alembic_version') IS NOT NULL"
            )
        )
        if version_table_exists:
            version_count = await connection.scalar(
                text("SELECT count(*) FROM public.alembic_version")
            )
            if version_count:
                pytest.fail(
                    "TEST_DATABASE_URL already has an applied Alembic revision"
                )


@pytest.fixture(scope="module")
def migrated_database() -> Iterator[str]:
    database_url = os.getenv("TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL API tests")
    if make_url(database_url).drivername != "postgresql+asyncpg":
        pytest.fail("TEST_DATABASE_URL must use postgresql+asyncpg")

    asyncio.run(_assert_safe_empty_database(database_url))
    previous_database_url = os.environ.get("DATABASE_URL")
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
            if previous_database_url is None:
                os.environ.pop("DATABASE_URL", None)
            else:
                os.environ["DATABASE_URL"] = previous_database_url
            get_settings.cache_clear()


@pytest.fixture
async def api_context(
    migrated_database: str,
) -> AsyncGenerator[tuple[AsyncClient, AsyncEngine, FastAPI], None]:
    from skmc_erp.database import get_db_session
    from skmc_erp.main import app

    engine = create_async_engine(migrated_database)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession)

    async def override_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    settings = Settings(
        database_url=migrated_database,
        environment="development",
    )
    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_settings] = lambda: settings
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        try:
            yield client, engine, app
        finally:
            app.dependency_overrides.clear()
            async with engine.begin() as connection:
                await connection.execute(text("TRUNCATE core.tenants CASCADE"))
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


async def _tenant_company(engine: AsyncEngine) -> tuple[UUID, UUID]:
    tenant_id = await _scalar(
        engine,
        "INSERT INTO core.tenants (name, status) "
        "VALUES (:name, 'ACTIVE') RETURNING id",
        {"name": f"G2 Tenant {uuid4()}"},
    )
    company_id = await _scalar(
        engine,
        "INSERT INTO core.companies (tenant_id, legal_name, status) "
        "VALUES (:tenant, :name, 'DRAFT') RETURNING id",
        {
            "tenant": tenant_id,
            "name": f"G2 Company {uuid4()}",
        },
    )
    return tenant_id, company_id


async def _stored_file(engine: AsyncEngine, company_id: UUID) -> UUID:
    return await _scalar(
        engine,
        """
        INSERT INTO core.stored_files (
            company_id, object_key, content_hash, content_type, size_bytes
        ) VALUES (
            :company, :object_key, :content_hash, 'image/png', 10
        ) RETURNING id
        """,
        {
            "company": company_id,
            "object_key": f"branding/{uuid4()}.png",
            "content_hash": uuid4().hex,
        },
    )


async def test_initial_company_wide_template_selection_and_scope(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id, company_id = await _tenant_company(engine)
    other_tenant_id, _ = await _tenant_company(engine)
    headers = {"X-Tenant-ID": str(tenant_id)}

    current = await client.get(
        f"/companies/{company_id}/document-templates/current",
        headers=headers,
    )
    assert current.status_code == 404
    branding = await client.get(
        f"/companies/{company_id}/document-branding/current",
        headers=headers,
    )
    assert branding.status_code == 404

    unknown = await client.put(
        f"/companies/{company_id}/document-templates/current",
        headers=headers,
        json={"template_key": "UNKNOWN_V1"},
    )
    assert unknown.status_code == 422
    per_document_type = await client.put(
        f"/companies/{company_id}/document-templates/current",
        headers=headers,
        json={"template_key": "STANDARD_V1", "document_type": "TI"},
    )
    assert per_document_type.status_code == 422

    selected = await client.put(
        f"/companies/{company_id}/document-templates/current",
        headers=headers,
        json={"template_key": "STANDARD_V1"},
    )
    assert selected.status_code == 200
    body = selected.json()
    assert body["selection"]["template_key"] == "STANDARD_V1"
    assert body["selection"]["version_no"] == 1
    assert body["selection"]["status"] == "ACTIVE"
    assert body["branding"] is None
    assert "document_type" not in body["selection"]
    assert "show_logo" not in body["selection"]

    history = await client.get(
        f"/companies/{company_id}/document-templates",
        headers=headers,
    )
    assert history.status_code == 200
    assert [row["version_no"] for row in history.json()] == [1]
    assert await _scalar(
        engine,
        "SELECT count(*) FROM ar.company_document_templates "
        "WHERE company_id = :company AND status = 'ACTIVE'",
        {"company": company_id},
    ) == 1

    concealed_headers = {"X-Tenant-ID": str(other_tenant_id)}
    concealed = await client.get(
        f"/companies/{company_id}/document-templates/current",
        headers=concealed_headers,
    )
    assert concealed.status_code == 404
    concealed_history = await client.get(
        f"/companies/{company_id}/document-templates",
        headers=concealed_headers,
    )
    assert concealed_history.status_code == 200
    assert concealed_history.json() == []
    concealed_change = await client.put(
        f"/companies/{company_id}/document-templates/current",
        headers=concealed_headers,
        json={"template_key": "MODERN_V1"},
    )
    assert concealed_change.status_code == 404
    delete_response = await client.delete(
        f"/companies/{company_id}/document-templates/current",
        headers=headers,
    )
    assert delete_response.status_code == 405


async def test_template_change_preserves_selection_history(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id, company_id = await _tenant_company(engine)
    headers = {"X-Tenant-ID": str(tenant_id)}

    first = await client.put(
        f"/companies/{company_id}/document-templates/current",
        headers=headers,
        json={"template_key": "STANDARD_V1"},
    )
    second = await client.put(
        f"/companies/{company_id}/document-templates/current",
        headers=headers,
        json={"template_key": "MODERN_V1"},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["selection"]["id"] != second.json()["selection"]["id"]

    current = await client.get(
        f"/companies/{company_id}/document-templates/current",
        headers=headers,
    )
    assert current.status_code == 200
    assert current.json()["selection"]["template_key"] == "MODERN_V1"
    assert current.json()["selection"]["version_no"] == 2

    history = await client.get(
        f"/companies/{company_id}/document-templates",
        headers=headers,
    )
    assert history.status_code == 200
    assert [row["template_key"] for row in history.json()] == [
        "STANDARD_V1",
        "MODERN_V1",
    ]
    assert [row["status"] for row in history.json()] == [
        "INACTIVE",
        "ACTIVE",
    ]
    assert await _scalar(
        engine,
        "SELECT count(*) FROM ar.company_document_templates "
        "WHERE company_id = :company AND status = 'ACTIVE'",
        {"company": company_id},
    ) == 1


async def test_branding_change_preserves_history_and_reversions_selection(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id, company_id = await _tenant_company(engine)
    _, other_company_id = await _tenant_company(engine)
    headers = {"X-Tenant-ID": str(tenant_id)}
    logo_file_id = await _stored_file(engine, company_id)
    other_file_id = await _stored_file(engine, other_company_id)

    cross_company = await client.put(
        f"/companies/{company_id}/document-branding/current",
        headers=headers,
        json={"logo_file_id": str(other_file_id)},
    )
    assert cross_company.status_code == 422
    presentation_option = await client.put(
        f"/companies/{company_id}/document-branding/current",
        headers=headers,
        json={"logo_file_id": str(logo_file_id), "show_logo": True},
    )
    assert presentation_option.status_code == 422

    first_branding = await client.put(
        f"/companies/{company_id}/document-branding/current",
        headers=headers,
        json={
            "logo_file_id": str(logo_file_id),
            "header_text": "Original header",
        },
    )
    assert first_branding.status_code == 200
    first_branding_id = first_branding.json()["id"]
    selected = await client.put(
        f"/companies/{company_id}/document-templates/current",
        headers=headers,
        json={"template_key": "COMPACT_V1"},
    )
    assert selected.status_code == 200
    assert selected.json()["selection"]["branding_id"] == first_branding_id

    second_branding = await client.put(
        f"/companies/{company_id}/document-branding/current",
        headers=headers,
        json={
            "logo_file_id": str(logo_file_id),
            "header_text": "Replacement header",
            "footer_text": "Replacement footer",
        },
    )
    assert second_branding.status_code == 200
    second_branding_id = second_branding.json()["id"]
    assert second_branding_id != first_branding_id

    current = await client.get(
        f"/companies/{company_id}/document-templates/current",
        headers=headers,
    )
    assert current.status_code == 200
    assert current.json()["selection"]["template_key"] == "COMPACT_V1"
    assert current.json()["selection"]["version_no"] == 2
    assert current.json()["selection"]["branding_id"] == second_branding_id
    assert current.json()["branding"]["id"] == second_branding_id

    branding_history = await client.get(
        f"/companies/{company_id}/document-branding",
        headers=headers,
    )
    assert branding_history.status_code == 200
    assert [row["id"] for row in branding_history.json()] == [
        first_branding_id,
        second_branding_id,
    ]
    assert [row["status"] for row in branding_history.json()] == [
        "INACTIVE",
        "ACTIVE",
    ]
    template_history = await client.get(
        f"/companies/{company_id}/document-templates",
        headers=headers,
    )
    assert [row["template_key"] for row in template_history.json()] == [
        "COMPACT_V1",
        "COMPACT_V1",
    ]
    assert [row["branding_id"] for row in template_history.json()] == [
        first_branding_id,
        second_branding_id,
    ]
    assert await _scalar(
        engine,
        "SELECT header_text FROM ar.company_document_branding WHERE id = :id",
        {"id": UUID(first_branding_id)},
    ) == "Original header"
    assert await _scalar(
        engine,
        "SELECT count(*) FROM ar.company_document_branding "
        "WHERE company_id = :company",
        {"company": company_id},
    ) == 2
    assert await _scalar(
        engine,
        "SELECT count(*) FROM ar.company_document_templates "
        "WHERE company_id = :company AND status = 'ACTIVE'",
        {"company": company_id},
    ) == 1
