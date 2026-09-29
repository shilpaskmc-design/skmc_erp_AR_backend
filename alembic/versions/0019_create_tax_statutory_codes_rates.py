"""Create Tax Statutory Codes and effective rate cases.

Revision ID: 0019_tax_statutory_codes_rates
Revises: 0018_gl_account_group_mappings
Create Date: 2026-09-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0019_tax_statutory_codes_rates"
down_revision: str | None = "0018_gl_account_group_mappings"
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
        "tax_statutory_codes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tax_type_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("code_kind", sa.String(length=20), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "btrim(code) <> ''",
            name="ck_tax_statutory_codes_code_not_blank",
        ),
        sa.CheckConstraint(
            "btrim(name) <> ''",
            name="ck_tax_statutory_codes_name_not_blank",
        ),
        sa.CheckConstraint(
            "code_kind IN ('COMPONENT', 'SECTION')",
            name="ck_tax_statutory_codes_code_kind",
        ),
        sa.CheckConstraint(
            "country_code ~ '^[A-Z]{2}$'",
            name="ck_tax_statutory_codes_country_code_format",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_tax_statutory_codes_status",
        ),
        sa.ForeignKeyConstraint(
            ["tax_type_id"],
            ["core.tax_types.id"],
            name="fk_tax_statutory_codes_tax_type_id_tax_types",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_tax_statutory_codes"),
        sa.UniqueConstraint(
            "tax_type_id",
            "country_code",
            "code_kind",
            "code",
            name="uq_tax_statutory_codes_tax_type_country_kind_code",
        ),
        schema=CORE_SCHEMA,
    )

    op.create_table(
        "tax_statutory_code_rates",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "tax_statutory_code_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("case_code", sa.String(length=50), nullable=True),
        sa.Column("rate_percent", sa.Numeric(9, 6), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "case_code IS NULL OR btrim(case_code) <> ''",
            name="ck_tax_statutory_code_rates_case_code_not_blank",
        ),
        sa.CheckConstraint(
            "rate_percent >= 0 AND rate_percent <= 100",
            name="ck_tax_statutory_code_rates_rate_percent_range",
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_tax_statutory_code_rates_date_order",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_tax_statutory_code_rates_status",
        ),
        sa.ForeignKeyConstraint(
            ["tax_statutory_code_id"],
            ["core.tax_statutory_codes.id"],
            name="fk_tax_statutory_code_rates_statutory_code",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_tax_statutory_code_rates"),
        postgresql.ExcludeConstraint(
            ("tax_statutory_code_id", "="),
            ("case_code", "="),
            (
                sa.func.daterange(
                    sa.column("valid_from"),
                    sa.column("valid_to"),
                    "[]",
                ),
                "&&",
            ),
            name="ex_tax_statutory_code_rates_active_named_overlap",
            using="gist",
            where=sa.text("status = 'ACTIVE' AND case_code IS NOT NULL"),
        ),
        postgresql.ExcludeConstraint(
            ("tax_statutory_code_id", "="),
            (
                sa.func.daterange(
                    sa.column("valid_from"),
                    sa.column("valid_to"),
                    "[]",
                ),
                "&&",
            ),
            name="ex_tax_statutory_code_rates_active_default_overlap",
            using="gist",
            where=sa.text("status = 'ACTIVE' AND case_code IS NULL"),
        ),
        schema=CORE_SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("tax_statutory_code_rates", schema=CORE_SCHEMA)
    op.drop_table("tax_statutory_codes", schema=CORE_SCHEMA)
