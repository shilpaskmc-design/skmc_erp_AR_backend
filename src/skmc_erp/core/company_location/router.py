from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.core.company_location.schema import (
    CompanyLocationCreate,
    CompanyLocationResponse,
)
from skmc_erp.core.company_location.service import (
    CompanyLocationInputError,
    CompanyLocationNotFoundError,
    CompanyLocationStateConflictError,
    create_company_location,
)
from skmc_erp.core.tenant.dependencies import get_temporary_tenant_context
from skmc_erp.core.tenant.model import Tenant
from skmc_erp.database import get_db_session

router = APIRouter(
    prefix="/companies/{company_id}/locations",
    tags=["company-locations"],
)


@router.post(
    "",
    response_model=CompanyLocationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_company_location_endpoint(
    company_id: UUID,
    location_data: CompanyLocationCreate,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyLocationResponse:
    try:
        location = await create_company_location(
            session=session,
            tenant=tenant,
            company_id=company_id,
            location_data=location_data,
        )
    except CompanyLocationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except CompanyLocationInputError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except CompanyLocationStateConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return CompanyLocationResponse.model_validate(location)
