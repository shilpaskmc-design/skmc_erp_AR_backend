"""Create effective-dated GL Account hierarchy placements.

Revision ID: 0018_gl_account_group_mappings
Revises: 0017_account_group_relationships
Create Date: 2026-09-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0018_gl_account_group_mappings"
down_revision: str | None = "0017_account_group_relationships"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CORE_SCHEMA = "core"


def upgrade() -> None:
    op.create_table(
        "gl_account_group_mappings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("hierarchy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gl_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_group_id", postgresql.UUID(as_uuid=True), nullable=True),
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
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_gl_account_group_mappings_valid_range",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_gl_account_group_mappings_company_id_companies",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "hierarchy_id"],
            [
                "core.account_hierarchies.company_id",
                "core.account_hierarchies.id",
            ],
            name="fk_gl_account_group_mappings_company_hierarchy",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "gl_account_id"],
            [
                "core.gl_accounts.company_id",
                "core.gl_accounts.id",
            ],
            name="fk_gl_account_group_mappings_company_gl_account",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "hierarchy_id", "account_group_id"],
            [
                "core.account_groups.company_id",
                "core.account_groups.hierarchy_id",
                "core.account_groups.id",
            ],
            name="fk_gl_account_group_mappings_company_hierarchy_group",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_gl_account_group_mappings"),
        postgresql.ExcludeConstraint(
            ("gl_account_id", "="),
            ("hierarchy_id", "="),
            (
                sa.func.daterange(
                    sa.column("valid_from"),
                    sa.column("valid_to"),
                    "[]",
                ),
                "&&",
            ),
            name="ex_gl_account_group_mappings_gl_hierarchy_period_overlap",
            using="gist",
        ),
        schema=CORE_SCHEMA,
    )

    op.create_index(
        "ix_gl_account_group_mappings_company_hierarchy_group_dates",
        "gl_account_group_mappings",
        [
            "company_id",
            "hierarchy_id",
            "account_group_id",
            "valid_from",
            "valid_to",
        ],
        unique=False,
        schema=CORE_SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_gl_account_group_mappings_company_hierarchy_group_dates",
        table_name="gl_account_group_mappings",
        schema=CORE_SCHEMA,
    )
    op.drop_table("gl_account_group_mappings", schema=CORE_SCHEMA)
