"""Create AR document numbering configuration.

Revision ID: 0029_document_numbering_configuration
Revises: 0028_revenue_gl_mapping_enhancement
Create Date: 2026-09-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0029_document_numbering_configuration"
down_revision: str | None = "0028_revenue_gl_mapping_enhancement"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_sequences",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "financial_year_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("document_type", sa.String(length=10), nullable=False),
        sa.Column("series_name", sa.String(length=100), nullable=False),
        sa.Column("format", sa.String(length=255), nullable=False),
        sa.Column("prefix", sa.String(length=50), nullable=True),
        sa.Column("start_number", sa.BigInteger(), nullable=False),
        sa.Column("next_number", sa.BigInteger(), nullable=False),
        sa.Column("padding", sa.SmallInteger(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "document_type IN ('PI', 'TI', 'CN', 'DN')",
            name="ck_document_sequences_document_type",
        ),
        sa.CheckConstraint(
            "start_number >= 1",
            name="ck_document_sequences_start_number",
        ),
        sa.CheckConstraint(
            "next_number >= start_number",
            name="ck_document_sequences_next_number",
        ),
        sa.CheckConstraint(
            "padding >= 1",
            name="ck_document_sequences_padding",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_document_sequences_status",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_document_sequences_company_id_companies",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "financial_year_id"],
            ["core.financial_years.company_id", "core.financial_years.id"],
            name="fk_document_sequences_company_financial_year",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_document_sequences"),
        sa.UniqueConstraint(
            "company_id",
            "financial_year_id",
            "document_type",
            "series_name",
            name="uq_document_sequences_company_fy_type_name",
        ),
        schema="ar",
    )

    op.create_table(
        "document_sequence_conditions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "document_sequence_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("condition_type", sa.String(length=40), nullable=False),
        sa.Column("operator", sa.String(length=20), nullable=False),
        sa.Column("condition_value", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_sequence_id"],
            ["ar.document_sequences.id"],
            name="fk_document_sequence_conditions_sequence_id_sequences",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name="pk_document_sequence_conditions",
        ),
        schema="ar",
    )


def downgrade() -> None:
    op.drop_table("document_sequence_conditions", schema="ar")
    op.drop_table("document_sequences", schema="ar")
