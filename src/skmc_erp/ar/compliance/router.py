from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.ar.compliance import service
from skmc_erp.ar.compliance.schema import CompanyLutCreate, CompanyLutResponse
from skmc_erp.core.tenant.dependencies import get_temporary_tenant_context
from skmc_erp.core.tenant.model import Tenant
from skmc_erp.database import get_db_session
from skmc_erp.ar.compliance.service import (
    CompanyLutInputError,
    CompanyLutNotFoundError,
    CompanyLutStateConflictError,
)

router = APIRouter(prefix="/companies/{company_id}/luts", tags=["ar_compliance"])


@router.get("", response_model=list[CompanyLutResponse])
async def list_company_luts_endpoint(
    company_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[CompanyLutResponse]:
    try:
        luts = await service.list_company_luts(session, tenant, company_id)
        return [CompanyLutResponse.model_validate(lut) for lut in luts]
    except CompanyLutNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{lut_id}", response_model=CompanyLutResponse)
async def get_company_lut_endpoint(
    company_id: UUID,
    lut_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyLutResponse:
    try:
        lut = await service.get_company_lut(session, tenant, company_id, lut_id)
        return CompanyLutResponse.model_validate(lut)
    except CompanyLutNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("", response_model=CompanyLutResponse)
async def create_company_lut_endpoint(
    company_id: UUID,
    payload: CompanyLutCreate,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyLutResponse:
    try:
        lut = await service.create_company_lut(session, tenant, company_id, payload)
        return CompanyLutResponse.model_validate(lut)
    except CompanyLutStateConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except CompanyLutNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{lut_id}/inactivate", response_model=CompanyLutResponse)
async def inactivate_company_lut_endpoint(
    company_id: UUID,
    lut_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyLutResponse:
    try:
        lut = await service.inactivate_company_lut(session, tenant, company_id, lut_id)
        return CompanyLutResponse.model_validate(lut)
    except CompanyLutStateConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except CompanyLutNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{lut_id}/activate", response_model=CompanyLutResponse)
async def activate_company_lut_endpoint(
    company_id: UUID,
    lut_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyLutResponse:
    try:
        lut = await service.activate_company_lut(session, tenant, company_id, lut_id)
        return CompanyLutResponse.model_validate(lut)
    except CompanyLutStateConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except CompanyLutNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
