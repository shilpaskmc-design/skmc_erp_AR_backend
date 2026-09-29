from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.ar.document_presentation.schema import (
    CompanyDocumentBrandingCreate,
    CompanyDocumentBrandingResponse,
    CompanyDocumentPresentationResponse,
    CompanyDocumentTemplateResponse,
    CompanyDocumentTemplateSelection,
)
from skmc_erp.ar.document_presentation.service import (
    DocumentPresentationInputError,
    DocumentPresentationNotFoundError,
    DocumentPresentationStateConflictError,
    create_company_document_branding,
    get_current_company_document_branding,
    get_current_document_presentation,
    list_company_document_branding,
    list_document_templates,
    select_company_billing_template,
)
from skmc_erp.core.tenant.dependencies import get_temporary_tenant_context
from skmc_erp.core.tenant.model import Tenant
from skmc_erp.database import get_db_session

router = APIRouter(
    prefix="/companies/{company_id}/document-templates",
    tags=["document-templates"],
)
branding_router = APIRouter(
    prefix="/companies/{company_id}/document-branding",
    tags=["document-branding"],
)


def _presentation_response(
    selection: object,
    branding: object | None,
) -> CompanyDocumentPresentationResponse:
    return CompanyDocumentPresentationResponse(
        selection=CompanyDocumentTemplateResponse.model_validate(selection),
        branding=(
            CompanyDocumentBrandingResponse.model_validate(branding)
            if branding is not None
            else None
        ),
    )


@router.get("", response_model=list[CompanyDocumentTemplateResponse])
async def list_document_templates_endpoint(
    company_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[CompanyDocumentTemplateResponse]:
    templates = await list_document_templates(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    return [
        CompanyDocumentTemplateResponse.model_validate(item)
        for item in templates
    ]


@router.get(
    "/current",
    response_model=CompanyDocumentPresentationResponse,
)
async def get_current_document_presentation_endpoint(
    company_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyDocumentPresentationResponse:
    presentation = await get_current_document_presentation(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    if presentation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Current billing document template is not configured",
        )
    return _presentation_response(*presentation)


@router.put(
    "/current",
    response_model=CompanyDocumentPresentationResponse,
)
async def select_company_billing_template_endpoint(
    company_id: UUID,
    selection_data: CompanyDocumentTemplateSelection,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyDocumentPresentationResponse:
    try:
        presentation = await select_company_billing_template(
            session=session,
            tenant=tenant,
            company_id=company_id,
            selection_data=selection_data,
        )
    except DocumentPresentationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except DocumentPresentationInputError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except DocumentPresentationStateConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return _presentation_response(*presentation)


@branding_router.get("", response_model=list[CompanyDocumentBrandingResponse])
async def list_company_document_branding_endpoint(
    company_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[CompanyDocumentBrandingResponse]:
    rows = await list_company_document_branding(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    return [CompanyDocumentBrandingResponse.model_validate(row) for row in rows]


@branding_router.get(
    "/current",
    response_model=CompanyDocumentBrandingResponse,
)
async def get_current_company_document_branding_endpoint(
    company_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyDocumentBrandingResponse:
    branding = await get_current_company_document_branding(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    if branding is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Current Company document branding is not configured",
        )
    return CompanyDocumentBrandingResponse.model_validate(branding)


@branding_router.put(
    "/current",
    response_model=CompanyDocumentBrandingResponse,
)
async def create_company_document_branding_endpoint(
    company_id: UUID,
    branding_data: CompanyDocumentBrandingCreate,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyDocumentBrandingResponse:
    try:
        branding = await create_company_document_branding(
            session=session,
            tenant=tenant,
            company_id=company_id,
            branding_data=branding_data,
        )
    except DocumentPresentationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except DocumentPresentationInputError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except DocumentPresentationStateConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return CompanyDocumentBrandingResponse.model_validate(branding)
