"""Create effective-dated Company legal-name history.

Revision ID: 0030_company_legal_name_history
Revises: 0029_document_numbering_configuration
Create Date: 2026-09-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0030_company_legal_name_history"
down_revision: str | None = "0029_document_numbering_configuration"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CORE_SCHEMA = "core"


def upgrade() -> None:
    op.create_table(
        "company_legal_name_versions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("legal_name", sa.String(length=255), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "btrim(legal_name) <> ''",
            name="ck_company_legal_name_versions_legal_name_not_blank",
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_company_legal_name_versions_date_order",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_company_legal_name_versions_company_id_companies",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name="pk_company_legal_name_versions",
        ),
        postgresql.ExcludeConstraint(
            ("company_id", "="),
            (
                sa.func.daterange(
                    sa.column("valid_from"),
                    sa.column("valid_to"),
                    "[]",
                ),
                "&&",
            ),
            name="ex_company_legal_name_versions_company_effective_range",
            using="gist",
        ),
        schema=CORE_SCHEMA,
    )
    op.create_index(
        "ix_company_legal_name_versions_company_valid_from",
        "company_legal_name_versions",
        ["company_id", "valid_from"],
        schema=CORE_SCHEMA,
    )
    op.create_index(
        "uq_company_legal_name_versions_open_company",
        "company_legal_name_versions",
        ["company_id"],
        unique=True,
        schema=CORE_SCHEMA,
        postgresql_where=sa.text("valid_to IS NULL"),
    )

    op.execute(
        sa.text(
            """
            INSERT INTO core.company_legal_name_versions (
                company_id,
                legal_name,
                valid_from,
                valid_to,
                created_at
            )
            SELECT
                id,
                legal_name,
                created_at::date,
                NULL,
                created_at
            FROM core.companies
            ORDER BY id
            """
        )
    )


def downgrade() -> None:
    op.drop_index(
        "uq_company_legal_name_versions_open_company",
        table_name="company_legal_name_versions",
        schema=CORE_SCHEMA,
    )
    op.drop_index(
        "ix_company_legal_name_versions_company_valid_from",
        table_name="company_legal_name_versions",
        schema=CORE_SCHEMA,
    )
    op.drop_table("company_legal_name_versions", schema=CORE_SCHEMA)
