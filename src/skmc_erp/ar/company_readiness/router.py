from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.ar.company_readiness.schema import CompanyReadinessResponse
from skmc_erp.ar.company_readiness.service import (
    CompanyActivationConflictError,
    activate_company,
    evaluate_company_readiness,
)
from skmc_erp.core.company.schema import CompanyResponse
from skmc_erp.core.tenant.dependencies import get_temporary_tenant_context
from skmc_erp.core.tenant.model import Tenant
from skmc_erp.database import get_db_session


router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("/{company_id}/readiness", response_model=CompanyReadinessResponse)
async def get_company_readiness_endpoint(
    company_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyReadinessResponse:
    readiness = await evaluate_company_readiness(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    if readiness is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )
    return readiness


@router.post("/{company_id}/activate", response_model=CompanyResponse)
async def activate_company_endpoint(
    company_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyResponse:
    try:
        company = await activate_company(
            session=session,
            tenant=tenant,
            company_id=company_id,
        )
    except CompanyActivationConflictError as exc:
        detail: str | dict[str, object] = str(exc)
        if exc.readiness is not None:
            detail = {
                "message": str(exc),
                "ready_for_activation": False,
                "blocking_checks": [
                    check.model_dump() for check in exc.readiness.blocking_checks
                ],
            }
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        ) from exc
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )
    return CompanyResponse.model_validate(company)
