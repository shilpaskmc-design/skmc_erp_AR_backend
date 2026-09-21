"""Create Account Hierarchies and Account Groups.

Revision ID: 0016_account_hierarchies_groups
Revises: 0015_exchange_rates_fx_policies
Create Date: 2026-09-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0016_account_hierarchies_groups"
down_revision: str | None = "0015_exchange_rates_fx_policies"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CORE_SCHEMA = "core"


def upgrade() -> None:
    op.create_table(
        "account_hierarchies",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("hierarchy_name", sa.String(length=150), nullable=False),
        sa.Column("purpose_code", sa.String(length=30), nullable=False),
        sa.Column(
            "is_primary",
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
            "btrim(hierarchy_name) <> ''",
            name="ck_account_hierarchies_name_not_blank",
        ),
        sa.CheckConstraint(
            "purpose_code = 'ACCOUNTING'",
            name="ck_account_hierarchies_purpose_code",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_account_hierarchies_status",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_account_hierarchies_company_id_companies",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name="pk_account_hierarchies",
        ),
        sa.UniqueConstraint(
            "company_id",
            "id",
            name="uq_account_hierarchies_company_id_id",
        ),
        sa.UniqueConstraint(
            "company_id",
            "purpose_code",
            "hierarchy_name",
            name="uq_account_hierarchies_company_purpose_name",
        ),
        schema=CORE_SCHEMA,
    )

    op.create_index(
        "uq_account_hierarchies_active_primary_accounting",
        "account_hierarchies",
        ["company_id"],
        unique=True,
        schema=CORE_SCHEMA,
        postgresql_where=sa.text(
            "purpose_code = 'ACCOUNTING' "
            "AND status = 'ACTIVE' "
            "AND is_primary = true"
        ),
    )

    op.create_table(
        "account_groups",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("hierarchy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("group_name", sa.String(length=200), nullable=False),
        sa.Column("group_code", sa.String(length=50), nullable=True),
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
            "btrim(group_name) <> ''",
            name="ck_account_groups_name_not_blank",
        ),
        sa.CheckConstraint(
            "group_code IS NULL OR btrim(group_code) <> ''",
            name="ck_account_groups_code_not_blank",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_account_groups_status",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_account_groups_company_id_companies",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "hierarchy_id"],
            [
                "core.account_hierarchies.company_id",
                "core.account_hierarchies.id",
            ],
            name="fk_account_groups_company_hierarchy",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name="pk_account_groups",
        ),
        sa.UniqueConstraint(
            "company_id",
            "hierarchy_id",
            "group_name",
            name="uq_account_groups_company_hierarchy_name",
        ),
        schema=CORE_SCHEMA,
    )

    op.create_index(
        "uq_account_groups_company_hierarchy_code",
        "account_groups",
        ["company_id", "hierarchy_id", "group_code"],
        unique=True,
        schema=CORE_SCHEMA,
        postgresql_where=sa.text("group_code IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_account_groups_company_hierarchy_code",
        table_name="account_groups",
        schema=CORE_SCHEMA,
    )
    op.drop_table("account_groups", schema=CORE_SCHEMA)

    op.drop_index(
        "uq_account_hierarchies_active_primary_accounting",
        table_name="account_hierarchies",
        schema=CORE_SCHEMA,
    )
    op.drop_table("account_hierarchies", schema=CORE_SCHEMA)