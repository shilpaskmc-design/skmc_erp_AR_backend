"""Create the Company GST Registration foundation.

Revision ID: 0007_core_company_gst_registrations
Revises: 0006_core_financial_years
Create Date: 2026-09-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_core_company_gst_registrations"
down_revision: str | None = "0006_core_financial_years"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CORE_SCHEMA = "core"


def upgrade() -> None:
    op.add_column(
        "country_subdivisions",
        sa.Column("gst_state_code", sa.String(length=2), nullable=True),
        schema=CORE_SCHEMA,
    )
    op.create_check_constraint(
        "ck_country_subdivisions_gst_state_code_format",
        "country_subdivisions",
        "gst_state_code IS NULL OR gst_state_code ~ '^[0-9]{2}$'",
        schema=CORE_SCHEMA,
    )
    op.create_index(
        "uq_country_subdivisions_country_gst_state_code",
        "country_subdivisions",
        ["country_code", "gst_state_code"],
        unique=True,
        schema=CORE_SCHEMA,
        postgresql_where=sa.text("gst_state_code IS NOT NULL"),
    )

    op.create_table(
        "gst_registration_types",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
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
            name="ck_gst_registration_types_status",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_gst_registration_types"),
        sa.UniqueConstraint(
            "code",
            name="uq_gst_registration_types_code",
        ),
        schema=CORE_SCHEMA,
    )

    op.create_table(
        "company_gst_registrations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gstin", sa.String(length=15), nullable=False),
        sa.Column(
            "registered_legal_name",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "gst_registration_type_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("subdivision_code", sa.String(length=10), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=True),
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
            "gstin ~ "
            "'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$'",
            name="ck_company_gst_registrations_gstin_format",
        ),
        sa.CheckConstraint(
            "registered_legal_name IS NULL "
            "OR btrim(registered_legal_name) <> ''",
            name="ck_company_gst_registrations_legal_name_not_blank",
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from",
            name="ck_company_gst_registrations_date_order",
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'ACTIVE', 'INACTIVE')",
            name="ck_company_gst_registrations_status",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_company_gst_registrations_company_id_companies",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["gst_registration_type_id"],
            ["core.gst_registration_types.id"],
            name="fk_company_gst_registrations_type_id_types",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["subdivision_code"],
            ["core.country_subdivisions.code"],
            name="fk_company_gst_registrations_subdivision_code",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_company_gst_registrations"),
        sa.UniqueConstraint(
            "gstin",
            name="uq_company_gst_registrations_gstin",
        ),
        sa.UniqueConstraint(
            "company_id",
            "id",
            "subdivision_code",
            name="uq_company_gst_registrations_company_id_id_subdivision",
        ),
        schema=CORE_SCHEMA,
    )
    op.create_index(
        "ix_company_gst_registrations_company_id",
        "company_gst_registrations",
        ["company_id"],
        schema=CORE_SCHEMA,
    )
    op.create_index(
        "uq_company_gst_registrations_active_company_subdivision",
        "company_gst_registrations",
        ["company_id", "subdivision_code"],
        unique=True,
        schema=CORE_SCHEMA,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )

    op.add_column(
        "company_locations",
        sa.Column(
            "gst_registration_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        schema=CORE_SCHEMA,
    )
    op.create_check_constraint(
        "ck_company_locations_gst_requires_subdivision",
        "company_locations",
        "gst_registration_id IS NULL OR subdivision_code IS NOT NULL",
        schema=CORE_SCHEMA,
    )
    op.create_foreign_key(
        "fk_company_locations_gst_registration_jurisdiction",
        "company_locations",
        "company_gst_registrations",
        ["company_id", "gst_registration_id", "subdivision_code"],
        ["company_id", "id", "subdivision_code"],
        source_schema=CORE_SCHEMA,
        referent_schema=CORE_SCHEMA,
        ondelete="NO ACTION",
    )
    op.create_index(
        "ix_company_locations_gst_registration_id",
        "company_locations",
        ["gst_registration_id"],
        schema=CORE_SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_company_locations_gst_registration_id",
        table_name="company_locations",
        schema=CORE_SCHEMA,
    )
    op.drop_constraint(
        "fk_company_locations_gst_registration_jurisdiction",
        "company_locations",
        type_="foreignkey",
        schema=CORE_SCHEMA,
    )
    op.drop_constraint(
        "ck_company_locations_gst_requires_subdivision",
        "company_locations",
        type_="check",
        schema=CORE_SCHEMA,
    )
    op.drop_column(
        "company_locations",
        "gst_registration_id",
        schema=CORE_SCHEMA,
    )

    op.drop_index(
        "uq_company_gst_registrations_active_company_subdivision",
        table_name="company_gst_registrations",
        schema=CORE_SCHEMA,
    )
    op.drop_index(
        "ix_company_gst_registrations_company_id",
        table_name="company_gst_registrations",
        schema=CORE_SCHEMA,
    )
    op.drop_table("company_gst_registrations", schema=CORE_SCHEMA)
    op.drop_table("gst_registration_types", schema=CORE_SCHEMA)

    op.drop_index(
        "uq_country_subdivisions_country_gst_state_code",
        table_name="country_subdivisions",
        schema=CORE_SCHEMA,
    )
    op.drop_constraint(
        "ck_country_subdivisions_gst_state_code_format",
        "country_subdivisions",
        type_="check",
        schema=CORE_SCHEMA,
    )
    op.drop_column(
        "country_subdivisions",
        "gst_state_code",
        schema=CORE_SCHEMA,
    )
