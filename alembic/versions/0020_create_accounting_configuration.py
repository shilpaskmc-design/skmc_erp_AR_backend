"""Create current AR accounting configuration.

Revision ID: 0020_accounting_configuration
Revises: 0019_tax_statutory_codes_rates
Create Date: 2026-09-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0020_accounting_configuration"
down_revision: str | None = "0019_tax_statutory_codes_rates"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


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
        "revenue_gl_mappings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supply_type_code", sa.String(length=30), nullable=False),
        sa.Column(
            "company_hsn_sac_code_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("gl_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_revenue_gl_mappings_date_order",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_revenue_gl_mappings_status",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_revenue_gl_mappings_company_id_companies",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "company_hsn_sac_code_id"],
            [
                "core.company_hsn_sac_codes.company_id",
                "core.company_hsn_sac_codes.id",
            ],
            name="fk_revenue_gl_mappings_company_hsn_sac_code",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "gl_account_id"],
            ["core.gl_accounts.company_id", "core.gl_accounts.id"],
            name="fk_revenue_gl_mappings_company_gl_account",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_revenue_gl_mappings"),
        postgresql.ExcludeConstraint(
            ("company_id", "="),
            ("supply_type_code", "="),
            ("company_hsn_sac_code_id", "="),
            (
                sa.func.daterange(
                    sa.column("valid_from"),
                    sa.column("valid_to"),
                    "[]",
                ),
                "&&",
            ),
            name="ex_revenue_gl_mappings_specific_period_overlap",
            using="gist",
            where=sa.text("company_hsn_sac_code_id IS NOT NULL"),
        ),
        postgresql.ExcludeConstraint(
            ("company_id", "="),
            ("supply_type_code", "="),
            (
                sa.func.daterange(
                    sa.column("valid_from"),
                    sa.column("valid_to"),
                    "[]",
                ),
                "&&",
            ),
            name="ex_revenue_gl_mappings_general_period_overlap",
            using="gist",
            where=sa.text("company_hsn_sac_code_id IS NULL"),
        ),
        schema="ar",
    )

    op.create_table(
        "tax_gl_account_mappings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "tax_statutory_code_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("gl_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_tax_gl_account_mappings_date_order",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_tax_gl_account_mappings_status",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_tax_gl_account_mappings_company_id_companies",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["tax_statutory_code_id"],
            ["core.tax_statutory_codes.id"],
            name="fk_tax_gl_account_mappings_statutory_code",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "gl_account_id"],
            ["core.gl_accounts.company_id", "core.gl_accounts.id"],
            name="fk_tax_gl_account_mappings_company_gl_account",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_tax_gl_account_mappings"),
        postgresql.ExcludeConstraint(
            ("company_id", "="),
            ("tax_statutory_code_id", "="),
            (
                sa.func.daterange(
                    sa.column("valid_from"),
                    sa.column("valid_to"),
                    "[]",
                ),
                "&&",
            ),
            name="ex_tax_gl_account_mappings_period_overlap",
            using="gist",
        ),
        schema="ar",
    )

    op.create_table(
        "company_accounting_settings",
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "default_receivable_gl_account_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_company_accounting_settings_company_id_companies",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "default_receivable_gl_account_id"],
            ["core.gl_accounts.company_id", "core.gl_accounts.id"],
            name="fk_company_accounting_settings_company_receivable_gl",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("company_id", name="pk_company_accounting_settings"),
        schema="core",
    )


def downgrade() -> None:
    op.drop_table("company_accounting_settings", schema="core")
    op.drop_table("tax_gl_account_mappings", schema="ar")
    op.drop_table("revenue_gl_mappings", schema="ar")
