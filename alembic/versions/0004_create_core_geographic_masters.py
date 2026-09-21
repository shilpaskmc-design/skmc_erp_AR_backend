"""Create the Core/Shared geographic reference masters.

Revision ID: 0004_core_geographic_masters
Revises: 0003_core_company_identity
Create Date: 2026-09-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_core_geographic_masters"
down_revision: str | None = "0003_core_company_identity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CORE_SCHEMA = "core"


def upgrade() -> None:
    op.create_table(
        "countries",
        sa.Column("code", sa.String(length=2), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
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
            "code ~ '^[A-Z]{2}$'",
            name="ck_countries_code_format",
        ),
        sa.CheckConstraint(
            "btrim(name) <> ''",
            name="ck_countries_name_not_blank",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_countries_status",
        ),
        sa.PrimaryKeyConstraint("code", name="pk_countries"),
        schema=CORE_SCHEMA,
    )

    op.create_table(
        "country_subdivisions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("code", sa.String(length=10), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("subdivision_type", sa.String(length=50), nullable=False),
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
            "code ~ '^[A-Z]{2}-[A-Z0-9]{1,3}$'",
            name="ck_country_subdivisions_code_format",
        ),
        sa.CheckConstraint(
            "left(code, 2) = country_code",
            name="ck_country_subdivisions_country_prefix",
        ),
        sa.CheckConstraint(
            "btrim(name) <> ''",
            name="ck_country_subdivisions_name_not_blank",
        ),
        sa.CheckConstraint(
            "subdivision_type ~ '^[A-Z]+(_[A-Z]+)*$'",
            name="ck_country_subdivisions_type_format",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_country_subdivisions_status",
        ),
        sa.ForeignKeyConstraint(
            ["country_code"],
            ["core.countries.code"],
            name="fk_country_subdivisions_country_code_countries",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_country_subdivisions"),
        sa.UniqueConstraint(
            "code",
            name="uq_country_subdivisions_code",
        ),
        schema=CORE_SCHEMA,
    )
    op.create_index(
        "ix_country_subdivisions_country_code",
        "country_subdivisions",
        ["country_code"],
        unique=False,
        schema=CORE_SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_country_subdivisions_country_code",
        table_name="country_subdivisions",
        schema=CORE_SCHEMA,
    )
    op.drop_table("country_subdivisions", schema=CORE_SCHEMA)
    op.drop_table("countries", schema=CORE_SCHEMA)
