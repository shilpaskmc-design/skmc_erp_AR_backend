"""Create Company Payment Terms.

Revision ID: 0011_payment_terms
Revises: 0010_cost_center_configuration
Create Date: 2026-09-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011_payment_terms"
down_revision: str | None = "0010_cost_center_configuration"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

AR_SCHEMA = "ar"


def upgrade() -> None:
    op.create_table(
        "payment_terms",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("term_type", sa.String(length=20), nullable=False),
        sa.Column("credit_days", sa.SmallInteger(), nullable=False),
        sa.Column(
            "is_default",
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
            "btrim(name) <> ''",
            name="ck_payment_terms_name_not_blank",
        ),
        sa.CheckConstraint(
            "term_type IN ('IMMEDIATE', 'NET_DAYS')",
            name="ck_payment_terms_term_type",
        ),
        sa.CheckConstraint(
            "(term_type = 'IMMEDIATE' AND credit_days = 0) OR "
            "(term_type = 'NET_DAYS' AND credit_days > 0)",
            name="ck_payment_terms_credit_days",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_payment_terms_status",
        ),
        sa.CheckConstraint(
            "NOT is_default OR status = 'ACTIVE'",
            name="ck_payment_terms_default_active",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_payment_terms_company_id_companies",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_payment_terms"),
        sa.UniqueConstraint(
            "company_id",
            "code",
            name="uq_payment_terms_company_id_code",
        ),
        schema=AR_SCHEMA,
    )
    op.create_index(
        "uq_payment_terms_active_default_company",
        "payment_terms",
        ["company_id"],
        unique=True,
        schema=AR_SCHEMA,
        postgresql_where=sa.text("is_default = true AND status = 'ACTIVE'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_payment_terms_active_default_company",
        table_name="payment_terms",
        schema=AR_SCHEMA,
    )
    op.drop_table("payment_terms", schema=AR_SCHEMA)
