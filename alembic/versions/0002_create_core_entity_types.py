"""Create the Core/Shared Entity Type master.

Revision ID: 0002_create_core_entity_types
Revises: 0001_create_core_tenants
Create Date: 2026-09-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_create_core_entity_types"
down_revision: str | None = "0001_create_core_tenants"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CORE_SCHEMA = "core"


def upgrade() -> None:
    op.create_table(
        "entity_types",
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
            name="ck_entity_types_country_code_format",
        ),
        sa.CheckConstraint(
            "btrim(code) <> ''",
            name="ck_entity_types_code_not_blank",
        ),
        sa.CheckConstraint(
            r"code ~ '^[A-Z0-9]+(?\:_[A-Z0-9]+)*$'",
            name="ck_entity_types_code_format",
        ),
        sa.CheckConstraint(
            "btrim(name) <> ''",
            name="ck_entity_types_name_not_blank",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_entity_types_status",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_entity_types"),
        sa.UniqueConstraint(
            "country_code",
            "code",
            name="uq_entity_types_country_code_code",
        ),
        schema=CORE_SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("entity_types", schema=CORE_SCHEMA)
