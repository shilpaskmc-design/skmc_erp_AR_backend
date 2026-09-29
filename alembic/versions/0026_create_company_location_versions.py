"""Create effective-dated Company Location address versions.

Revision ID: 0026_company_location_versions
Revises: 0025_company_access_foundation
Create Date: 2026-09-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0026_company_location_versions"
down_revision: str | None = "0025_company_access_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CORE_SCHEMA = "core"


def upgrade() -> None:
    op.create_table(
        "company_location_versions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "company_location_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("address_line_1", sa.String(length=255), nullable=False),
        sa.Column("address_line_2", sa.String(length=255), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("district", sa.String(length=100), nullable=True),
        sa.Column("subdivision_code", sa.String(length=10), nullable=True),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("postal_code", sa.String(length=20), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "btrim(address_line_1) <> ''",
            name="ck_company_location_versions_address_line_1_not_blank",
        ),
        sa.CheckConstraint(
            "address_line_2 IS NULL OR btrim(address_line_2) <> ''",
            name="ck_company_location_versions_address_line_2_not_blank",
        ),
        sa.CheckConstraint(
            "btrim(city) <> ''",
            name="ck_company_location_versions_city_not_blank",
        ),
        sa.CheckConstraint(
            "district IS NULL OR btrim(district) <> ''",
            name="ck_company_location_versions_district_not_blank",
        ),
        sa.CheckConstraint(
            "postal_code IS NULL OR btrim(postal_code) <> ''",
            name="ck_company_location_versions_postal_code_not_blank",
        ),
        sa.CheckConstraint(
            "country_code ~ '^[A-Z]{2}$'",
            name="ck_company_location_versions_country_code_format",
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_company_location_versions_date_order",
        ),
        sa.ForeignKeyConstraint(
            ["company_location_id"],
            ["core.company_locations.id"],
            name="fk_company_location_versions_location_id_locations",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["country_code"],
            ["core.countries.code"],
            name="fk_company_location_versions_country_code_countries",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["country_code", "subdivision_code"],
            [
                "core.country_subdivisions.country_code",
                "core.country_subdivisions.code",
            ],
            name="fk_company_location_versions_country_subdivision",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_company_location_versions"),
        postgresql.ExcludeConstraint(
            ("company_location_id", "="),
            (
                sa.func.daterange(
                    sa.column("valid_from"),
                    sa.column("valid_to"),
                    "[]",
                ),
                "&&",
            ),
            name="ex_company_location_versions_location_effective_range",
            using="gist",
        ),
        schema=CORE_SCHEMA,
    )
    op.create_index(
        "ix_company_location_versions_location_valid_from",
        "company_location_versions",
        ["company_location_id", "valid_from"],
        schema=CORE_SCHEMA,
    )
    op.create_index(
        "uq_company_location_versions_open_location",
        "company_location_versions",
        ["company_location_id"],
        unique=True,
        schema=CORE_SCHEMA,
        postgresql_where=sa.text("valid_to IS NULL"),
    )

    op.execute(
        sa.text(
            """
            INSERT INTO core.company_location_versions (
                company_location_id,
                address_line_1,
                address_line_2,
                city,
                district,
                subdivision_code,
                country_code,
                postal_code,
                valid_from,
                valid_to,
                created_at
            )
            SELECT
                id,
                address_line_1,
                address_line_2,
                city,
                district,
                subdivision_code,
                country_code,
                postal_code,
                created_at::date,
                NULL,
                created_at
            FROM core.company_locations
            ORDER BY id
            """
        )
    )


def downgrade() -> None:
    op.drop_index(
        "uq_company_location_versions_open_location",
        table_name="company_location_versions",
        schema=CORE_SCHEMA,
    )
    op.drop_index(
        "ix_company_location_versions_location_valid_from",
        table_name="company_location_versions",
        schema=CORE_SCHEMA,
    )
    op.drop_table("company_location_versions", schema=CORE_SCHEMA)
