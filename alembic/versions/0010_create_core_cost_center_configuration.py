"""Create Company Cost Center configuration.

Revision ID: 0010_cost_center_configuration
Revises: 0009_catalogue
Create Date: 2026-09-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010_cost_center_configuration"
down_revision: str | None = "0009_catalogue"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CORE_SCHEMA = "core"
AR_SCHEMA = "ar"


def _id_column() -> sa.Column:
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        server_default=sa.text("gen_random_uuid()"),
        nullable=False,
    )


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


def _create_reporting_bucket_table(table_name: str) -> None:
    op.create_table(
        table_name,
        _id_column(),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "btrim(name) <> ''",
            name=f"ck_{table_name}_name_not_blank",
        ),
        sa.CheckConstraint(
            "code IS NULL OR btrim(code) <> ''",
            name=f"ck_{table_name}_code_not_blank",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name=f"ck_{table_name}_status",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name=f"fk_{table_name}_company_id_companies",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name=f"pk_{table_name}"),
        sa.UniqueConstraint(
            "company_id",
            "name",
            name=f"uq_{table_name}_company_id_name",
        ),
        sa.UniqueConstraint(
            "company_id",
            "id",
            name=f"uq_{table_name}_company_id_id",
        ),
        schema=CORE_SCHEMA,
    )
    op.create_index(
        f"uq_{table_name}_company_id_code",
        table_name,
        ["company_id", "code"],
        unique=True,
        schema=CORE_SCHEMA,
        postgresql_where=sa.text("code IS NOT NULL"),
    )


def upgrade() -> None:
    for table_name in (
        "cost_center_locations",
        "cost_center_business_segments",
        "cost_center_teams",
    ):
        _create_reporting_bucket_table(table_name)

    op.create_table(
        "teams",
        _id_column(),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "cost_center_team_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("btrim(name) <> ''", name="ck_teams_name_not_blank"),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_teams_status",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_teams_company_id_companies",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "cost_center_team_id"],
            ["core.cost_center_teams.company_id", "core.cost_center_teams.id"],
            name="fk_teams_company_cost_center_team",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_teams"),
        sa.UniqueConstraint(
            "company_id",
            "name",
            name="uq_teams_company_id_name",
        ),
        schema=CORE_SCHEMA,
    )
    op.create_table(
        "company_cost_center_settings",
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "cost_center_reporting_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "business_segment_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "team_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "location_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        *_timestamps(),
        sa.CheckConstraint(
            "cost_center_reporting_enabled OR "
            "(NOT business_segment_enabled AND NOT team_enabled "
            "AND NOT location_enabled)",
            name="ck_company_cost_center_settings_disabled_bases",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_company_cost_center_settings_company_id_companies",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint(
            "company_id",
            name="pk_company_cost_center_settings",
        ),
        schema=CORE_SCHEMA,
    )

    op.add_column(
        "service_types",
        sa.Column(
            "business_segment_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        schema=AR_SCHEMA,
    )
    op.create_foreign_key(
        "fk_service_types_company_business_segment",
        "service_types",
        "cost_center_business_segments",
        ["company_id", "business_segment_id"],
        ["company_id", "id"],
        source_schema=AR_SCHEMA,
        referent_schema=CORE_SCHEMA,
        ondelete="NO ACTION",
    )

    op.add_column(
        "skus",
        sa.Column(
            "business_segment_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        schema=AR_SCHEMA,
    )
    op.create_foreign_key(
        "fk_skus_company_business_segment",
        "skus",
        "cost_center_business_segments",
        ["company_id", "business_segment_id"],
        ["company_id", "id"],
        source_schema=AR_SCHEMA,
        referent_schema=CORE_SCHEMA,
        ondelete="NO ACTION",
    )

    op.add_column(
        "company_locations",
        sa.Column(
            "cost_center_location_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        schema=CORE_SCHEMA,
    )
    op.create_foreign_key(
        "fk_company_locations_company_cost_center_location",
        "company_locations",
        "cost_center_locations",
        ["company_id", "cost_center_location_id"],
        ["company_id", "id"],
        source_schema=CORE_SCHEMA,
        referent_schema=CORE_SCHEMA,
        ondelete="NO ACTION",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_company_locations_company_cost_center_location",
        "company_locations",
        schema=CORE_SCHEMA,
        type_="foreignkey",
    )
    op.drop_column(
        "company_locations",
        "cost_center_location_id",
        schema=CORE_SCHEMA,
    )

    op.drop_constraint(
        "fk_skus_company_business_segment",
        "skus",
        schema=AR_SCHEMA,
        type_="foreignkey",
    )
    op.drop_column("skus", "business_segment_id", schema=AR_SCHEMA)

    op.drop_constraint(
        "fk_service_types_company_business_segment",
        "service_types",
        schema=AR_SCHEMA,
        type_="foreignkey",
    )
    op.drop_column("service_types", "business_segment_id", schema=AR_SCHEMA)

    op.drop_table("company_cost_center_settings", schema=CORE_SCHEMA)
    op.drop_table("teams", schema=CORE_SCHEMA)
    for table_name in (
        "cost_center_teams",
        "cost_center_business_segments",
        "cost_center_locations",
    ):
        op.drop_index(
            f"uq_{table_name}_company_id_code",
            table_name=table_name,
            schema=CORE_SCHEMA,
        )
        op.drop_table(table_name, schema=CORE_SCHEMA)
