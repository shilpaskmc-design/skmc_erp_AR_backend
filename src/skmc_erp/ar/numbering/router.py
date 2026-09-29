from typing import Annotated, Never
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.ar.numbering.schema import (
    DocumentSequenceCreate,
    DocumentSequenceResponse,
)
from skmc_erp.ar.numbering.service import (
    DocumentNumberingInputError,
    DocumentNumberingNotFoundError,
    DocumentNumberingStateConflictError,
    create_document_sequence,
    get_document_sequence,
    inactivate_document_sequence,
    list_document_sequences,
)
from skmc_erp.core.tenant.dependencies import get_temporary_tenant_context
from skmc_erp.core.tenant.model import Tenant
from skmc_erp.database import get_db_session


router = APIRouter(
    prefix="/companies/{company_id}/document-sequences",
    tags=["document-numbering"],
)


def _raise(exc: Exception) -> Never:
    if isinstance(exc, DocumentNumberingNotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, DocumentNumberingInputError):
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    else:
        status_code = status.HTTP_409_CONFLICT
    raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.post(
    "",
    response_model=DocumentSequenceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_document_sequence_endpoint(
    company_id: UUID,
    sequence_data: DocumentSequenceCreate,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DocumentSequenceResponse:
    try:
        sequence = await create_document_sequence(
            session=session,
            tenant=tenant,
            company_id=company_id,
            sequence_data=sequence_data,
        )
    except (
        DocumentNumberingInputError,
        DocumentNumberingNotFoundError,
        DocumentNumberingStateConflictError,
    ) as exc:
        _raise(exc)
    return DocumentSequenceResponse.model_validate(sequence)


@router.get("", response_model=list[DocumentSequenceResponse])
async def list_document_sequences_endpoint(
    company_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[DocumentSequenceResponse]:
    try:
        sequences = await list_document_sequences(
            session=session,
            tenant=tenant,
            company_id=company_id,
        )
    except DocumentNumberingNotFoundError as exc:
        _raise(exc)
    return [DocumentSequenceResponse.model_validate(row) for row in sequences]


@router.get("/{sequence_id}", response_model=DocumentSequenceResponse)
async def get_document_sequence_endpoint(
    company_id: UUID,
    sequence_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DocumentSequenceResponse:
    sequence = await get_document_sequence(
        session=session,
        tenant=tenant,
        company_id=company_id,
        sequence_id=sequence_id,
    )
    if sequence is None:
        raise HTTPException(status_code=404, detail="Document Sequence not found")
    return DocumentSequenceResponse.model_validate(sequence)


@router.post(
    "/{sequence_id}/inactivate",
    response_model=DocumentSequenceResponse,
)
async def inactivate_document_sequence_endpoint(
    company_id: UUID,
    sequence_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DocumentSequenceResponse:
    try:
        sequence = await inactivate_document_sequence(
            session=session,
            tenant=tenant,
            company_id=company_id,
            sequence_id=sequence_id,
        )
    except (
        DocumentNumberingNotFoundError,
        DocumentNumberingStateConflictError,
    ) as exc:
        _raise(exc)
    if sequence is None:
        raise HTTPException(status_code=404, detail="Document Sequence not found")
    return DocumentSequenceResponse.model_validate(sequence)
