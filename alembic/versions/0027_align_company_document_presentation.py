"""Align billing document presentation to one Company-wide selection.

Revision ID: 0027_company_document_presentation
Revises: 0026_company_location_versions
Create Date: 2026-09-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0027_company_document_presentation"
down_revision: str | None = "0026_company_location_versions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

AR_SCHEMA = "ar"

SHOW_COLUMNS = (
    "show_logo",
    "show_bank_details",
    "show_signature",
    "show_hsn_sac",
    "show_customer_reference",
)


def upgrade() -> None:
    op.drop_constraint(
        "uq_company_document_templates_company_type_key_version",
        "company_document_templates",
        type_="unique",
        schema=AR_SCHEMA,
    )
    op.execute(
        sa.text(
            """
            UPDATE ar.company_document_templates
            SET status = 'INACTIVE', updated_at = CURRENT_TIMESTAMP
            WHERE status = 'ACTIVE'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE ar.company_document_branding
            SET status = 'INACTIVE', updated_at = CURRENT_TIMESTAMP
            WHERE status = 'ACTIVE'
            """
        )
    )
    op.execute(
        sa.text(
            """
            WITH ordered AS (
                SELECT id,
                       row_number() OVER (
                           PARTITION BY company_id
                           ORDER BY created_at, id
                       ) AS company_version_no
                FROM ar.company_document_templates
            )
            UPDATE ar.company_document_templates AS templates
            SET version_no = ordered.company_version_no
            FROM ordered
            WHERE templates.id = ordered.id
            """
        )
    )

    op.alter_column(
        "company_document_templates",
        "document_type",
        existing_type=sa.String(length=10),
        nullable=True,
        schema=AR_SCHEMA,
    )
    for column_name in SHOW_COLUMNS:
        op.alter_column(
            "company_document_templates",
            column_name,
            existing_type=sa.Boolean(),
            nullable=True,
            schema=AR_SCHEMA,
        )

    op.create_check_constraint(
        "ck_company_document_templates_active_company_wide",
        "company_document_templates",
        "status <> 'ACTIVE' OR document_type IS NULL",
        schema=AR_SCHEMA,
    )
    op.create_unique_constraint(
        "uq_company_document_templates_company_version",
        "company_document_templates",
        ["company_id", "version_no"],
        schema=AR_SCHEMA,
    )
    op.create_index(
        "uq_company_document_templates_active_company",
        "company_document_templates",
        ["company_id"],
        unique=True,
        schema=AR_SCHEMA,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )
    op.create_index(
        "uq_company_document_branding_active_company",
        "company_document_branding",
        ["company_id"],
        unique=True,
        schema=AR_SCHEMA,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_company_document_branding_active_company",
        table_name="company_document_branding",
        schema=AR_SCHEMA,
    )
    op.drop_index(
        "uq_company_document_templates_active_company",
        table_name="company_document_templates",
        schema=AR_SCHEMA,
    )
    op.drop_constraint(
        "uq_company_document_templates_company_version",
        "company_document_templates",
        type_="unique",
        schema=AR_SCHEMA,
    )
    op.drop_constraint(
        "ck_company_document_templates_active_company_wide",
        "company_document_templates",
        type_="check",
        schema=AR_SCHEMA,
    )

    op.execute(
        sa.text(
            """
            UPDATE ar.company_document_templates
            SET document_type = COALESCE(document_type, 'TI'),
                show_logo = COALESCE(show_logo, false),
                show_bank_details = COALESCE(show_bank_details, false),
                show_signature = COALESCE(show_signature, false),
                show_hsn_sac = COALESCE(show_hsn_sac, false),
                show_customer_reference = COALESCE(
                    show_customer_reference, false
                )
            """
        )
    )
    op.alter_column(
        "company_document_templates",
        "document_type",
        existing_type=sa.String(length=10),
        nullable=False,
        schema=AR_SCHEMA,
    )
    for column_name in SHOW_COLUMNS:
        op.alter_column(
            "company_document_templates",
            column_name,
            existing_type=sa.Boolean(),
            nullable=False,
            schema=AR_SCHEMA,
        )
    op.create_unique_constraint(
        "uq_company_document_templates_company_type_key_version",
        "company_document_templates",
        ["company_id", "document_type", "template_key", "version_no"],
        schema=AR_SCHEMA,
    )
