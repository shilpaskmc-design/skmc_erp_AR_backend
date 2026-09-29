"""Create stored files and document-presentation configuration.

Revision ID: 0022_file_document_presentation
Revises: 0021_company_luts
Create Date: 2026-09-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0022_file_document_presentation"
down_revision: str | None = "0021_company_luts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> tuple[sa.Column, sa.Column]:
    return (
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
    )


def upgrade() -> None:
    op.create_table(
        "stored_files",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("object_key", sa.String(length=1024), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "size_bytes >= 0",
            name="ck_stored_files_size_bytes_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_stored_files_company_id_companies",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_stored_files"),
        sa.UniqueConstraint("object_key", name="uq_stored_files_object_key"),
        sa.UniqueConstraint(
            "company_id",
            "id",
            name="uq_stored_files_company_id_id",
        ),
        schema="core",
    )

    op.create_table(
        "company_document_branding",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("logo_file_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "signature_file_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
        sa.Column("stamp_file_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("header_text", sa.Text(), nullable=True),
        sa.Column("footer_text", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_company_document_branding_status",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_company_document_branding_company_id_companies",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "logo_file_id"],
            ["core.stored_files.company_id", "core.stored_files.id"],
            name="fk_company_document_branding_company_logo_file",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "signature_file_id"],
            ["core.stored_files.company_id", "core.stored_files.id"],
            name="fk_company_document_branding_company_signature_file",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "stamp_file_id"],
            ["core.stored_files.company_id", "core.stored_files.id"],
            name="fk_company_document_branding_company_stamp_file",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_company_document_branding"),
        sa.UniqueConstraint(
            "company_id",
            "id",
            name="uq_company_document_branding_company_id_id",
        ),
        schema="ar",
    )

    op.create_table(
        "company_document_templates",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_type", sa.String(length=10), nullable=False),
        sa.Column("branding_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("template_key", sa.String(length=100), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("show_logo", sa.Boolean(), nullable=False),
        sa.Column("show_bank_details", sa.Boolean(), nullable=False),
        sa.Column("show_signature", sa.Boolean(), nullable=False),
        sa.Column("show_hsn_sac", sa.Boolean(), nullable=False),
        sa.Column("show_customer_reference", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "document_type IN ('PI', 'TI', 'CN', 'DN')",
            name="ck_company_document_templates_document_type",
        ),
        sa.CheckConstraint(
            "version_no >= 1",
            name="ck_company_document_templates_version_no_positive",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_company_document_templates_status",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_company_document_templates_company_id_companies",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "branding_id"],
            [
                "ar.company_document_branding.company_id",
                "ar.company_document_branding.id",
            ],
            name="fk_company_document_templates_company_branding",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_company_document_templates"),
        sa.UniqueConstraint(
            "company_id",
            "document_type",
            "template_key",
            "version_no",
            name="uq_company_document_templates_company_type_key_version",
        ),
        schema="ar",
    )


def downgrade() -> None:
    op.drop_table("company_document_templates", schema="ar")
    op.drop_table("company_document_branding", schema="ar")
    op.drop_table("stored_files", schema="core")
