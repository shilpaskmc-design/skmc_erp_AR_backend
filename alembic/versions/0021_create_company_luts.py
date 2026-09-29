"""Create Company LUT configuration.

Revision ID: 0021_company_luts
Revises: 0020_accounting_configuration
Create Date: 2026-09-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0021_company_luts"
down_revision: str | None = "0020_accounting_configuration"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_company_gst_registrations_company_id_id",
        "company_gst_registrations",
        ["company_id", "id"],
        schema="core",
    )
    op.create_unique_constraint(
        "uq_financial_years_company_id_id",
        "financial_years",
        ["company_id", "id"],
        schema="core",
    )
    op.create_table(
        "company_luts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "gst_registration_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "financial_year_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("lut_reference", sa.String(length=100), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
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
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_company_luts_date_order",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_company_luts_status",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_company_luts_company_id_companies",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "gst_registration_id"],
            [
                "core.company_gst_registrations.company_id",
                "core.company_gst_registrations.id",
            ],
            name="fk_company_luts_company_gst_registration",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "financial_year_id"],
            ["core.financial_years.company_id", "core.financial_years.id"],
            name="fk_company_luts_company_financial_year",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_company_luts"),
        schema="ar",
    )
    op.create_index(
        "uq_company_luts_active_gst_registration_financial_year",
        "company_luts",
        ["gst_registration_id", "financial_year_id"],
        unique=True,
        schema="ar",
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_company_luts_active_gst_registration_financial_year",
        table_name="company_luts",
        schema="ar",
    )
    op.drop_table("company_luts", schema="ar")
    op.drop_constraint(
        "uq_financial_years_company_id_id",
        "financial_years",
        type_="unique",
        schema="core",
    )
    op.drop_constraint(
        "uq_company_gst_registrations_company_id_id",
        "company_gst_registrations",
        type_="unique",
        schema="core",
    )
