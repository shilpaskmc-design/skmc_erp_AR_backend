from datetime import datetime, time
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKeyConstraint,
    Integer,
    PrimaryKeyConstraint,
    String,
    Time,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from skmc_erp.model_base import Base


class ReminderScheduleRuleStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class ReminderPolicy(Base):
    __tablename__ = "reminder_policies"
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id"], ["core.companies.id"],
            name="fk_reminder_policies_company_id_companies", ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_reminder_policies"),
        UniqueConstraint("company_id", name="uq_reminder_policies_company_id"),
        {"schema": "ar"},
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    company_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    send_time: Mapped[time | None] = mapped_column(Time(timezone=False), nullable=True)
    default_template_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))


class ReminderScheduleRule(Base):
    __tablename__ = "reminder_schedule_rules"
    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="ck_reminder_schedule_rules_status"),
        ForeignKeyConstraint(
            ["reminder_policy_id"], ["ar.reminder_policies.id"],
            name="fk_reminder_schedule_rules_policy", ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_reminder_schedule_rules"),
        UniqueConstraint("reminder_policy_id", "offset_days", name="uq_reminder_schedule_rules_policy_offset"),
        {"schema": "ar"},
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    reminder_policy_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    offset_days: Mapped[int] = mapped_column(Integer, nullable=False)
    template_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[ReminderScheduleRuleStatus] = mapped_column(
        Enum(ReminderScheduleRuleStatus, native_enum=False, create_constraint=False, validate_strings=True, length=20), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
