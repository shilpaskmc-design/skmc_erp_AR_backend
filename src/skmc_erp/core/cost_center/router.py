from typing import Annotated, Never
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.core.cost_center.schema import (
    BusinessSegmentCreate,
    BusinessSegmentResponse,
    CompanyCostCenterSettingsResponse,
    CompanyCostCenterSettingsUpdate,
    CostCenterTeamCreate,
    CostCenterTeamResponse,
    LocationCostCenterCreate,
    LocationCostCenterResponse,
    TeamCreate,
    TeamResponse,
)
from skmc_erp.core.cost_center.service import (
    CostCenterNotFoundError,
    CostCenterStateConflictError,
    configure_company_cost_center_settings,
    create_business_segment,
    create_cost_center_team,
    create_location_cost_center,
    create_team,
)
from skmc_erp.core.tenant.dependencies import get_temporary_tenant_context
from skmc_erp.core.tenant.model import Tenant
from skmc_erp.database import get_db_session

router = APIRouter(
    prefix="/companies/{company_id}",
    tags=["cost-center-configuration"],
)


def _raise_http_error(exc: Exception) -> Never:
    if isinstance(exc, CostCenterNotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
    else:
        status_code = status.HTTP_409_CONFLICT
    raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.put(
    "/cost-center-settings",
    response_model=CompanyCostCenterSettingsResponse,
)
async def configure_company_cost_center_settings_endpoint(
    company_id: UUID,
    settings_data: CompanyCostCenterSettingsUpdate,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyCostCenterSettingsResponse:
    try:
        settings = await configure_company_cost_center_settings(
            session=session,
            tenant=tenant,
            company_id=company_id,
            settings_data=settings_data,
        )
    except (CostCenterNotFoundError, CostCenterStateConflictError) as exc:
        _raise_http_error(exc)
    return CompanyCostCenterSettingsResponse.model_validate(settings)


@router.post(
    "/business-segments",
    response_model=BusinessSegmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_business_segment_endpoint(
    company_id: UUID,
    segment_data: BusinessSegmentCreate,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> BusinessSegmentResponse:
    try:
        segment = await create_business_segment(
            session=session,
            tenant=tenant,
            company_id=company_id,
            segment_data=segment_data,
        )
    except (CostCenterNotFoundError, CostCenterStateConflictError) as exc:
        _raise_http_error(exc)
    return BusinessSegmentResponse.model_validate(segment)


@router.post(
    "/cost-center-teams",
    response_model=CostCenterTeamResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_cost_center_team_endpoint(
    company_id: UUID,
    team_data: CostCenterTeamCreate,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CostCenterTeamResponse:
    try:
        cost_center_team = await create_cost_center_team(
            session=session,
            tenant=tenant,
            company_id=company_id,
            team_data=team_data,
        )
    except (CostCenterNotFoundError, CostCenterStateConflictError) as exc:
        _raise_http_error(exc)
    return CostCenterTeamResponse.model_validate(cost_center_team)


@router.post(
    "/teams",
    response_model=TeamResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_team_endpoint(
    company_id: UUID,
    team_data: TeamCreate,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TeamResponse:
    try:
        team = await create_team(
            session=session,
            tenant=tenant,
            company_id=company_id,
            team_data=team_data,
        )
    except (CostCenterNotFoundError, CostCenterStateConflictError) as exc:
        _raise_http_error(exc)
    return TeamResponse.model_validate(team)


@router.post(
    "/location-cost-centers",
    response_model=LocationCostCenterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_location_cost_center_endpoint(
    company_id: UUID,
    location_data: LocationCostCenterCreate,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> LocationCostCenterResponse:
    try:
        location_cost_center = await create_location_cost_center(
            session=session,
            tenant=tenant,
            company_id=company_id,
            location_data=location_data,
        )
    except (CostCenterNotFoundError, CostCenterStateConflictError) as exc:
        _raise_http_error(exc)
    return LocationCostCenterResponse.model_validate(location_cost_center)
