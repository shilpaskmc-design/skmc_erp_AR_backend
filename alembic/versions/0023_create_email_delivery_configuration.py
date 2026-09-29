"""Create email-provider and invoice-delivery configuration.

Revision ID: 0023_email_delivery_configuration
Revises: 0022_file_document_presentation
Create Date: 2026-09-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0023_email_delivery_configuration"
down_revision: str | None = "0022_file_document_presentation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_companies_tenant_id_id",
        "companies",
        ["tenant_id", "id"],
        schema="core",
    )
    op.create_table(
        "email_provider_configs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider_type", sa.String(length=30), nullable=False),
        sa.Column("sender_identity", sa.String(length=320), nullable=False),
        sa.Column("secret_reference", sa.String(length=500), nullable=False),
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
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_email_provider_configs_status",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["core.tenants.id"],
            name="fk_email_provider_configs_tenant_id_tenants",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "company_id"],
            ["core.companies.tenant_id", "core.companies.id"],
            name="fk_email_provider_configs_tenant_company",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_email_provider_configs"),
        schema="core",
    )

    op.create_table(
        "company_invoice_delivery_settings",
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "automatic_sending_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "email_provider_config_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("sender_email", sa.String(length=320), nullable=True),
        sa.Column("reply_to_email", sa.String(length=320), nullable=True),
        sa.Column(
            "default_email_template_key",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column("default_cc", postgresql.ARRAY(sa.String(length=320)), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_company_invoice_delivery_settings_company_id_companies",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["email_provider_config_id"],
            ["core.email_provider_configs.id"],
            name="fk_company_invoice_delivery_settings_email_provider",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint(
            "company_id",
            name="pk_company_invoice_delivery_settings",
        ),
        schema="ar",
    )


def downgrade() -> None:
    op.drop_table("company_invoice_delivery_settings", schema="ar")
    op.drop_table("email_provider_configs", schema="core")
    op.drop_constraint(
        "uq_companies_tenant_id_id",
        "companies",
        type_="unique",
        schema="core",
    )
