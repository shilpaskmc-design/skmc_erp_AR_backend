"""Create Core Company Bank Accounts.

Revision ID: 0013_company_bank_accounts
Revises: 0012_gl_accounts
Create Date: 2026-09-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013_company_bank_accounts"
down_revision: str | None = "0012_gl_accounts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CORE_SCHEMA = "core"


def upgrade() -> None:
    op.create_table(
        "company_bank_accounts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_holder_name", sa.String(length=200), nullable=False),
        sa.Column("bank_name", sa.String(length=200), nullable=False),
        sa.Column("account_number", sa.String(length=64), nullable=False),
        sa.Column("branch_name", sa.String(length=200), nullable=True),
        sa.Column("ifsc", sa.String(length=11), nullable=True),
        sa.Column("swift", sa.String(length=11), nullable=True),
        sa.Column("iban", sa.String(length=34), nullable=True),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("account_type", sa.String(length=30), nullable=True),
        sa.Column("gl_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "is_default_for_billing",
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
            "btrim(account_holder_name) <> ''",
            name="ck_company_bank_accounts_holder_name_not_blank",
        ),
        sa.CheckConstraint(
            "btrim(bank_name) <> ''",
            name="ck_company_bank_accounts_bank_name_not_blank",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_company_bank_accounts_status",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_company_bank_accounts_company_id_companies",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["currency_code"],
            ["core.currencies.code"],
            name="fk_company_bank_accounts_currency_code_currencies",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "gl_account_id"],
            ["core.gl_accounts.company_id", "core.gl_accounts.id"],
            name="fk_company_bank_accounts_company_gl_account",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_company_bank_accounts"),
        sa.UniqueConstraint(
            "company_id",
            "id",
            name="uq_company_bank_accounts_company_id_id",
        ),
        schema=CORE_SCHEMA,
    )
    op.create_index(
        "uq_company_bank_accounts_active_billing_default",
        "company_bank_accounts",
        ["company_id", "currency_code"],
        unique=True,
        schema=CORE_SCHEMA,
        postgresql_where=sa.text(
            "is_default_for_billing = true AND status = 'ACTIVE'"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_company_bank_accounts_active_billing_default",
        table_name="company_bank_accounts",
        schema=CORE_SCHEMA,
    )
    op.drop_table("company_bank_accounts", schema=CORE_SCHEMA)
