"""Create the Core/Shared Company identity foundation.

Revision ID: 0003_core_company_identity
Revises: 0002_create_core_entity_types
Create Date: 2026-09-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_core_company_identity"
down_revision: str | None = "0002_create_core_entity_types"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CORE_SCHEMA = "core"
COMPANY_CODE_SEQUENCE = "company_code_seq"
COMPANY_CODE_FUNCTION = "next_company_code"


def upgrade() -> None:
    op.create_table(
        "currencies",
        sa.Column("code", sa.String(length=3), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("symbol", sa.String(length=16), nullable=True),
        sa.Column("minor_units", sa.SmallInteger(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "code ~ '^[A-Z]{3}$'",
            name="ck_currencies_code_format",
        ),
        sa.CheckConstraint(
            "btrim(name) <> ''",
            name="ck_currencies_name_not_blank",
        ),
        sa.CheckConstraint(
            "symbol IS NULL OR btrim(symbol) <> ''",
            name="ck_currencies_symbol_not_blank",
        ),
        sa.CheckConstraint(
            "minor_units BETWEEN 0 AND 4",
            name="ck_currencies_minor_units_range",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_currencies_status",
        ),
        sa.PrimaryKeyConstraint("code", name="pk_currencies"),
        schema=CORE_SCHEMA,
    )

    op.create_table(
        "organisations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "btrim(name) <> ''",
            name="ck_organisations_name_not_blank",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_organisations_status",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["core.tenants.id"],
            name="fk_organisations_tenant_id_tenants",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_organisations"),
        sa.UniqueConstraint(
            "tenant_id",
            "name",
            name="uq_organisations_tenant_id_name",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "id",
            name="uq_organisations_tenant_id_id",
        ),
        schema=CORE_SCHEMA,
    )

    op.execute(
        sa.schema.CreateSequence(
            sa.Sequence(
                COMPANY_CODE_SEQUENCE,
                schema=CORE_SCHEMA,
                start=1,
                increment=1,
            )
        )
    )
    op.execute(
        f"""
        CREATE FUNCTION {CORE_SCHEMA}.{COMPANY_CODE_FUNCTION}()
        RETURNS VARCHAR(50)
        LANGUAGE SQL
        VOLATILE
        AS $$
            WITH generated AS (
                SELECT nextval('{CORE_SCHEMA}.{COMPANY_CODE_SEQUENCE}') AS value
            )
            SELECT 'COM' || lpad(
                value::text,
                GREATEST(6, length(value::text)),
                '0'
            )
            FROM generated
        $$
        """
    )

    op.create_table(
        "companies",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "organisation_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("legal_name", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=True),
        sa.Column(
            "company_code",
            sa.String(length=50),
            server_default=sa.text(
                f"{CORE_SCHEMA}.{COMPANY_CODE_FUNCTION}()"
            ),
            nullable=False,
        ),
        sa.Column(
            "entity_type_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("country_code", sa.String(length=2), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("website", sa.String(length=2048), nullable=True),
        sa.Column("base_timezone", sa.String(length=64), nullable=True),
        sa.Column("base_currency_code", sa.String(length=3), nullable=True),
        sa.Column("business_nature", sa.String(length=20), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "btrim(legal_name) <> ''",
            name="ck_companies_legal_name_not_blank",
        ),
        sa.CheckConstraint(
            "display_name IS NULL OR btrim(display_name) <> ''",
            name="ck_companies_display_name_not_blank",
        ),
        sa.CheckConstraint(
            "company_code ~ '^COM[0-9]{6,}$'",
            name="ck_companies_company_code_format",
        ),
        sa.CheckConstraint(
            "country_code IS NULL OR country_code ~ '^[A-Z]{2}$'",
            name="ck_companies_country_code_format",
        ),
        sa.CheckConstraint(
            "email IS NULL OR btrim(email) <> ''",
            name="ck_companies_email_not_blank",
        ),
        sa.CheckConstraint(
            "phone IS NULL OR btrim(phone) <> ''",
            name="ck_companies_phone_not_blank",
        ),
        sa.CheckConstraint(
            "website IS NULL OR btrim(website) <> ''",
            name="ck_companies_website_not_blank",
        ),
        sa.CheckConstraint(
            "base_timezone IS NULL OR btrim(base_timezone) <> ''",
            name="ck_companies_base_timezone_not_blank",
        ),
        sa.CheckConstraint(
            "business_nature IS NULL OR "
            "business_nature IN ('SERVICES', 'GOODS', 'BOTH')",
            name="ck_companies_business_nature",
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'ACTIVE', 'INACTIVE')",
            name="ck_companies_status",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["core.tenants.id"],
            name="fk_companies_tenant_id_tenants",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organisation_id"],
            ["core.organisations.tenant_id", "core.organisations.id"],
            name="fk_companies_tenant_organisation",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["entity_type_id"],
            ["core.entity_types.id"],
            name="fk_companies_entity_type_id_entity_types",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["base_currency_code"],
            ["core.currencies.code"],
            name="fk_companies_base_currency_code_currencies",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_companies"),
        sa.UniqueConstraint(
            "company_code",
            name="uq_companies_company_code",
        ),
        schema=CORE_SCHEMA,
    )
    op.create_index(
        "ix_companies_tenant_id_organisation_id",
        "companies",
        ["tenant_id", "organisation_id"],
        unique=False,
        schema=CORE_SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_companies_tenant_id_organisation_id",
        table_name="companies",
        schema=CORE_SCHEMA,
    )
    op.drop_table("companies", schema=CORE_SCHEMA)
    op.execute(
        f"DROP FUNCTION {CORE_SCHEMA}.{COMPANY_CODE_FUNCTION}()"
    )
    op.execute(
        sa.schema.DropSequence(
            sa.Sequence(COMPANY_CODE_SEQUENCE, schema=CORE_SCHEMA)
        )
    )
    op.drop_table("organisations", schema=CORE_SCHEMA)
    op.drop_table("currencies", schema=CORE_SCHEMA)
