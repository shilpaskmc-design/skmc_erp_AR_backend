from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from skmc_erp.ar.fx.model import FXPolicyPurpose, FXPolicyRateType, FXPolicyStatus


class FXPolicyPut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_rate_type: FXPolicyRateType
    allow_user_fixed_override: bool = False
    reason_required_for_override: bool = False
    status: FXPolicyStatus = FXPolicyStatus.ACTIVE

    @model_validator(mode="after")
    def validate_override(self) -> "FXPolicyPut":
        if self.reason_required_for_override and not self.allow_user_fixed_override:
            raise ValueError("reason_required_for_override requires allow_user_fixed_override")
        return self


class FXPolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    purpose: FXPolicyPurpose
    default_rate_type: FXPolicyRateType
    allow_user_fixed_override: bool
    reason_required_for_override: bool
    status: FXPolicyStatus
    created_at: datetime
    updated_at: datetime
