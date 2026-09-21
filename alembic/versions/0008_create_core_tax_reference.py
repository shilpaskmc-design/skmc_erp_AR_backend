"""Create the tax-reference prerequisite foundation.

Revision ID: 0008_tax_reference
Revises: 0007_core_company_gst_registrations
Create Date: 2026-09-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_tax_reference"
down_revision: str | None = "0007_core_company_gst_registrations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CORE_SCHEMA = "core"


def _timestamps() -> tuple[sa.Column, sa.Column]:
    return (
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
    )


def upgrade() -> None:
    op.create_table(
        "tax_types",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "btrim(code) <> ''", name="ck_tax_types_code_not_blank"
        ),
        sa.CheckConstraint(
            "btrim(name) <> ''", name="ck_tax_types_name_not_blank"
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_tax_types_status",
        ),
        sa.ForeignKeyConstraint(
            ["country_code"],
            ["core.countries.code"],
            name="fk_tax_types_country_code_countries",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_tax_types"),
        sa.UniqueConstraint(
            "country_code", "code", name="uq_tax_types_country_code_code"
        ),
        schema=CORE_SCHEMA,
    )

    op.create_table(
        "company_hsn_sac_codes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("classification_type", sa.String(length=10), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "classification_type IN ('HSN', 'SAC')",
            name="ck_company_hsn_sac_codes_classification_type",
        ),
        sa.CheckConstraint(
            "btrim(code) <> ''",
            name="ck_company_hsn_sac_codes_code_not_blank",
        ),
        sa.CheckConstraint(
            "btrim(description) <> ''",
            name="ck_company_hsn_sac_codes_description_not_blank",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_company_hsn_sac_codes_status",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_company_hsn_sac_codes_company_id_companies",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_company_hsn_sac_codes"),
        sa.UniqueConstraint(
            "company_id",
            "classification_type",
            "code",
            name="uq_company_hsn_sac_codes_company_type_code",
        ),
        sa.UniqueConstraint(
            "company_id",
            "id",
            name="uq_company_hsn_sac_codes_company_id_id",
        ),
        schema=CORE_SCHEMA,
    )

    op.create_table(
        "tax_rates",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tax_type_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rate_percent", sa.Numeric(9, 6), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "rate_percent >= 0 AND rate_percent <= 100",
            name="ck_tax_rates_rate_percent_range",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_tax_rates_status",
        ),
        sa.ForeignKeyConstraint(
            ["tax_type_id"],
            ["core.tax_types.id"],
            name="fk_tax_rates_tax_type_id_tax_types",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["country_code"],
            ["core.countries.code"],
            name="fk_tax_rates_country_code_countries",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_tax_rates"),
        sa.UniqueConstraint(
            "tax_type_id",
            "country_code",
            "rate_percent",
            name="uq_tax_rates_tax_type_country_rate",
        ),
        schema=CORE_SCHEMA,
    )

    op.create_table(
        "company_hsn_sac_tax_rates",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "company_hsn_sac_code_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("tax_rate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_company_hsn_sac_tax_rates_date_order",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_company_hsn_sac_tax_rates_status",
        ),
        sa.ForeignKeyConstraint(
            ["company_hsn_sac_code_id"],
            ["core.company_hsn_sac_codes.id"],
            name="fk_company_hsn_sac_tax_rates_hsn_sac_code",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["tax_rate_id"],
            ["core.tax_rates.id"],
            name="fk_company_hsn_sac_tax_rates_tax_rate",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_company_hsn_sac_tax_rates"),
        postgresql.ExcludeConstraint(
            ("company_hsn_sac_code_id", "="),
            ("tax_rate_id", "="),
            (
                sa.func.daterange(
                    sa.column("valid_from"),
                    sa.column("valid_to"),
                    "[]",
                ),
                "&&",
            ),
            name="ex_company_hsn_sac_tax_rates_active_overlap",
            using="gist",
            where=sa.text("status = 'ACTIVE'"),
        ),
        schema=CORE_SCHEMA,
    )

    op.create_table(
        "tax_treatments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("tax_type_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "btrim(code) <> ''", name="ck_tax_treatments_code_not_blank"
        ),
        sa.CheckConstraint(
            "btrim(name) <> ''", name="ck_tax_treatments_name_not_blank"
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_tax_treatments_status",
        ),
        sa.ForeignKeyConstraint(
            ["tax_type_id"],
            ["core.tax_types.id"],
            name="fk_tax_treatments_tax_type_id_tax_types",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["country_code"],
            ["core.countries.code"],
            name="fk_tax_treatments_country_code_countries",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_tax_treatments"),
        sa.UniqueConstraint(
            "tax_type_id",
            "country_code",
            "code",
            name="uq_tax_treatments_tax_type_country_code",
        ),
        schema=CORE_SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("tax_treatments", schema=CORE_SCHEMA)
    op.drop_table("company_hsn_sac_tax_rates", schema=CORE_SCHEMA)
    op.drop_table("tax_rates", schema=CORE_SCHEMA)
    op.drop_table("company_hsn_sac_codes", schema=CORE_SCHEMA)
    op.drop_table("tax_types", schema=CORE_SCHEMA)
