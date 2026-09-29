from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator

from skmc_erp.core.accounting.model import (
    AccountGroupStatus,
    AccountHierarchyPurpose,
    AccountHierarchyStatus,
    GlAccountStatus,
)


RequiredName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
]
OptionalCode = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=50),
]


class GlAccountCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_code: OptionalCode | None = None
    account_name: RequiredName
    valid_from: date
    valid_to: date | None = None

    @field_validator("valid_to")
    @classmethod
    def validate_dates(cls, valid_to: date | None, info) -> date | None:
        valid_from = info.data.get("valid_from")
        if valid_from and valid_to and valid_to < valid_from:
            raise ValueError("valid_to cannot be earlier than valid_from")
        return valid_to


class GlAccountUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_name: RequiredName | None = None
    valid_to: date | None = None


class GlAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    account_code: str | None
    account_name: str
    valid_from: date
    valid_to: date | None
    status: GlAccountStatus
    created_at: datetime
    updated_at: datetime


class AccountHierarchyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hierarchy_name: RequiredName


class AccountHierarchyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    hierarchy_name: str
    purpose_code: AccountHierarchyPurpose
    is_primary: bool
    status: AccountHierarchyStatus
    created_at: datetime
    updated_at: datetime


class AccountGroupCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    group_name: RequiredName
    group_code: OptionalCode | None = None


class AccountGroupUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    group_name: RequiredName | None = None
    # Code is immutable as per verified rules


class AccountGroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    hierarchy_id: UUID
    group_name: str
    group_code: str | None
    status: AccountGroupStatus
    created_at: datetime
    updated_at: datetime


class ReparentGroupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    new_parent_group_id: UUID
    effective_date: date


class MoveGroupToRootRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    effective_date: date


class AccountGroupRelationshipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    hierarchy_id: UUID
    child_group_id: UUID
    parent_group_id: UUID
    valid_from: date
    valid_to: date | None
    created_at: datetime
    updated_at: datetime


class GlAccountGroupAssignmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    account_group_id: UUID
    effective_date: date


class GlAccountRootAssignmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    effective_date: date


class GlAccountEndAssignmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    effective_date: date


class GlAccountGroupMappingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    hierarchy_id: UUID
    gl_account_id: UUID
    account_group_id: UUID | None
    valid_from: date
    valid_to: date | None
    created_at: datetime
    updated_at: datetime


class CompanyAccountingSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    default_receivable_gl_account_id: UUID


class CompanyAccountingSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    company_id: UUID
    default_receivable_gl_account_id: UUID
    updated_at: datetime
    updated_by: UUID | None
