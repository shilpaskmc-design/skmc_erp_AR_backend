from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.core.company_location.schema import (
    CompanyLocationCreate,
    CompanyLocationResponse,
    CompanyLocationUpdate,
    CompanyLocationVersionResponse,
    LocationCostCenterAssignment,
)
from skmc_erp.core.company_location.service import (
    CompanyLocationInputError,
    CompanyLocationNotFoundError,
    CompanyLocationStateConflictError,
    assign_location_cost_center,
    create_company_location,
    get_company_location,
    inactivate_company_location,
    list_company_location_address_history,
    list_company_locations,
    update_company_location,
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


@router.get("", response_model=list[CompanyLocationResponse])
async def list_company_locations_endpoint(
    company_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[CompanyLocationResponse]:
    try:
        locations = await list_company_locations(
            session=session,
            tenant=tenant,
            company_id=company_id,
        )
    except CompanyLocationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return [
        CompanyLocationResponse.model_validate(location)
        for location in locations
    ]


@router.get("/{location_id}", response_model=CompanyLocationResponse)
async def get_company_location_endpoint(
    company_id: UUID,
    location_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyLocationResponse:
    location = await get_company_location(
        session=session,
        tenant=tenant,
        company_id=company_id,
        location_id=location_id,
    )
    if location is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company Location not found",
        )
    return CompanyLocationResponse.model_validate(location)


@router.get(
    "/{location_id}/address-history",
    response_model=list[CompanyLocationVersionResponse],
)
async def list_company_location_address_history_endpoint(
    company_id: UUID,
    location_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    as_of: date | None = None,
) -> list[CompanyLocationVersionResponse]:
    versions = await list_company_location_address_history(
        session=session,
        tenant=tenant,
        company_id=company_id,
        location_id=location_id,
        as_of=as_of,
    )
    if versions is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company Location not found",
        )
    return [
        CompanyLocationVersionResponse.model_validate(version)
        for version in versions
    ]


@router.patch("/{location_id}", response_model=CompanyLocationResponse)
async def update_company_location_endpoint(
    company_id: UUID,
    location_id: UUID,
    location_data: CompanyLocationUpdate,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyLocationResponse:
    try:
        location = await update_company_location(
            session=session,
            tenant=tenant,
            company_id=company_id,
            location_id=location_id,
            location_data=location_data,
        )
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
    if location is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company Location not found",
        )
    return CompanyLocationResponse.model_validate(location)


@router.put(
    "/{location_id}/location-cost-center",
    response_model=CompanyLocationResponse,
)
async def assign_location_cost_center_endpoint(
    company_id: UUID,
    location_id: UUID,
    assignment_data: LocationCostCenterAssignment,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyLocationResponse:
    try:
        location = await assign_location_cost_center(
            session=session,
            tenant=tenant,
            company_id=company_id,
            location_id=location_id,
            assignment_data=assignment_data,
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
    if location is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company Location not found",
        )
    return CompanyLocationResponse.model_validate(location)


@router.post(
    "/{location_id}/inactivate",
    response_model=CompanyLocationResponse,
)
async def inactivate_company_location_endpoint(
    company_id: UUID,
    location_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyLocationResponse:
    try:
        location = await inactivate_company_location(
            session=session,
            tenant=tenant,
            company_id=company_id,
            location_id=location_id,
        )
    except CompanyLocationStateConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    if location is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company Location not found",
        )
    return CompanyLocationResponse.model_validate(location)
