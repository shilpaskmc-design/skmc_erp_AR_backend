from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.core.company.schema import (
    CompanyCreate,
    CompanyLegalNameVersionResponse,
    CompanyResponse,
    CompanyUpdate,
)
from skmc_erp.core.company.service import (
    CompanyInputError,
    CompanyStateConflictError,
    create_company,
    get_company,
    inactivate_company,
    list_company_legal_name_history,
    list_companies,
    update_company,
)
from skmc_erp.core.tenant.dependencies import get_temporary_tenant_context
from skmc_erp.core.tenant.model import Tenant
from skmc_erp.database import get_db_session

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post("", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company_endpoint(
    company_data: CompanyCreate,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyResponse:
    try:
        company = await create_company(
            session=session,
            tenant=tenant,
            company_data=company_data,
        )
    except CompanyInputError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except CompanyStateConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return CompanyResponse.model_validate(company)


@router.get("", response_model=list[CompanyResponse])
async def list_companies_endpoint(
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[CompanyResponse]:
    companies = await list_companies(session=session, tenant=tenant)
    return [CompanyResponse.model_validate(company) for company in companies]


@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company_endpoint(
    company_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyResponse:
    company = await get_company(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )
    return CompanyResponse.model_validate(company)


@router.get(
    "/{company_id}/legal-name-history",
    response_model=list[CompanyLegalNameVersionResponse],
)
async def list_company_legal_name_history_endpoint(
    company_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[CompanyLegalNameVersionResponse]:
    versions = await list_company_legal_name_history(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    if versions is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )
    return [
        CompanyLegalNameVersionResponse.model_validate(version)
        for version in versions
    ]


@router.patch("/{company_id}", response_model=CompanyResponse)
async def update_company_endpoint(
    company_id: UUID,
    company_data: CompanyUpdate,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyResponse:
    try:
        company = await update_company(
            session=session,
            tenant=tenant,
            company_id=company_id,
            company_data=company_data,
        )
    except CompanyInputError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except CompanyStateConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )
    return CompanyResponse.model_validate(company)


@router.post("/{company_id}/inactivate", response_model=CompanyResponse)
async def inactivate_company_endpoint(
    company_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyResponse:
    try:
        company = await inactivate_company(
            session=session,
            tenant=tenant,
            company_id=company_id,
        )
    except CompanyStateConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )
    return CompanyResponse.model_validate(company)
