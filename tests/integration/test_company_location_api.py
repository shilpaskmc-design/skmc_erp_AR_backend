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
from skmc_erp.core.company_location import service as company_location_service


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
            pytest.fail("TEST_DATABASE_URL must point to a database without core schema")

        version_table_exists = await connection.scalar(
            text("SELECT to_regclass('public.alembic_version') IS NOT NULL")
        )
        if version_table_exists:
            version_count = await connection.scalar(
                text("SELECT count(*) FROM public.alembic_version")
            )
            if version_count:
                pytest.fail("TEST_DATABASE_URL already has an applied Alembic revision")


async def _assert_all_migrations_removed(database_url: str) -> None:
    async with _connection(database_url) as connection:
        assert not await connection.scalar(
            text("SELECT to_regnamespace('core') IS NOT NULL")
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
    alembic_config = Config("alembic.ini")
    command.upgrade(alembic_config, "head")

    try:
        yield database_url
    finally:
        try:
            command.downgrade(alembic_config, "base")
            asyncio.run(_assert_all_migrations_removed(database_url))
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

    test_engine = create_async_engine(migrated_database)
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
    )

    async def override_db_session() -> AsyncGenerator[AsyncSession, None]:
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
    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_settings] = lambda: settings

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        try:
            yield client, test_engine, app
        finally:
            app.dependency_overrides.clear()
            async with test_engine.begin() as connection:
                await connection.execute(
                    text(
                        """
                        TRUNCATE TABLE
                            core.company_locations,
                            core.companies,
                            core.organisations,
                            core.country_subdivisions,
                            core.entity_types,
                            core.currencies,
                            core.countries,
                            core.tenants
                        CASCADE
                        """
                    )
                )
            await test_engine.dispose()


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
    async with engine.connect() as connection:
        return await connection.scalar(text(sql), parameters or {})


async def _insert_tenant(
    engine: AsyncEngine,
    tenant_id: UUID,
) -> None:
    await _execute(
        engine,
        """
        INSERT INTO core.tenants (id, name, status)
        VALUES (:id, :name, 'ACTIVE')
        """,
        {"id": tenant_id, "name": f"Tenant {tenant_id}"},
    )


async def _insert_company(
    engine: AsyncEngine,
    *,
    company_id: UUID,
    tenant_id: UUID,
    status: str = "DRAFT",
) -> None:
    await _execute(
        engine,
        """
        INSERT INTO core.companies (id, tenant_id, legal_name, status)
        VALUES (:id, :tenant_id, :name, :status)
        """,
        {
            "id": company_id,
            "tenant_id": tenant_id,
            "name": f"Company {company_id}",
            "status": status,
        },
    )


async def _insert_country(
    engine: AsyncEngine,
    *,
    code: str,
    status: str = "ACTIVE",
) -> None:
    await _execute(
        engine,
        """
        INSERT INTO core.countries (code, name, status)
        VALUES (:code, :name, :status)
        """,
        {"code": code, "name": f"Country {code}", "status": status},
    )


async def _insert_subdivision(
    engine: AsyncEngine,
    *,
    country_code: str,
    code: str,
    status: str = "ACTIVE",
) -> None:
    await _execute(
        engine,
        """
        INSERT INTO core.country_subdivisions
            (country_code, code, name, subdivision_type, status)
        VALUES
            (:country_code, :code, :name, 'STATE', :status)
        """,
        {
            "country_code": country_code,
            "code": code,
            "name": f"Subdivision {code}",
            "status": status,
        },
    )


async def _insert_gst_registration(
    engine: AsyncEngine,
    *,
    registration_id: UUID,
    company_id: UUID,
    gstin: str,
    subdivision_code: str,
    status: str = "DRAFT",
) -> None:
    await _execute(
        engine,
        """
        INSERT INTO core.company_gst_registrations
            (id, company_id, gstin, subdivision_code, status)
        VALUES
            (:id, :company_id, :gstin, :subdivision_code, :status)
        """,
        {
            "id": registration_id,
            "company_id": company_id,
            "gstin": gstin,
            "subdivision_code": subdivision_code,
            "status": status,
        },
    )


def _location_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "location_name": "Noida Branch",
        "address_line_1": "Sector 62",
        "city": "Noida",
        "country_code": "IN",
        "is_branch": True,
    }
    payload.update(overrides)
    return payload


async def test_minimal_location_creation_and_multiple_purposes(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = uuid4()
    company_id = uuid4()
    await _insert_tenant(engine, tenant_id)
    await _insert_company(engine, company_id=company_id, tenant_id=tenant_id)
    await _insert_country(engine, code="IN")

    minimal = await client.post(
        f"/companies/{company_id}/locations",
        headers={"X-Tenant-ID": str(tenant_id)},
        json=_location_payload(),
    )
    multipurpose = await client.post(
        f"/companies/{company_id}/locations",
        headers={"X-Tenant-ID": str(tenant_id)},
        json=_location_payload(
            location_name="Corporate Billing Office",
            is_branch=False,
            is_corporate_office=True,
            is_billing_office=True,
        ),
    )

    assert minimal.status_code == 201
    assert UUID(minimal.json()["id"])
    assert minimal.json()["company_id"] == str(company_id)
    assert minimal.json()["status"] == "ACTIVE"
    assert minimal.json()["subdivision_code"] is None
    assert multipurpose.status_code == 201
    assert multipurpose.json()["is_corporate_office"] is True
    assert multipurpose.json()["is_billing_office"] is True
    assert await _scalar(
        engine,
        "SELECT count(*) FROM core.company_locations",
    ) == 2
    assert await _scalar(
        engine,
        "SELECT count(*) FROM core.company_location_versions",
    ) == 2


async def test_company_lookup_is_tenant_safe_and_rejects_inactive_company(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = uuid4()
    other_tenant_id = uuid4()
    other_company_id = uuid4()
    inactive_company_id = uuid4()
    await _insert_tenant(engine, tenant_id)
    await _insert_tenant(engine, other_tenant_id)
    await _insert_company(
        engine,
        company_id=other_company_id,
        tenant_id=other_tenant_id,
    )
    await _insert_company(
        engine,
        company_id=inactive_company_id,
        tenant_id=tenant_id,
        status="INACTIVE",
    )
    await _insert_country(engine, code="IN")

    for company_id in (uuid4(), other_company_id):
        response = await client.post(
            f"/companies/{company_id}/locations",
            headers={"X-Tenant-ID": str(tenant_id)},
            json=_location_payload(),
        )
        assert response.status_code == 404
        assert response.json() == {"detail": "Company not found"}

    inactive = await client.post(
        f"/companies/{inactive_company_id}/locations",
        headers={"X-Tenant-ID": str(tenant_id)},
        json=_location_payload(),
    )
    assert inactive.status_code == 409
    assert await _scalar(
        engine,
        "SELECT count(*) FROM core.company_locations",
    ) == 0


async def test_country_and_subdivision_validation(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = uuid4()
    company_id = uuid4()
    await _insert_tenant(engine, tenant_id)
    await _insert_company(engine, company_id=company_id, tenant_id=tenant_id)
    await _insert_country(engine, code="IN")
    await _insert_country(engine, code="US")
    await _insert_country(engine, code="CA", status="INACTIVE")
    await _insert_subdivision(
        engine,
        country_code="IN",
        code="IN-UP",
    )
    await _insert_subdivision(
        engine,
        country_code="US",
        code="US-CA",
    )
    await _insert_subdivision(
        engine,
        country_code="IN",
        code="IN-DL",
        status="INACTIVE",
    )

    cases = [
        (_location_payload(country_code="ZZ"), 422),
        (_location_payload(country_code="CA"), 409),
        (_location_payload(subdivision_code="IN-MH"), 422),
        (_location_payload(subdivision_code="IN-DL"), 409),
        (_location_payload(subdivision_code="US-CA"), 422),
    ]
    for payload, expected_status in cases:
        response = await client.post(
            f"/companies/{company_id}/locations",
            headers={"X-Tenant-ID": str(tenant_id)},
            json=payload,
        )
        assert response.status_code == expected_status

    valid = await client.post(
        f"/companies/{company_id}/locations",
        headers={"X-Tenant-ID": str(tenant_id)},
        json=_location_payload(subdivision_code="IN-UP"),
    )
    assert valid.status_code == 201
    assert valid.json()["subdivision_code"] == "IN-UP"
    assert await _scalar(
        engine,
        "SELECT count(*) FROM core.company_locations",
    ) == 1


async def test_registered_office_uniqueness_and_repeatable_other_purposes(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = uuid4()
    first_company_id = uuid4()
    second_company_id = uuid4()
    await _insert_tenant(engine, tenant_id)
    await _insert_company(
        engine,
        company_id=first_company_id,
        tenant_id=tenant_id,
    )
    await _insert_company(
        engine,
        company_id=second_company_id,
        tenant_id=tenant_id,
    )
    await _insert_country(engine, code="IN")

    first_registered = await client.post(
        f"/companies/{first_company_id}/locations",
        headers={"X-Tenant-ID": str(tenant_id)},
        json=_location_payload(
            location_name="Registered Corporate",
            is_branch=False,
            is_registered_office=True,
            is_corporate_office=True,
        ),
    )
    second_registered = await client.post(
        f"/companies/{first_company_id}/locations",
        headers={"X-Tenant-ID": str(tenant_id)},
        json=_location_payload(
            location_name="Second Registered",
            is_branch=False,
            is_registered_office=True,
        ),
    )
    other_company_registered = await client.post(
        f"/companies/{second_company_id}/locations",
        headers={"X-Tenant-ID": str(tenant_id)},
        json=_location_payload(
            location_name="Other Company Registered",
            is_branch=False,
            is_registered_office=True,
        ),
    )

    assert first_registered.status_code == 201
    assert second_registered.status_code == 409
    assert other_company_registered.status_code == 201

    for purpose in ("is_branch", "is_warehouse"):
        for index in range(2):
            purpose_flags = {"is_branch": False, purpose: True}
            response = await client.post(
                f"/companies/{first_company_id}/locations",
                headers={"X-Tenant-ID": str(tenant_id)},
                json=_location_payload(
                    location_name=f"{purpose} {index}",
                    **purpose_flags,
                ),
            )
            assert response.status_code == 201

    assert await _scalar(
        engine,
        "SELECT count(*) FROM core.company_locations",
    ) == 6
    assert await _scalar(
        engine,
        "SELECT count(*) FROM core.company_location_versions",
    ) == 6


async def test_location_reads_are_company_and_tenant_scoped(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = uuid4()
    other_tenant_id = uuid4()
    company_id = uuid4()
    sibling_company_id = uuid4()
    other_company_id = uuid4()
    await _insert_tenant(engine, tenant_id)
    await _insert_tenant(engine, other_tenant_id)
    await _insert_company(engine, company_id=company_id, tenant_id=tenant_id)
    await _insert_company(
        engine,
        company_id=sibling_company_id,
        tenant_id=tenant_id,
    )
    await _insert_company(
        engine,
        company_id=other_company_id,
        tenant_id=other_tenant_id,
    )
    await _insert_country(engine, code="IN")

    own = await client.post(
        f"/companies/{company_id}/locations",
        headers={"X-Tenant-ID": str(tenant_id)},
        json=_location_payload(location_name="Own Location"),
    )
    sibling = await client.post(
        f"/companies/{sibling_company_id}/locations",
        headers={"X-Tenant-ID": str(tenant_id)},
        json=_location_payload(location_name="Sibling Location"),
    )
    other = await client.post(
        f"/companies/{other_company_id}/locations",
        headers={"X-Tenant-ID": str(other_tenant_id)},
        json=_location_payload(location_name="Other Tenant Location"),
    )
    assert own.status_code == sibling.status_code == other.status_code == 201

    listed = await client.get(
        f"/companies/{company_id}/locations",
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    fetched = await client.get(
        f"/companies/{company_id}/locations/{own.json()['id']}",
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    wrong_company = await client.get(
        f"/companies/{company_id}/locations/{sibling.json()['id']}",
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    wrong_tenant = await client.get(
        f"/companies/{other_company_id}/locations/{other.json()['id']}",
        headers={"X-Tenant-ID": str(tenant_id)},
    )

    assert listed.status_code == 200
    assert [location["id"] for location in listed.json()] == [own.json()["id"]]
    assert fetched.status_code == 200
    assert fetched.json()["location_name"] == "Own Location"
    assert wrong_company.status_code == 404
    assert wrong_tenant.status_code == 404


async def test_location_update_preserves_purpose_and_registered_office_rules(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, engine, _ = api_context
    tenant_id = uuid4()
    company_id = uuid4()
    await _insert_tenant(engine, tenant_id)
    await _insert_company(engine, company_id=company_id, tenant_id=tenant_id)
    await _insert_country(engine, code="IN")
    business_dates = iter(
        (date(2026, 4, 10), date(2026, 4, 10), date(2026, 9, 20))
    )
    monkeypatch.setattr(
        company_location_service,
        "_business_date",
        lambda: next(business_dates),
    )

    registered = await client.post(
        f"/companies/{company_id}/locations",
        headers={"X-Tenant-ID": str(tenant_id)},
        json=_location_payload(
            location_name="Registered Office",
            is_branch=False,
            is_registered_office=True,
        ),
    )
    branch = await client.post(
        f"/companies/{company_id}/locations",
        headers={"X-Tenant-ID": str(tenant_id)},
        json=_location_payload(location_name="Branch Office"),
    )
    assert registered.status_code == branch.status_code == 201

    updated = await client.patch(
        f"/companies/{company_id}/locations/{branch.json()['id']}",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={
            "location_name": "  Updated Branch  ",
            "address_line_1": "  Sector 63  ",
            "address_line_2": "  Tower A  ",
            "city": "Ghaziabad",
            "district": "Ghaziabad",
            "postal_code": "201001",
            "is_warehouse": True,
        },
    )
    no_purpose = await client.patch(
        f"/companies/{company_id}/locations/{branch.json()['id']}",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={
            "is_registered_office": False,
            "is_corporate_office": False,
            "is_branch": False,
            "is_billing_office": False,
            "is_warehouse": False,
            "other_purpose": None,
        },
    )
    duplicate_registered = await client.patch(
        f"/companies/{company_id}/locations/{branch.json()['id']}",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={"is_registered_office": True},
    )

    assert updated.status_code == 200
    assert updated.json()["location_name"] == "Updated Branch"
    assert updated.json()["address_line_1"] == "Sector 63"
    assert updated.json()["is_warehouse"] is True
    assert no_purpose.status_code == 422
    assert duplicate_registered.status_code == 409
    assert duplicate_registered.json() == {
        "detail": "Company already has an active Registered Office"
    }
    assert await _scalar(
        engine,
        """
        SELECT count(*)
        FROM core.company_locations
        WHERE company_id = :company_id
          AND status = 'ACTIVE'
          AND is_registered_office
        """,
        {"company_id": company_id},
    ) == 1
    assert await _scalar(
        engine,
        """
        SELECT is_registered_office
        FROM core.company_locations
        WHERE id = :location_id
        """,
        {"location_id": branch.json()["id"]},
    ) is False


async def test_location_gst_assignment_is_nullable_and_scope_safe(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = uuid4()
    company_id = uuid4()
    other_company_id = uuid4()
    await _insert_tenant(engine, tenant_id)
    await _insert_company(engine, company_id=company_id, tenant_id=tenant_id)
    await _insert_company(
        engine,
        company_id=other_company_id,
        tenant_id=tenant_id,
    )
    await _insert_country(engine, code="IN")
    await _insert_subdivision(engine, country_code="IN", code="IN-UP")
    await _insert_subdivision(engine, country_code="IN", code="IN-DL")

    matching_id = uuid4()
    mismatched_id = uuid4()
    other_company_registration_id = uuid4()
    await _insert_gst_registration(
        engine,
        registration_id=matching_id,
        company_id=company_id,
        gstin="09ABCDE1234F1Z5",
        subdivision_code="IN-UP",
    )
    await _insert_gst_registration(
        engine,
        registration_id=mismatched_id,
        company_id=company_id,
        gstin="07ABCDE1234F1Z5",
        subdivision_code="IN-DL",
    )
    await _insert_gst_registration(
        engine,
        registration_id=other_company_registration_id,
        company_id=other_company_id,
        gstin="09ABCDE1234F1Z6",
        subdivision_code="IN-UP",
    )
    created = await client.post(
        f"/companies/{company_id}/locations",
        headers={"X-Tenant-ID": str(tenant_id)},
        json=_location_payload(subdivision_code="IN-UP"),
    )
    assert created.status_code == 201
    location_url = f"/companies/{company_id}/locations/{created.json()['id']}"

    assigned = await client.patch(
        location_url,
        headers={"X-Tenant-ID": str(tenant_id)},
        json={"gst_registration_id": str(matching_id)},
    )
    mismatched = await client.patch(
        location_url,
        headers={"X-Tenant-ID": str(tenant_id)},
        json={"gst_registration_id": str(mismatched_id)},
    )
    cross_company = await client.patch(
        location_url,
        headers={"X-Tenant-ID": str(tenant_id)},
        json={"gst_registration_id": str(other_company_registration_id)},
    )
    unassigned = await client.patch(
        location_url,
        headers={"X-Tenant-ID": str(tenant_id)},
        json={"gst_registration_id": None},
    )

    assert assigned.status_code == 200
    assert assigned.json()["gst_registration_id"] == str(matching_id)
    assert mismatched.status_code == 422
    assert cross_company.status_code == 422
    assert unassigned.status_code == 200
    assert unassigned.json()["gst_registration_id"] is None


async def test_inactive_gst_rejects_new_location_assignment_but_keeps_existing(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = uuid4()
    company_id = uuid4()
    await _insert_tenant(engine, tenant_id)
    await _insert_company(engine, company_id=company_id, tenant_id=tenant_id)
    await _insert_country(engine, code="IN")
    await _insert_subdivision(engine, country_code="IN", code="IN-UP")
    registration_id = uuid4()
    await _insert_gst_registration(
        engine,
        registration_id=registration_id,
        company_id=company_id,
        gstin="09ABCDE1234F1Z5",
        subdivision_code="IN-UP",
    )
    headers = {"X-Tenant-ID": str(tenant_id)}
    first = await client.post(
        f"/companies/{company_id}/locations",
        headers=headers,
        json=_location_payload(subdivision_code="IN-UP"),
    )
    second = await client.post(
        f"/companies/{company_id}/locations",
        headers=headers,
        json=_location_payload(
            location_name="Second Branch",
            subdivision_code="IN-UP",
        ),
    )
    third = await client.post(
        f"/companies/{company_id}/locations",
        headers=headers,
        json=_location_payload(
            location_name="Third Branch",
            subdivision_code="IN-UP",
        ),
    )
    first_url = f"/companies/{company_id}/locations/{first.json()['id']}"
    second_url = f"/companies/{company_id}/locations/{second.json()['id']}"
    third_url = f"/companies/{company_id}/locations/{third.json()['id']}"
    assigned = await client.patch(
        first_url,
        headers=headers,
        json={"gst_registration_id": str(registration_id)},
    )
    assert assigned.status_code == 200
    await _execute(
        engine,
        "UPDATE core.company_gst_registrations SET status = 'ACTIVE' WHERE id = :id",
        {"id": registration_id},
    )
    active_assignment = await client.patch(
        second_url,
        headers=headers,
        json={"gst_registration_id": str(registration_id)},
    )
    assert active_assignment.status_code == 200
    await _execute(
        engine,
        "UPDATE core.company_gst_registrations SET status = 'INACTIVE' WHERE id = :id",
        {"id": registration_id},
    )

    existing = await client.patch(
        first_url,
        headers=headers,
        json={"gst_registration_id": str(registration_id)},
    )
    new_assignment = await client.patch(
        third_url,
        headers=headers,
        json={"gst_registration_id": str(registration_id)},
    )

    assert existing.status_code == 200
    assert existing.json()["gst_registration_id"] == str(registration_id)
    assert new_assignment.status_code == 409
    assert "Inactive GST Registration" in new_assignment.json()["detail"]


async def test_location_inactivation_is_supported_without_delete_or_reactivate(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = uuid4()
    company_id = uuid4()
    await _insert_tenant(engine, tenant_id)
    await _insert_company(engine, company_id=company_id, tenant_id=tenant_id)
    await _insert_country(engine, code="IN")
    created = await client.post(
        f"/companies/{company_id}/locations",
        headers={"X-Tenant-ID": str(tenant_id)},
        json=_location_payload(),
    )
    assert created.status_code == 201
    location_url = f"/companies/{company_id}/locations/{created.json()['id']}"

    inactivated = await client.post(
        f"{location_url}/inactivate",
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    deleted = await client.delete(
        location_url,
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    reactivate = await client.post(
        f"{location_url}/activate",
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    address_update = await client.patch(
        location_url,
        headers={"X-Tenant-ID": str(tenant_id)},
        json={"address_line_1": "New address"},
    )
    gst_update = await client.patch(
        location_url,
        headers={"X-Tenant-ID": str(tenant_id)},
        json={"gst_registration_id": None},
    )
    cost_center_update = await client.put(
        f"{location_url}/location-cost-center",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={"cost_center_location_id": None},
    )
    history = await client.get(
        f"{location_url}/address-history",
        headers={"X-Tenant-ID": str(tenant_id)},
    )

    assert inactivated.status_code == 200
    assert inactivated.json()["status"] == "INACTIVE"
    assert deleted.status_code == 405
    assert reactivate.status_code == 404
    assert address_update.status_code == 409
    assert gst_update.status_code == 409
    assert cost_center_update.status_code == 409
    assert history.status_code == 200
    assert len(history.json()) == 1


async def test_location_cost_center_assignment_current_state_and_scope(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = uuid4()
    company_id = uuid4()
    other_company_id = uuid4()
    await _insert_tenant(engine, tenant_id)
    await _insert_company(engine, company_id=company_id, tenant_id=tenant_id)
    await _insert_company(
        engine,
        company_id=other_company_id,
        tenant_id=tenant_id,
    )
    await _insert_country(engine, code="IN")
    created = await client.post(
        f"/companies/{company_id}/locations",
        headers={"X-Tenant-ID": str(tenant_id)},
        json=_location_payload(),
    )
    assert created.status_code == 201
    assert created.json()["cost_center_location_id"] is None

    cost_centers = []
    for name, owner_id in (
        ("Noida Operations", company_id),
        ("North Operations", company_id),
        ("Other Company Operations", other_company_id),
    ):
        response = await client.post(
            f"/companies/{owner_id}/location-cost-centers",
            headers={"X-Tenant-ID": str(tenant_id)},
            json={"name": name},
        )
        assert response.status_code == 201
        cost_centers.append(response.json()["id"])

    assignment_url = (
        f"/companies/{company_id}/locations/{created.json()['id']}/"
        "location-cost-center"
    )
    for target_id in (cost_centers[0], cost_centers[1], None):
        assigned = await client.put(
            assignment_url,
            headers={"X-Tenant-ID": str(tenant_id)},
            json={"cost_center_location_id": target_id},
        )
        read_back = await client.get(
            f"/companies/{company_id}/locations/{created.json()['id']}",
            headers={"X-Tenant-ID": str(tenant_id)},
        )
        assert assigned.status_code == 200
        assert assigned.json()["cost_center_location_id"] == target_id
        assert read_back.status_code == 200
        assert read_back.json()["cost_center_location_id"] == target_id

    cross_company = await client.put(
        assignment_url,
        headers={"X-Tenant-ID": str(tenant_id)},
        json={"cost_center_location_id": cost_centers[2]},
    )
    assert cross_company.status_code == 422

    await _execute(
        engine,
        "UPDATE core.cost_center_locations SET status = 'INACTIVE' "
        "WHERE id = :id",
        {"id": cost_centers[0]},
    )
    inactive_target = await client.put(
        assignment_url,
        headers={"X-Tenant-ID": str(tenant_id)},
        json={"cost_center_location_id": cost_centers[0]},
    )
    assert inactive_target.status_code == 409


async def test_location_address_history_is_versioned_without_noop_duplicates(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, engine, _ = api_context
    tenant_id = uuid4()
    company_id = uuid4()
    await _insert_tenant(engine, tenant_id)
    await _insert_company(engine, company_id=company_id, tenant_id=tenant_id)
    await _insert_country(engine, code="IN")
    await _insert_subdivision(engine, country_code="IN", code="IN-UP")

    business_dates = iter(
        (date(2026, 4, 10), date(2026, 9, 20), date(2026, 10, 5))
    )
    monkeypatch.setattr(
        company_location_service,
        "_business_date",
        lambda: next(business_dates),
    )
    created = await client.post(
        f"/companies/{company_id}/locations",
        headers={"X-Tenant-ID": str(tenant_id)},
        json=_location_payload(subdivision_code="IN-UP"),
    )
    assert created.status_code == 201
    location_url = f"/companies/{company_id}/locations/{created.json()['id']}"
    history_url = f"{location_url}/address-history"

    initial_history = await client.get(
        history_url,
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    first_change = await client.patch(
        location_url,
        headers={"X-Tenant-ID": str(tenant_id)},
        json={
            "address_line_1": "Sector 63",
            "address_line_2": "Tower A",
            "city": "Ghaziabad",
            "district": "Ghaziabad",
            "postal_code": "201001",
        },
    )
    no_op = await client.patch(
        location_url,
        headers={"X-Tenant-ID": str(tenant_id)},
        json={"address_line_1": "Sector 63"},
    )
    non_address = await client.patch(
        location_url,
        headers={"X-Tenant-ID": str(tenant_id)},
        json={"location_name": "Updated Noida Branch"},
    )
    second_change = await client.patch(
        location_url,
        headers={"X-Tenant-ID": str(tenant_id)},
        json={"address_line_1": "Sector 64"},
    )
    final_history = await client.get(
        history_url,
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    first_as_of = await client.get(
        f"{history_url}?as_of=2026-09-19",
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    second_as_of = await client.get(
        f"{history_url}?as_of=2026-09-20",
        headers={"X-Tenant-ID": str(tenant_id)},
    )

    assert initial_history.status_code == 200
    assert len(initial_history.json()) == 1
    assert initial_history.json()[0]["valid_from"] == "2026-04-10"
    assert initial_history.json()[0]["valid_to"] is None
    assert initial_history.json()[0]["address_line_1"] == "Sector 62"
    assert first_change.status_code == 200
    assert no_op.status_code == 200
    assert non_address.status_code == 200
    assert second_change.status_code == 200
    assert second_change.json()["id"] == created.json()["id"]
    assert second_change.json()["address_line_1"] == "Sector 64"
    assert final_history.status_code == 200
    assert [row["valid_from"] for row in final_history.json()] == [
        "2026-04-10",
        "2026-09-20",
        "2026-10-05",
    ]
    assert [row["valid_to"] for row in final_history.json()] == [
        "2026-09-19",
        "2026-10-04",
        None,
    ]
    assert [row["address_line_1"] for row in final_history.json()] == [
        "Sector 62",
        "Sector 63",
        "Sector 64",
    ]
    assert first_as_of.status_code == 200
    assert [row["address_line_1"] for row in first_as_of.json()] == [
        "Sector 62"
    ]
    assert second_as_of.status_code == 200
    assert [row["address_line_1"] for row in second_as_of.json()] == [
        "Sector 63"
    ]
    assert await _scalar(
        engine,
        "SELECT count(*) FROM core.company_location_versions "
        "WHERE company_location_id = :location_id",
        {"location_id": created.json()["id"]},
    ) == 3


async def test_location_address_history_uses_company_and_tenant_concealment(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI],
) -> None:
    client, engine, _ = api_context
    tenant_id = uuid4()
    other_tenant_id = uuid4()
    company_id = uuid4()
    sibling_company_id = uuid4()
    await _insert_tenant(engine, tenant_id)
    await _insert_tenant(engine, other_tenant_id)
    await _insert_company(engine, company_id=company_id, tenant_id=tenant_id)
    await _insert_company(
        engine,
        company_id=sibling_company_id,
        tenant_id=other_tenant_id,
    )
    await _insert_country(engine, code="IN")
    created = await client.post(
        f"/companies/{company_id}/locations",
        headers={"X-Tenant-ID": str(tenant_id)},
        json=_location_payload(),
    )
    assert created.status_code == 201

    wrong_company = await client.get(
        f"/companies/{sibling_company_id}/locations/"
        f"{created.json()['id']}/address-history",
        headers={"X-Tenant-ID": str(other_tenant_id)},
    )
    wrong_tenant = await client.get(
        f"/companies/{company_id}/locations/"
        f"{created.json()['id']}/address-history",
        headers={"X-Tenant-ID": str(other_tenant_id)},
    )

    assert wrong_company.status_code == 404
    assert wrong_tenant.status_code == 404
