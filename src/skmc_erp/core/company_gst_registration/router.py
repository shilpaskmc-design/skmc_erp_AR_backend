from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.core.company_gst_registration.schema import (
    CompanyGSTRegistrationCreate,
    CompanyGSTRegistrationResponse,
)
from skmc_erp.core.company_gst_registration.service import (
    CompanyGSTRegistrationInputError,
    CompanyGSTRegistrationNotFoundError,
    CompanyGSTRegistrationStateConflictError,
    create_company_gst_registration,
)
from skmc_erp.core.tenant.dependencies import get_temporary_tenant_context
from skmc_erp.core.tenant.model import Tenant
from skmc_erp.database import get_db_session


router = APIRouter(
    prefix="/companies/{company_id}/gst-registrations",
    tags=["company-gst-registrations"],
)


@router.post(
    "",
    response_model=CompanyGSTRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_company_gst_registration_endpoint(
    company_id: UUID,
    registration_data: CompanyGSTRegistrationCreate,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyGSTRegistrationResponse:
    try:
        registration = await create_company_gst_registration(
            session=session,
            tenant=tenant,
            company_id=company_id,
            registration_data=registration_data,
        )
    except CompanyGSTRegistrationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except CompanyGSTRegistrationInputError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except CompanyGSTRegistrationStateConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return CompanyGSTRegistrationResponse.model_validate(registration)
