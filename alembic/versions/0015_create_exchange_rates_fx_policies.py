"""Create Exchange Rate facts and AR FX Policies.

Revision ID: 0015_exchange_rates_fx_policies
Revises: 0014_company_currency_configuration
Create Date: 2026-09-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015_exchange_rates_fx_policies"
down_revision: str | None = "0014_company_currency_configuration"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CORE_SCHEMA = "core"
AR_SCHEMA = "ar"


def upgrade() -> None:
    op.create_table(
        "exchange_rates",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_currency_code", sa.String(length=3), nullable=False),
        sa.Column("to_currency_code", sa.String(length=3), nullable=False),
        sa.Column("rate", sa.Numeric(precision=28, scale=12), nullable=False),
        sa.Column("rate_type", sa.String(length=20), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=True),
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
            "rate > 0",
            name="ck_exchange_rates_rate_positive",
        ),
        sa.CheckConstraint(
            "from_currency_code <> to_currency_code",
            name="ck_exchange_rates_currency_pair",
        ),
        sa.CheckConstraint(
            "rate_type IN ('CORPORATE', 'SPOT')",
            name="ck_exchange_rates_rate_type",
        ),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_exchange_rates_effective_dates",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_exchange_rates_status",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_exchange_rates_company_id_companies",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["from_currency_code"],
            ["core.currencies.code"],
            name="fk_exchange_rates_from_currency_currencies",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["to_currency_code"],
            ["core.currencies.code"],
            name="fk_exchange_rates_to_currency_currencies",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_exchange_rates"),
        postgresql.ExcludeConstraint(
            ("company_id", "="),
            ("from_currency_code", "="),
            ("to_currency_code", "="),
            ("rate_type", "="),
            (
                sa.func.daterange(
                    sa.column("effective_from"),
                    sa.column("effective_to"),
                    "[]",
                ),
                "&&",
            ),
            name="ex_exchange_rates_active_period_overlap",
            using="gist",
            where=sa.text("status = 'ACTIVE'"),
        ),
        schema=CORE_SCHEMA,
    )

    op.create_table(
        "fx_policies",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purpose", sa.String(length=20), nullable=False),
        sa.Column("default_rate_type", sa.String(length=20), nullable=False),
        sa.Column(
            "allow_user_fixed_override",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "reason_required_for_override",
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
            "purpose IN ('BILLING', 'RECEIPT', 'REPORTING')",
            name="ck_fx_policies_purpose",
        ),
        sa.CheckConstraint(
            "default_rate_type IN ('CORPORATE', 'SPOT')",
            name="ck_fx_policies_default_rate_type",
        ),
        sa.CheckConstraint(
            "NOT reason_required_for_override OR allow_user_fixed_override",
            name="ck_fx_policies_override_reason_requires_override",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_fx_policies_status",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_fx_policies_company_id_companies",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_fx_policies"),
        sa.UniqueConstraint(
            "company_id",
            "purpose",
            name="uq_fx_policies_company_id_purpose",
        ),
        schema=AR_SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("fx_policies", schema=AR_SCHEMA)
    op.drop_table("exchange_rates", schema=CORE_SCHEMA)
