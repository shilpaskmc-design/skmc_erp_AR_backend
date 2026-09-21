"""Create Company fiscal settings and Financial Years.

Revision ID: 0006_core_financial_years
Revises: 0005_core_company_locations
Create Date: 2026-09-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_core_financial_years"
down_revision: str | None = "0005_core_company_locations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CORE_SCHEMA = "core"


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.create_table(
        "company_fiscal_settings",
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("fiscal_year_pattern", sa.String(length=20), nullable=False),
        sa.Column("start_month", sa.SmallInteger(), nullable=False),
        sa.Column("start_day", sa.SmallInteger(), nullable=False),
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
            "fiscal_year_pattern IN ('APR_MAR', 'JAN_DEC', 'CUSTOM')",
            name="ck_company_fiscal_settings_pattern",
        ),
        sa.CheckConstraint(
            "start_month BETWEEN 1 AND 12",
            name="ck_company_fiscal_settings_start_month",
        ),
        sa.CheckConstraint(
            "start_day BETWEEN 1 AND CASE "
            "WHEN start_month = 2 THEN 28 "
            "WHEN start_month IN (4, 6, 9, 11) THEN 30 "
            "ELSE 31 END",
            name="ck_company_fiscal_settings_recurring_date",
        ),
        sa.CheckConstraint(
            "(fiscal_year_pattern = 'APR_MAR' "
            "AND start_month = 4 AND start_day = 1) "
            "OR (fiscal_year_pattern = 'JAN_DEC' "
            "AND start_month = 1 AND start_day = 1) "
            "OR fiscal_year_pattern = 'CUSTOM'",
            name="ck_company_fiscal_settings_pattern_values",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_company_fiscal_settings_company_id_companies",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint(
            "company_id",
            name="pk_company_fiscal_settings",
        ),
        schema=CORE_SCHEMA,
    )

    op.create_table(
        "financial_years",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("display_code", sa.String(length=30), nullable=False),
        sa.Column(
            "is_transition",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
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
            "end_date >= start_date",
            name="ck_financial_years_date_order",
        ),
        sa.CheckConstraint(
            "btrim(display_code) <> ''",
            name="ck_financial_years_display_code_not_blank",
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'OPEN', 'CLOSED')",
            name="ck_financial_years_status",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_financial_years_company_id_companies",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_financial_years"),
        sa.UniqueConstraint(
            "company_id",
            "display_code",
            name="uq_financial_years_company_id_display_code",
        ),
        postgresql.ExcludeConstraint(
            ("company_id", "="),
            (
                sa.func.daterange(
                    sa.column("start_date"),
                    sa.column("end_date"),
                    "[]",
                ),
                "&&",
            ),
            name="ex_financial_years_company_date_overlap",
            using="gist",
        ),
        schema=CORE_SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("financial_years", schema=CORE_SCHEMA)
    op.drop_table("company_fiscal_settings", schema=CORE_SCHEMA)
    # btree_gist is cluster-scoped and may be shared by unrelated schemas, so
    # downgrade intentionally leaves the extension installed.
