from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints

LutReferenceText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]


class CompanyLutBase(BaseModel):
    gst_registration_id: UUID
    financial_year_id: UUID
    lut_reference: LutReferenceText
    valid_from: date
    valid_to: date | None = None


class CompanyLutCreate(CompanyLutBase):
    pass


class CompanyLutResponse(CompanyLutBase):
    id: UUID
    company_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
