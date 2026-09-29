"""Create Company access foundation.

Revision ID: 0025_company_access_foundation
Revises: 0024_reminder_configuration
Create Date: 2026-09-21
"""

from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0025_company_access_foundation"
down_revision: str | None = "0024_reminder_configuration"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "company_user_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_subject_id", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="ck_company_user_memberships_status"),
        sa.ForeignKeyConstraint(["company_id"], ["core.companies.id"], name="fk_company_user_memberships_company_id_companies", ondelete="NO ACTION"),
        sa.PrimaryKeyConstraint("id", name="pk_company_user_memberships"),
        sa.UniqueConstraint("company_id", "user_subject_id", name="uq_company_user_memberships_company_user"),
        schema="core",
    )
    op.create_index("idx_company_user_memberships_active_user", "company_user_memberships", ["user_subject_id", "company_id"], unique=False, schema="core", postgresql_where=sa.text("status = 'ACTIVE'"))


def downgrade() -> None:
    op.drop_index("idx_company_user_memberships_active_user", table_name="company_user_memberships", schema="core")
    op.drop_table("company_user_memberships", schema="core")
