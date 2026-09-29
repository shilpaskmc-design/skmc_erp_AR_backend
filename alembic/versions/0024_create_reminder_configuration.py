"""Create reminder configuration.

Revision ID: 0024_reminder_configuration
Revises: 0023_email_delivery_configuration
Create Date: 2026-09-21
"""

from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0024_reminder_configuration"
down_revision: str | None = "0023_email_delivery_configuration"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reminder_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("send_time", sa.Time(timezone=False), nullable=True),
        sa.Column("default_template_key", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["core.companies.id"], name="fk_reminder_policies_company_id_companies", ondelete="NO ACTION"),
        sa.PrimaryKeyConstraint("id", name="pk_reminder_policies"),
        sa.UniqueConstraint("company_id", name="uq_reminder_policies_company_id"),
        schema="ar",
    )
    op.create_table(
        "reminder_schedule_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("reminder_policy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("offset_days", sa.Integer(), nullable=False),
        sa.Column("template_key", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="ck_reminder_schedule_rules_status"),
        sa.ForeignKeyConstraint(["reminder_policy_id"], ["ar.reminder_policies.id"], name="fk_reminder_schedule_rules_policy", ondelete="NO ACTION"),
        sa.PrimaryKeyConstraint("id", name="pk_reminder_schedule_rules"),
        sa.UniqueConstraint("reminder_policy_id", "offset_days", name="uq_reminder_schedule_rules_policy_offset"),
        schema="ar",
    )


def downgrade() -> None:
    op.drop_table("reminder_schedule_rules", schema="ar")
    op.drop_table("reminder_policies", schema="ar")
