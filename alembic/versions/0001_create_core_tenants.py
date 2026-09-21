"""Create the Core/Shared Tenant master.

Revision ID: 0001_create_core_tenants
Revises:
Create Date: 2026-09-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_create_core_tenants"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CORE_SCHEMA = "core"
TENANT_CODE_SEQUENCE = "tenant_code_seq"
TENANT_CODE_FUNCTION = "next_tenant_code"


def upgrade() -> None:
    op.execute(sa.schema.CreateSchema(CORE_SCHEMA))
    op.execute(
        sa.schema.CreateSequence(
            sa.Sequence(
                TENANT_CODE_SEQUENCE,
                schema=CORE_SCHEMA,
                start=1,
                increment=1,
            )
        )
    )
    op.execute(
        f"""
        CREATE FUNCTION {CORE_SCHEMA}.{TENANT_CODE_FUNCTION}()
        RETURNS VARCHAR(50)
        LANGUAGE SQL
        VOLATILE
        AS $$
            WITH generated AS (
                SELECT nextval('{CORE_SCHEMA}.{TENANT_CODE_SEQUENCE}') AS value
            )
            SELECT 'TEN' || lpad(
                value::text,
                GREATEST(6, length(value::text)),
                '0'
            )
            FROM generated
        $$
        """
    )

    op.create_table(
        "tenants",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "code",
            sa.String(length=50),
            server_default=sa.text(f"{CORE_SCHEMA}.{TENANT_CODE_FUNCTION}()"),
            nullable=False,
        ),
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
            "btrim(name) <> ''",
            name="ck_tenants_name_not_blank",
        ),
        sa.CheckConstraint(
            "btrim(code) <> ''",
            name="ck_tenants_code_not_blank",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'SUSPENDED', 'INACTIVE')",
            name="ck_tenants_status",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_tenants"),
        sa.UniqueConstraint("code", name="uq_tenants_code"),
        schema=CORE_SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("tenants", schema=CORE_SCHEMA)
    op.execute(
        f"DROP FUNCTION {CORE_SCHEMA}.{TENANT_CODE_FUNCTION}()"
    )
    op.execute(
        sa.schema.DropSequence(
            sa.Sequence(TENANT_CODE_SEQUENCE, schema=CORE_SCHEMA)
        )
    )
    op.execute(sa.schema.DropSchema(CORE_SCHEMA))
