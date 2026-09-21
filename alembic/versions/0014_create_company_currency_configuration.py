"""Create Company Reporting and AR Currency configuration.

Revision ID: 0014_company_currency_configuration
Revises: 0013_company_bank_accounts
Create Date: 2026-09-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014_company_currency_configuration"
down_revision: str | None = "0013_company_bank_accounts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CORE_SCHEMA = "core"
AR_SCHEMA = "ar"


def upgrade() -> None:
    op.create_table(
        "company_reporting_currencies",
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
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
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_company_reporting_currencies_status",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_company_reporting_currencies_company_id_companies",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["currency_code"],
            ["core.currencies.code"],
            name="fk_company_reporting_currencies_currency_code_currencies",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint(
            "company_id",
            "currency_code",
            name="pk_company_reporting_currencies",
        ),
        schema=CORE_SCHEMA,
    )

    op.create_table(
        "company_ar_currencies",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column(
            "billing_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "receipt_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "is_default_billing",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "is_default_receipt",
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
            "NOT is_default_billing OR billing_enabled",
            name="ck_company_ar_currencies_default_billing_enabled",
        ),
        sa.CheckConstraint(
            "NOT is_default_receipt OR receipt_enabled",
            name="ck_company_ar_currencies_default_receipt_enabled",
        ),
        sa.CheckConstraint(
            "status <> 'ACTIVE' OR billing_enabled OR receipt_enabled",
            name="ck_company_ar_currencies_active_use_enabled",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_company_ar_currencies_status",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_company_ar_currencies_company_id_companies",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["currency_code"],
            ["core.currencies.code"],
            name="fk_company_ar_currencies_currency_code_currencies",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_company_ar_currencies"),
        sa.UniqueConstraint(
            "company_id",
            "currency_code",
            name="uq_company_ar_currencies_company_currency",
        ),
        schema=AR_SCHEMA,
    )
    op.create_index(
        "uq_company_ar_currencies_active_billing_default",
        "company_ar_currencies",
        ["company_id"],
        unique=True,
        schema=AR_SCHEMA,
        postgresql_where=sa.text(
            "status = 'ACTIVE' AND billing_enabled = true "
            "AND is_default_billing = true"
        ),
    )
    op.create_index(
        "uq_company_ar_currencies_active_receipt_default",
        "company_ar_currencies",
        ["company_id"],
        unique=True,
        schema=AR_SCHEMA,
        postgresql_where=sa.text(
            "status = 'ACTIVE' AND receipt_enabled = true "
            "AND is_default_receipt = true"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_company_ar_currencies_active_receipt_default",
        table_name="company_ar_currencies",
        schema=AR_SCHEMA,
    )
    op.drop_index(
        "uq_company_ar_currencies_active_billing_default",
        table_name="company_ar_currencies",
        schema=AR_SCHEMA,
    )
    op.drop_table("company_ar_currencies", schema=AR_SCHEMA)
    op.drop_table("company_reporting_currencies", schema=CORE_SCHEMA)
