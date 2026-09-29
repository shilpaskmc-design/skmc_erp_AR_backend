from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# --- Tax GL Account Mappings ---

class TaxGlAccountMappingBase(BaseModel):
    tax_statutory_code_id: UUID
    gl_account_id: UUID
    valid_from: date


class TaxGlAccountMappingCreate(TaxGlAccountMappingBase):
    pass


class TaxGlAccountMappingRemap(BaseModel):
    gl_account_id: UUID
    valid_from: date


class TaxGlAccountMappingEnd(BaseModel):
    valid_to: date


class TaxGlAccountMappingResponse(TaxGlAccountMappingBase):
    id: UUID
    company_id: UUID
    valid_to: date | None = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Revenue GL Mappings ---

APPROVED_SUPPLY_TYPES = {"B2B", "B2C", "EXPWOP", "EXPWP", "SEZWOP", "SEZWP"}


class RevenueGlMappingCreate(BaseModel):
    service_type_id: UUID | None = None
    sku_id: UUID | None = None
    supply_type_code: str | None = Field(default=None, max_length=30)
    company_location_id: UUID | None = None
    gl_account_id: UUID
    valid_from: date
    valid_to: date | None = None


class RevenueGlMappingEnd(BaseModel):
    valid_to: date


class RevenueGlMappingResponse(BaseModel):
    id: UUID
    company_id: UUID
    service_type_id: UUID | None = None
    sku_id: UUID | None = None
    supply_type_code: str | None = None
    company_location_id: UUID | None = None
    gl_account_id: UUID
    valid_from: date
    valid_to: date | None = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
