"""Create stable Company GL Accounts.

Revision ID: 0012_gl_accounts
Revises: 0011_payment_terms
Create Date: 2026-09-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012_gl_accounts"
down_revision: str | None = "0011_payment_terms"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CORE_SCHEMA = "core"


def upgrade() -> None:
    op.create_table(
        "gl_accounts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_code", sa.String(length=50), nullable=True),
        sa.Column("account_name", sa.String(length=200), nullable=False),
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
            "account_code IS NULL OR btrim(account_code) <> ''",
            name="ck_gl_accounts_code_not_blank",
        ),
        sa.CheckConstraint(
            "btrim(account_name) <> ''",
            name="ck_gl_accounts_name_not_blank",
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_gl_accounts_valid_range",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_gl_accounts_status",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_gl_accounts_company_id_companies",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_gl_accounts"),
        sa.UniqueConstraint(
            "company_id",
            "id",
            name="uq_gl_accounts_company_id_id",
        ),
        schema=CORE_SCHEMA,
    )
    op.create_index(
        "uq_gl_accounts_company_id_account_code",
        "gl_accounts",
        ["company_id", "account_code"],
        unique=True,
        schema=CORE_SCHEMA,
        postgresql_where=sa.text("account_code IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_gl_accounts_company_id_account_code",
        table_name="gl_accounts",
        schema=CORE_SCHEMA,
    )
    op.drop_table("gl_accounts", schema=CORE_SCHEMA)
