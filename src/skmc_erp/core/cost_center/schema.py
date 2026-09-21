from datetime import datetime
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

from skmc_erp.core.cost_center.model import CostCenterStatus, TeamStatus


CostCenterName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=150),
]
CostCenterCode = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=50),
]


class CompanyCostCenterSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cost_center_reporting_enabled: bool
    business_segment_enabled: bool
    team_enabled: bool
    location_enabled: bool

    @model_validator(mode="after")
    def validate_disabled_bases(self) -> Self:
        if not self.cost_center_reporting_enabled and (
            self.business_segment_enabled
            or self.team_enabled
            or self.location_enabled
        ):
            raise ValueError(
                "reporting bases cannot be enabled when Cost Center "
                "reporting is disabled"
            )
        return self


class CompanyCostCenterSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    company_id: UUID
    cost_center_reporting_enabled: bool
    business_segment_enabled: bool
    team_enabled: bool
    location_enabled: bool
    created_at: datetime
    updated_at: datetime


class BusinessSegmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: CostCenterName
    code: CostCenterCode | None = None


class BusinessSegmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    name: str
    code: str | None
    status: CostCenterStatus
    created_at: datetime
    updated_at: datetime


class CostCenterTeamCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: CostCenterName
    code: CostCenterCode | None = None


class CostCenterTeamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    name: str
    code: str | None
    status: CostCenterStatus
    created_at: datetime
    updated_at: datetime


class TeamCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: CostCenterName


class TeamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    cost_center_team_id: UUID | None
    name: str
    status: TeamStatus
    created_at: datetime
    updated_at: datetime


class LocationCostCenterCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: CostCenterName
    code: CostCenterCode | None = None


class LocationCostCenterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    name: str
    code: str | None
    status: CostCenterStatus
    created_at: datetime
    updated_at: datetime
