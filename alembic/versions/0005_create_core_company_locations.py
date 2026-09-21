"""Create the Core/Shared Company Location foundation.

Revision ID: 0005_core_company_locations
Revises: 0004_core_geographic_masters
Create Date: 2026-09-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_core_company_locations"
down_revision: str | None = "0004_core_geographic_masters"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CORE_SCHEMA = "core"


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_country_subdivisions_country_code_code",
        "country_subdivisions",
        ["country_code", "code"],
        schema=CORE_SCHEMA,
    )

    op.create_table(
        "company_locations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("location_name", sa.String(length=150), nullable=False),
        sa.Column("address_line_1", sa.String(length=255), nullable=False),
        sa.Column("address_line_2", sa.String(length=255), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("district", sa.String(length=100), nullable=True),
        sa.Column("subdivision_code", sa.String(length=10), nullable=True),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("postal_code", sa.String(length=20), nullable=True),
        sa.Column(
            "is_registered_office",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "is_corporate_office",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "is_branch",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "is_billing_office",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "is_warehouse",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("other_purpose", sa.String(length=150), nullable=True),
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
            "btrim(location_name) <> ''",
            name="ck_company_locations_name_not_blank",
        ),
        sa.CheckConstraint(
            "btrim(address_line_1) <> ''",
            name="ck_company_locations_address_line_1_not_blank",
        ),
        sa.CheckConstraint(
            "address_line_2 IS NULL OR btrim(address_line_2) <> ''",
            name="ck_company_locations_address_line_2_not_blank",
        ),
        sa.CheckConstraint(
            "btrim(city) <> ''",
            name="ck_company_locations_city_not_blank",
        ),
        sa.CheckConstraint(
            "district IS NULL OR btrim(district) <> ''",
            name="ck_company_locations_district_not_blank",
        ),
        sa.CheckConstraint(
            "postal_code IS NULL OR btrim(postal_code) <> ''",
            name="ck_company_locations_postal_code_not_blank",
        ),
        sa.CheckConstraint(
            "other_purpose IS NULL OR btrim(other_purpose) <> ''",
            name="ck_company_locations_other_purpose_not_blank",
        ),
        sa.CheckConstraint(
            "is_registered_office OR is_corporate_office OR is_branch "
            "OR is_billing_office OR is_warehouse "
            "OR other_purpose IS NOT NULL",
            name="ck_company_locations_at_least_one_purpose",
        ),
        sa.CheckConstraint(
            "country_code ~ '^[A-Z]{2}$'",
            name="ck_company_locations_country_code_format",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_company_locations_status",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_company_locations_company_id_companies",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["country_code"],
            ["core.countries.code"],
            name="fk_company_locations_country_code_countries",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["country_code", "subdivision_code"],
            [
                "core.country_subdivisions.country_code",
                "core.country_subdivisions.code",
            ],
            name="fk_company_locations_country_subdivision",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_company_locations"),
        schema=CORE_SCHEMA,
    )
    op.create_index(
        "ix_company_locations_company_id",
        "company_locations",
        ["company_id"],
        unique=False,
        schema=CORE_SCHEMA,
    )
    op.create_index(
        "uq_company_locations_active_registered_office",
        "company_locations",
        ["company_id"],
        unique=True,
        schema=CORE_SCHEMA,
        postgresql_where=sa.text(
            "status = 'ACTIVE' AND is_registered_office"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_company_locations_active_registered_office",
        table_name="company_locations",
        schema=CORE_SCHEMA,
    )
    op.drop_index(
        "ix_company_locations_company_id",
        table_name="company_locations",
        schema=CORE_SCHEMA,
    )
    op.drop_table("company_locations", schema=CORE_SCHEMA)
    op.drop_constraint(
        "uq_country_subdivisions_country_code_code",
        "country_subdivisions",
        type_="unique",
        schema=CORE_SCHEMA,
    )
