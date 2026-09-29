from datetime import datetime, time
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints

from skmc_erp.ar.reminder.model import ReminderScheduleRuleStatus

OptionalKey = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class ReminderPolicyPut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = False
    send_time: time | None = None
    default_template_key: OptionalKey | None = None


class ReminderPolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    enabled: bool
    send_time: time | None
    default_template_key: str | None
    created_at: datetime
    updated_at: datetime


class ReminderScheduleRuleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    offset_days: int
    template_key: OptionalKey | None = None


class ReminderScheduleRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    reminder_policy_id: UUID
    offset_days: int
    template_key: str | None
    status: ReminderScheduleRuleStatus
    created_at: datetime
    updated_at: datetime
