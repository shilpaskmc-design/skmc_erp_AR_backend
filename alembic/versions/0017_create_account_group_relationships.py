"""Create effective-dated Account Group relationships.

Revision ID: 0017_account_group_relationships
Revises: 0016_account_hierarchies_groups
Create Date: 2026-09-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0017_account_group_relationships"
down_revision: str | None = "0016_account_hierarchies_groups"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CORE_SCHEMA = "core"


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_account_groups_company_hierarchy_id",
        "account_groups",
        ["company_id", "hierarchy_id", "id"],
        schema=CORE_SCHEMA,
    )

    op.create_table(
        "account_group_relationships",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("hierarchy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("child_group_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_group_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
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
            "child_group_id <> parent_group_id",
            name="ck_account_group_relationships_not_self_parent",
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_account_group_relationships_valid_range",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_account_group_relationships_company_id_companies",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "hierarchy_id"],
            [
                "core.account_hierarchies.company_id",
                "core.account_hierarchies.id",
            ],
            name="fk_account_group_relationships_company_hierarchy",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "hierarchy_id", "child_group_id"],
            [
                "core.account_groups.company_id",
                "core.account_groups.hierarchy_id",
                "core.account_groups.id",
            ],
            name="fk_account_group_relationships_child_group",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "hierarchy_id", "parent_group_id"],
            [
                "core.account_groups.company_id",
                "core.account_groups.hierarchy_id",
                "core.account_groups.id",
            ],
            name="fk_account_group_relationships_parent_group",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_account_group_relationships"),
        postgresql.ExcludeConstraint(
            ("child_group_id", "="),
            (
                sa.func.daterange(
                    sa.column("valid_from"),
                    sa.column("valid_to"),
                    "[]",
                ),
                "&&",
            ),
            name="ex_account_group_relationships_child_period_overlap",
            using="gist",
        ),
        schema=CORE_SCHEMA,
    )

    op.create_index(
        "ix_account_group_relationships_company_hierarchy_parent_dates",
        "account_group_relationships",
        [
            "company_id",
            "hierarchy_id",
            "parent_group_id",
            "valid_from",
            "valid_to",
        ],
        unique=False,
        schema=CORE_SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_account_group_relationships_company_hierarchy_parent_dates",
        table_name="account_group_relationships",
        schema=CORE_SCHEMA,
    )
    op.drop_table("account_group_relationships", schema=CORE_SCHEMA)

    op.drop_constraint(
        "uq_account_groups_company_hierarchy_id",
        "account_groups",
        type_="unique",
        schema=CORE_SCHEMA,
    )
