from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.core.company.model import Company, CompanyStatus
from skmc_erp.core.cost_center.model import (
    CompanyCostCenterSettings,
    CostCenterBusinessSegment,
    CostCenterLocation,
    CostCenterStatus,
    CostCenterTeam,
    Team,
    TeamStatus,
)
from skmc_erp.core.cost_center.schema import (
    BusinessSegmentCreate,
    CompanyCostCenterSettingsUpdate,
    CostCenterTeamCreate,
    LocationCostCenterCreate,
    TeamCreate,
)
from skmc_erp.core.tenant.model import Tenant


class CostCenterNotFoundError(Exception):
    """The Company is not visible within the resolved Tenant."""


class CostCenterStateConflictError(Exception):
    """The requested configuration conflicts with current business state."""


async def _get_tenant_company(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
) -> Company:
    company = await session.scalar(
        select(Company).where(
            Company.id == company_id,
            Company.tenant_id == tenant.id,
        )
    )
    if company is None:
        raise CostCenterNotFoundError("Company not found")
    if company.status is CompanyStatus.INACTIVE:
        raise CostCenterStateConflictError("Company is inactive")
    return company


async def configure_company_cost_center_settings(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    settings_data: CompanyCostCenterSettingsUpdate,
) -> CompanyCostCenterSettings:
    company = await _get_tenant_company(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    settings = await session.get(CompanyCostCenterSettings, company.id)
    if settings is None:
        settings = CompanyCostCenterSettings(
            company_id=company.id,
            cost_center_reporting_enabled=(
                settings_data.cost_center_reporting_enabled
            ),
            business_segment_enabled=settings_data.business_segment_enabled,
            team_enabled=settings_data.team_enabled,
            location_enabled=settings_data.location_enabled,
        )
        session.add(settings)
    else:
        settings.cost_center_reporting_enabled = (
            settings_data.cost_center_reporting_enabled
        )
        settings.business_segment_enabled = settings_data.business_segment_enabled
        settings.team_enabled = settings_data.team_enabled
        settings.location_enabled = settings_data.location_enabled
        settings.updated_at = datetime.now(UTC)

    try:
        await session.flush()
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise CostCenterStateConflictError(
            "Cost Center settings could not be saved due to a data conflict"
        ) from exc

    await session.refresh(settings)
    return settings


async def create_business_segment(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    segment_data: BusinessSegmentCreate,
) -> CostCenterBusinessSegment:
    company = await _get_tenant_company(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    segment = CostCenterBusinessSegment(
        company_id=company.id,
        name=segment_data.name,
        code=segment_data.code,
        status=CostCenterStatus.ACTIVE,
    )
    session.add(segment)
    try:
        await session.flush()
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise CostCenterStateConflictError(
            "Business Segment could not be created due to a data conflict"
        ) from exc
    await session.refresh(segment)
    return segment


async def create_cost_center_team(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    team_data: CostCenterTeamCreate,
) -> CostCenterTeam:
    company = await _get_tenant_company(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    cost_center_team = CostCenterTeam(
        company_id=company.id,
        name=team_data.name,
        code=team_data.code,
        status=CostCenterStatus.ACTIVE,
    )
    session.add(cost_center_team)
    try:
        await session.flush()
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise CostCenterStateConflictError(
            "Cost Center Team could not be created due to a data conflict"
        ) from exc
    await session.refresh(cost_center_team)
    return cost_center_team


async def create_team(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    team_data: TeamCreate,
) -> Team:
    company = await _get_tenant_company(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    team = Team(
        company_id=company.id,
        name=team_data.name,
        status=TeamStatus.ACTIVE,
    )
    session.add(team)
    try:
        await session.flush()
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise CostCenterStateConflictError(
            "Team could not be created due to a data conflict"
        ) from exc
    await session.refresh(team)
    return team


async def create_location_cost_center(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    location_data: LocationCostCenterCreate,
) -> CostCenterLocation:
    company = await _get_tenant_company(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    location_cost_center = CostCenterLocation(
        company_id=company.id,
        name=location_data.name,
        code=location_data.code,
        status=CostCenterStatus.ACTIVE,
    )
    session.add(location_cost_center)
    try:
        await session.flush()
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise CostCenterStateConflictError(
            "Location Cost Center could not be created due to a data conflict"
        ) from exc
    await session.refresh(location_cost_center)
    return location_cost_center
