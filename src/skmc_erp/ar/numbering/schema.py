from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from skmc_erp.ar.numbering.model import DocumentSequenceStatus, DocumentType


SeriesName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]
NumberFormat = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]
OptionalPrefix = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=50),
]


class DocumentSequenceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    financial_year_id: UUID
    document_type: DocumentType
    series_name: SeriesName
    format: NumberFormat
    prefix: OptionalPrefix | None = None
    start_number: int = Field(ge=1)
    next_number: int = Field(ge=1)
    padding: int = Field(ge=1)
    priority: int | None = None


class DocumentSequenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    financial_year_id: UUID
    document_type: DocumentType
    series_name: str
    format: str
    prefix: str | None
    start_number: int
    next_number: int
    padding: int
    priority: int | None
    status: DocumentSequenceStatus
    created_at: datetime
    updated_at: datetime
