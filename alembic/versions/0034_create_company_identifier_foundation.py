"""Create the approved Company legal-identifier foundation.

Revision ID: 0034_company_identifier_foundation
Revises: 0033_catalogue_base_gst_nature
Create Date: 2026-09-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0034_company_identifier_foundation"
down_revision: str | None = "0033_catalogue_base_gst_nature"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "company_identifier_types",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.CheckConstraint(
            "country_code ~ '^[A-Z]{2}$'",
            name="ck_company_identifier_types_country_code_format",
        ),
        sa.CheckConstraint(
            "code ~ '^[A-Z0-9]+(_[A-Z0-9]+)*$'",
            name="ck_company_identifier_types_code_format",
        ),
        sa.CheckConstraint(
            "btrim(name) <> ''",
            name="ck_company_identifier_types_name_not_blank",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_company_identifier_types_status",
        ),
        sa.ForeignKeyConstraint(
            ["country_code"],
            ["core.countries.code"],
            name="fk_company_identifier_types_country_code_countries",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_company_identifier_types"),
        sa.UniqueConstraint(
            "country_code",
            "code",
            name="uq_company_identifier_types_country_code_code",
        ),
        schema="core",
    )

    op.create_table(
        "company_identifiers",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "identifier_type_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("identifier_value", sa.String(length=255), nullable=False),
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
            "btrim(identifier_value) <> ''",
            name="ck_company_identifiers_value_not_blank",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_company_identifiers_status",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_company_identifiers_company_id_companies",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["identifier_type_id"],
            ["core.company_identifier_types.id"],
            name="fk_company_identifiers_type_id_types",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_company_identifiers"),
        sa.UniqueConstraint(
            "company_id",
            "identifier_type_id",
            name="uq_company_identifiers_company_id_type_id",
        ),
        schema="core",
    )

    op.create_table(
        "entity_type_identifier_rules",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("entity_type_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "identifier_type_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("requirement_level", sa.String(length=20), nullable=False),
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
            "requirement_level IN ('REQUIRED', 'OPTIONAL')",
            name="ck_entity_type_identifier_rules_requirement_level",
        ),
        sa.ForeignKeyConstraint(
            ["entity_type_id"],
            ["core.entity_types.id"],
            name="fk_entity_type_identifier_rules_entity_type_id_entity_types",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["identifier_type_id"],
            ["core.company_identifier_types.id"],
            name="fk_entity_type_identifier_rules_identifier_type_id_types",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_entity_type_identifier_rules"),
        sa.UniqueConstraint(
            "entity_type_id",
            "identifier_type_id",
            name="uq_entity_type_identifier_rules_entity_type_id_type_id",
        ),
        schema="core",
    )


def downgrade() -> None:
    op.drop_table("entity_type_identifier_rules", schema="core")
    op.drop_table("company_identifiers", schema="core")
    op.drop_table("company_identifier_types", schema="core")
