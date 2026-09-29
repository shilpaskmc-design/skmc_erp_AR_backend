import asyncio
import os
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy.engine import make_url

from skmc_erp.config import get_settings
from tests.integration.company_configuration_migration_support import (
    execute,
    rejected,
    scalar,
)

REVISION = "0027_company_document_presentation"
PREVIOUS_REVISION = "0026_company_location_versions"


async def _seed_legacy_rows(url: str) -> tuple[UUID, UUID, UUID]:
    tenant_id = await scalar(
        url,
        "INSERT INTO core.tenants (name, status) "
        "VALUES ('G2 Migration Tenant', 'ACTIVE') RETURNING id",
    )
    company_id = await scalar(
        url,
        "INSERT INTO core.companies (tenant_id, legal_name, status) "
        "VALUES (:tenant, 'G2 Company', 'DRAFT') RETURNING id",
        {"tenant": tenant_id},
    )
    other_company_id = await scalar(
        url,
        "INSERT INTO core.companies (tenant_id, legal_name, status) "
        "VALUES (:tenant, 'Other G2 Company', 'DRAFT') RETURNING id",
        {"tenant": tenant_id},
    )
    branding_id = await scalar(
        url,
        "INSERT INTO ar.company_document_branding (company_id, status) "
        "VALUES (:company, 'ACTIVE') RETURNING id",
        {"company": company_id},
    )
    await execute(
        url,
        "INSERT INTO ar.company_document_branding (company_id, status) "
        "VALUES (:company, 'ACTIVE')",
        {"company": company_id},
    )
    for document_type, template_key in (
        ("PI", "STANDARD"),
        ("TI", "MODERN"),
    ):
        await execute(
            url,
            """
            INSERT INTO ar.company_document_templates (
                company_id, document_type, branding_id, template_key,
                version_no, show_logo, show_bank_details, show_signature,
                show_hsn_sac, show_customer_reference, status
            ) VALUES (
                :company, :document_type, :branding, :template_key,
                1, true, true, true, true, true, 'ACTIVE'
            )
            """,
            {
                "company": company_id,
                "document_type": document_type,
                "branding": branding_id,
                "template_key": template_key,
            },
        )
    return company_id, other_company_id, branding_id


async def _exercise(
    url: str,
    company_id: UUID,
    other_company_id: UUID,
    branding_id: UUID,
) -> None:
    assert await scalar(
        url,
        """
        SELECT is_nullable = 'YES'
        FROM information_schema.columns
        WHERE table_schema = 'ar'
          AND table_name = 'company_document_templates'
          AND column_name = 'document_type'
        """,
    )
    for column_name in (
        "show_logo",
        "show_bank_details",
        "show_signature",
        "show_hsn_sac",
        "show_customer_reference",
    ):
        assert await scalar(
            url,
            """
            SELECT is_nullable = 'YES'
            FROM information_schema.columns
            WHERE table_schema = 'ar'
              AND table_name = 'company_document_templates'
              AND column_name = :column_name
            """,
            {"column_name": column_name},
        )

    assert await scalar(
        url,
        "SELECT count(*) FROM ar.company_document_templates "
        "WHERE company_id = :company AND status = 'ACTIVE'",
        {"company": company_id},
    ) == 0
    assert await scalar(
        url,
        "SELECT count(*) FROM ar.company_document_branding "
        "WHERE company_id = :company AND status = 'ACTIVE'",
        {"company": company_id},
    ) == 0
    current_branding_id = await scalar(
        url,
        "INSERT INTO ar.company_document_branding (company_id, status) "
        "VALUES (:company, 'ACTIVE') RETURNING id",
        {"company": company_id},
    )
    await rejected(
        url,
        "INSERT INTO ar.company_document_branding (company_id, status) "
        "VALUES (:company, 'ACTIVE')",
        {"company": company_id},
    )
    assert await scalar(
        url,
        "SELECT array_agg(document_type ORDER BY version_no) "
        "FROM ar.company_document_templates WHERE company_id = :company",
        {"company": company_id},
    ) == ["PI", "TI"]
    assert await scalar(
        url,
        "SELECT array_agg(version_no ORDER BY version_no) "
        "FROM ar.company_document_templates WHERE company_id = :company",
        {"company": company_id},
    ) == [1, 2]

    constraint_names = await scalar(
        url,
        """
        SELECT array_agg(con.conname ORDER BY con.conname)
        FROM pg_constraint con
        JOIN pg_class rel ON rel.oid = con.conrelid
        JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
        WHERE nsp.nspname = 'ar'
          AND rel.relname = 'company_document_templates'
          AND con.conname IN (
              'ck_company_document_templates_active_company_wide',
              'uq_company_document_templates_company_version'
          )
        """,
    )
    assert constraint_names == [
        "ck_company_document_templates_active_company_wide",
        "uq_company_document_templates_company_version",
    ]
    assert await scalar(
        url,
        """
        SELECT count(*) = 2
        FROM pg_indexes
        WHERE schemaname = 'ar'
          AND indexname IN (
              'uq_company_document_templates_active_company',
              'uq_company_document_branding_active_company'
          )
        """,
    )

    await execute(
        url,
        """
        INSERT INTO ar.company_document_templates (
            company_id, branding_id, template_key, version_no, status
        ) VALUES (
            :company, :branding, 'STANDARD_V1', 3, 'ACTIVE'
        )
        """,
        {"company": company_id, "branding": current_branding_id},
    )
    await rejected(
        url,
        """
        INSERT INTO ar.company_document_templates (
            company_id, template_key, version_no, status
        ) VALUES (
            :company, 'MODERN_V1', 4, 'ACTIVE'
        )
        """,
        {"company": company_id},
    )
    await rejected(
        url,
        """
        INSERT INTO ar.company_document_templates (
            company_id, document_type, template_key, version_no, status
        ) VALUES (
            :company, 'TI', 'MODERN_V1', 4, 'ACTIVE'
        )
        """,
        {"company": company_id},
    )
    await execute(
        url,
        """
        INSERT INTO ar.company_document_templates (
            company_id, document_type, template_key, version_no, status
        ) VALUES (
            :company, 'CN', 'COMPACT_V1', 4, 'INACTIVE'
        )
        """,
        {"company": company_id},
    )
    await rejected(
        url,
        """
        INSERT INTO ar.company_document_templates (
            company_id, document_type, template_key, version_no, status
        ) VALUES (
            :company, 'DN', 'MODERN_V1', 4, 'INACTIVE'
        )
        """,
        {"company": company_id},
    )
    await rejected(
        url,
        """
        INSERT INTO ar.company_document_templates (
            company_id, branding_id, template_key, version_no, status
        ) VALUES (
            :company, :branding, 'STANDARD_V1', 1, 'INACTIVE'
        )
        """,
        {"company": other_company_id, "branding": branding_id},
    )


async def _safe_empty(url: str) -> None:
    assert not await scalar(url, "SELECT to_regnamespace('core') IS NOT NULL")
    if await scalar(
        url, "SELECT to_regclass('public.alembic_version') IS NOT NULL"
    ):
        assert await scalar(url, "SELECT count(*) FROM alembic_version") == 0


def test_company_document_presentation_alignment_migration() -> None:
    url = os.getenv("TEST_DATABASE_URL")
    if url is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL migration tests")
    if make_url(url).drivername != "postgresql+asyncpg":
        pytest.fail("TEST_DATABASE_URL must use postgresql+asyncpg")

    asyncio.run(_safe_empty(url))
    old_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    get_settings.cache_clear()
    config = Config("alembic.ini")
    try:
        command.upgrade(config, PREVIOUS_REVISION)
        company_id, other_company_id, branding_id = asyncio.run(
            _seed_legacy_rows(url)
        )
        command.upgrade(config, REVISION)
        assert asyncio.run(
            scalar(url, "SELECT version_num FROM alembic_version")
        ) == REVISION
        asyncio.run(
            _exercise(url, company_id, other_company_id, branding_id)
        )

        command.downgrade(config, PREVIOUS_REVISION)
        assert asyncio.run(
            scalar(url, "SELECT version_num FROM alembic_version")
        ) == PREVIOUS_REVISION
        assert not asyncio.run(
            scalar(
                url,
                "SELECT is_nullable = 'YES' "
                "FROM information_schema.columns "
                "WHERE table_schema = 'ar' "
                "AND table_name = 'company_document_templates' "
                "AND column_name = 'document_type'",
            )
        )

        command.upgrade(config, REVISION)
        assert asyncio.run(
            scalar(url, "SELECT version_num FROM alembic_version")
        ) == REVISION
        assert len(ScriptDirectory.from_config(config).get_heads()) == 1
    finally:
        try:
            command.downgrade(config, "base")
        finally:
            if old_url is None:
                os.environ.pop("DATABASE_URL", None)
            else:
                os.environ["DATABASE_URL"] = old_url
            get_settings.cache_clear()
