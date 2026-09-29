from typing import Annotated, Never
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.core.cost_center.schema import (
    BusinessSegmentCreate,
    BusinessSegmentResponse,
    BusinessSegmentUpdate,
    CompanyCostCenterSettingsResponse,
    CompanyCostCenterSettingsUpdate,
    CostCenterTeamAssignment,
    CostCenterTeamCreate,
    CostCenterTeamResponse,
    CostCenterTeamUpdate,
    LocationCostCenterCreate,
    LocationCostCenterResponse,
    LocationCostCenterUpdate,
    TeamCreate,
    TeamResponse,
)
from skmc_erp.core.cost_center.service import (
    CostCenterInputError,
    CostCenterNotFoundError,
    CostCenterStateConflictError,
    assign_team_cost_center,
    configure_company_cost_center_settings,
    create_business_segment,
    create_cost_center_team,
    create_location_cost_center,
    create_team,
    get_business_segment,
    get_company_cost_center_settings,
    get_cost_center_team,
    get_location_cost_center,
    inactivate_business_segment,
    inactivate_cost_center_team,
    inactivate_location_cost_center,
    inactivate_team,
    list_business_segments,
    list_cost_center_teams,
    list_location_cost_centers,
    update_business_segment,
    update_cost_center_team,
    update_location_cost_center,
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
    elif isinstance(exc, CostCenterInputError):
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    else:
        status_code = status.HTTP_409_CONFLICT
    raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.get(
    "/cost-center-settings",
    response_model=CompanyCostCenterSettingsResponse,
)
async def get_company_cost_center_settings_endpoint(
    company_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyCostCenterSettingsResponse:
    try:
        settings = await get_company_cost_center_settings(
            session=session,
            tenant=tenant,
            company_id=company_id,
        )
    except CostCenterNotFoundError as exc:
        _raise_http_error(exc)
    if settings is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cost Center settings not found",
        )
    return CompanyCostCenterSettingsResponse.model_validate(settings)


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


@router.get(
    "/business-segments",
    response_model=list[BusinessSegmentResponse],
)
async def list_business_segments_endpoint(
    company_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[BusinessSegmentResponse]:
    try:
        segments = await list_business_segments(
            session=session,
            tenant=tenant,
            company_id=company_id,
        )
    except CostCenterNotFoundError as exc:
        _raise_http_error(exc)
    return [BusinessSegmentResponse.model_validate(row) for row in segments]


@router.get(
    "/business-segments/{segment_id}",
    response_model=BusinessSegmentResponse,
)
async def get_business_segment_endpoint(
    company_id: UUID,
    segment_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> BusinessSegmentResponse:
    segment = await get_business_segment(
        session=session,
        tenant=tenant,
        company_id=company_id,
        segment_id=segment_id,
    )
    if segment is None:
        raise HTTPException(status_code=404, detail="Business Segment not found")
    return BusinessSegmentResponse.model_validate(segment)


@router.patch(
    "/business-segments/{segment_id}",
    response_model=BusinessSegmentResponse,
)
async def update_business_segment_endpoint(
    company_id: UUID,
    segment_id: UUID,
    segment_data: BusinessSegmentUpdate,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> BusinessSegmentResponse:
    try:
        segment = await update_business_segment(
            session=session,
            tenant=tenant,
            company_id=company_id,
            segment_id=segment_id,
            segment_data=segment_data,
        )
    except (CostCenterNotFoundError, CostCenterStateConflictError) as exc:
        _raise_http_error(exc)
    if segment is None:
        raise HTTPException(status_code=404, detail="Business Segment not found")
    return BusinessSegmentResponse.model_validate(segment)


@router.post(
    "/business-segments/{segment_id}/inactivate",
    response_model=BusinessSegmentResponse,
)
async def inactivate_business_segment_endpoint(
    company_id: UUID,
    segment_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> BusinessSegmentResponse:
    try:
        segment = await inactivate_business_segment(
            session=session,
            tenant=tenant,
            company_id=company_id,
            segment_id=segment_id,
        )
    except (CostCenterNotFoundError, CostCenterStateConflictError) as exc:
        _raise_http_error(exc)
    if segment is None:
        raise HTTPException(status_code=404, detail="Business Segment not found")
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


@router.get(
    "/cost-center-teams",
    response_model=list[CostCenterTeamResponse],
)
async def list_cost_center_teams_endpoint(
    company_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[CostCenterTeamResponse]:
    try:
        teams = await list_cost_center_teams(
            session=session,
            tenant=tenant,
            company_id=company_id,
        )
    except CostCenterNotFoundError as exc:
        _raise_http_error(exc)
    return [CostCenterTeamResponse.model_validate(row) for row in teams]


@router.get(
    "/cost-center-teams/{cost_center_team_id}",
    response_model=CostCenterTeamResponse,
)
async def get_cost_center_team_endpoint(
    company_id: UUID,
    cost_center_team_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CostCenterTeamResponse:
    cost_center_team = await get_cost_center_team(
        session=session,
        tenant=tenant,
        company_id=company_id,
        cost_center_team_id=cost_center_team_id,
    )
    if cost_center_team is None:
        raise HTTPException(status_code=404, detail="Cost Center Team not found")
    return CostCenterTeamResponse.model_validate(cost_center_team)


@router.patch(
    "/cost-center-teams/{cost_center_team_id}",
    response_model=CostCenterTeamResponse,
)
async def update_cost_center_team_endpoint(
    company_id: UUID,
    cost_center_team_id: UUID,
    team_data: CostCenterTeamUpdate,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CostCenterTeamResponse:
    try:
        cost_center_team = await update_cost_center_team(
            session=session,
            tenant=tenant,
            company_id=company_id,
            cost_center_team_id=cost_center_team_id,
            team_data=team_data,
        )
    except (CostCenterNotFoundError, CostCenterStateConflictError) as exc:
        _raise_http_error(exc)
    if cost_center_team is None:
        raise HTTPException(status_code=404, detail="Cost Center Team not found")
    return CostCenterTeamResponse.model_validate(cost_center_team)


@router.post(
    "/cost-center-teams/{cost_center_team_id}/inactivate",
    response_model=CostCenterTeamResponse,
)
async def inactivate_cost_center_team_endpoint(
    company_id: UUID,
    cost_center_team_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CostCenterTeamResponse:
    try:
        cost_center_team = await inactivate_cost_center_team(
            session=session,
            tenant=tenant,
            company_id=company_id,
            cost_center_team_id=cost_center_team_id,
        )
    except (CostCenterNotFoundError, CostCenterStateConflictError) as exc:
        _raise_http_error(exc)
    if cost_center_team is None:
        raise HTTPException(status_code=404, detail="Cost Center Team not found")
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


@router.put(
    "/teams/{team_id}/cost-center-team",
    response_model=TeamResponse,
)
async def assign_team_cost_center_endpoint(
    company_id: UUID,
    team_id: UUID,
    assignment_data: CostCenterTeamAssignment,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TeamResponse:
    try:
        team = await assign_team_cost_center(
            session=session,
            tenant=tenant,
            company_id=company_id,
            team_id=team_id,
            assignment_data=assignment_data,
        )
    except (
        CostCenterInputError,
        CostCenterNotFoundError,
        CostCenterStateConflictError,
    ) as exc:
        _raise_http_error(exc)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")
    return TeamResponse.model_validate(team)


@router.post(
    "/teams/{team_id}/inactivate",
    response_model=TeamResponse,
)
async def inactivate_team_endpoint(
    company_id: UUID,
    team_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TeamResponse:
    try:
        team = await inactivate_team(
            session=session,
            tenant=tenant,
            company_id=company_id,
            team_id=team_id,
        )
    except (CostCenterNotFoundError, CostCenterStateConflictError) as exc:
        _raise_http_error(exc)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")
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


@router.get(
    "/location-cost-centers",
    response_model=list[LocationCostCenterResponse],
)
async def list_location_cost_centers_endpoint(
    company_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[LocationCostCenterResponse]:
    try:
        rows = await list_location_cost_centers(
            session=session,
            tenant=tenant,
            company_id=company_id,
        )
    except CostCenterNotFoundError as exc:
        _raise_http_error(exc)
    return [LocationCostCenterResponse.model_validate(row) for row in rows]


@router.get(
    "/location-cost-centers/{location_cost_center_id}",
    response_model=LocationCostCenterResponse,
)
async def get_location_cost_center_endpoint(
    company_id: UUID,
    location_cost_center_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> LocationCostCenterResponse:
    location_cost_center = await get_location_cost_center(
        session=session,
        tenant=tenant,
        company_id=company_id,
        location_cost_center_id=location_cost_center_id,
    )
    if location_cost_center is None:
        raise HTTPException(
            status_code=404,
            detail="Location Cost Center not found",
        )
    return LocationCostCenterResponse.model_validate(location_cost_center)


@router.patch(
    "/location-cost-centers/{location_cost_center_id}",
    response_model=LocationCostCenterResponse,
)
async def update_location_cost_center_endpoint(
    company_id: UUID,
    location_cost_center_id: UUID,
    location_data: LocationCostCenterUpdate,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> LocationCostCenterResponse:
    try:
        location_cost_center = await update_location_cost_center(
            session=session,
            tenant=tenant,
            company_id=company_id,
            location_cost_center_id=location_cost_center_id,
            location_data=location_data,
        )
    except (CostCenterNotFoundError, CostCenterStateConflictError) as exc:
        _raise_http_error(exc)
    if location_cost_center is None:
        raise HTTPException(
            status_code=404,
            detail="Location Cost Center not found",
        )
    return LocationCostCenterResponse.model_validate(location_cost_center)


@router.post(
    "/location-cost-centers/{location_cost_center_id}/inactivate",
    response_model=LocationCostCenterResponse,
)
async def inactivate_location_cost_center_endpoint(
    company_id: UUID,
    location_cost_center_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> LocationCostCenterResponse:
    try:
        location_cost_center = await inactivate_location_cost_center(
            session=session,
            tenant=tenant,
            company_id=company_id,
            location_cost_center_id=location_cost_center_id,
        )
    except (CostCenterNotFoundError, CostCenterStateConflictError) as exc:
        _raise_http_error(exc)
    if location_cost_center is None:
        raise HTTPException(
            status_code=404,
            detail="Location Cost Center not found",
        )
    return LocationCostCenterResponse.model_validate(location_cost_center)
