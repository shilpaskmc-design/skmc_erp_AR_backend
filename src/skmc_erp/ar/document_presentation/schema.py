from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints

from skmc_erp.ar.document_presentation.model import DocumentPresentationStatus


TemplateKey = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=100,
        pattern=r"^[A-Z][A-Z0-9_]*$",
    ),
]


class CompanyDocumentTemplateSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_key: TemplateKey


class CompanyDocumentBrandingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    logo_file_id: UUID | None = None
    signature_file_id: UUID | None = None
    stamp_file_id: UUID | None = None
    header_text: str | None = None
    footer_text: str | None = None


class CompanyDocumentBrandingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    logo_file_id: UUID | None
    signature_file_id: UUID | None
    stamp_file_id: UUID | None
    header_text: str | None
    footer_text: str | None
    status: DocumentPresentationStatus
    created_at: datetime
    updated_at: datetime


class CompanyDocumentTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    branding_id: UUID | None
    template_key: str
    version_no: int
    status: DocumentPresentationStatus
    created_at: datetime
    updated_at: datetime


class CompanyDocumentPresentationResponse(BaseModel):
    selection: CompanyDocumentTemplateResponse
    branding: CompanyDocumentBrandingResponse | None
