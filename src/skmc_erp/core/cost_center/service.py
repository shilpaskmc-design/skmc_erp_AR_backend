from collections.abc import Sequence
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
    BusinessSegmentUpdate,
    CompanyCostCenterSettingsUpdate,
    CostCenterTeamAssignment,
    CostCenterTeamCreate,
    CostCenterTeamUpdate,
    LocationCostCenterCreate,
    LocationCostCenterUpdate,
    TeamCreate,
)
from skmc_erp.core.tenant.model import Tenant


class CostCenterNotFoundError(Exception):
    """The Company is not visible within the resolved Tenant."""


class CostCenterInputError(Exception):
    """A supplied Cost Center relationship is invalid."""


class CostCenterStateConflictError(Exception):
    """The requested configuration conflicts with current business state."""


async def _get_visible_company(
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
    return company


async def _get_tenant_company(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
) -> Company:
    company = await _get_visible_company(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    if company.status is CompanyStatus.INACTIVE:
        raise CostCenterStateConflictError("Company is inactive")
    return company


async def _commit(session: AsyncSession, conflict_message: str) -> None:
    try:
        await session.flush()
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise CostCenterStateConflictError(conflict_message) from exc


async def get_company_cost_center_settings(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
) -> CompanyCostCenterSettings | None:
    await _get_visible_company(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    return await session.get(CompanyCostCenterSettings, company_id)


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

    await _commit(
        session,
        "Cost Center settings could not be saved due to a data conflict",
    )

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
    await _commit(
        session,
        "Business Segment could not be created due to a data conflict",
    )
    await session.refresh(segment)
    return segment


async def list_business_segments(
    *, session: AsyncSession, tenant: Tenant, company_id: UUID
) -> Sequence[CostCenterBusinessSegment]:
    await _get_visible_company(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    result = await session.scalars(
        select(CostCenterBusinessSegment)
        .where(CostCenterBusinessSegment.company_id == company_id)
        .order_by(CostCenterBusinessSegment.name, CostCenterBusinessSegment.id)
    )
    return result.all()


async def get_business_segment(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    segment_id: UUID,
) -> CostCenterBusinessSegment | None:
    return await session.scalar(
        select(CostCenterBusinessSegment)
        .join(Company, CostCenterBusinessSegment.company_id == Company.id)
        .where(
            CostCenterBusinessSegment.id == segment_id,
            CostCenterBusinessSegment.company_id == company_id,
            Company.tenant_id == tenant.id,
        )
    )


async def update_business_segment(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    segment_id: UUID,
    segment_data: BusinessSegmentUpdate,
) -> CostCenterBusinessSegment | None:
    await _get_tenant_company(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    segment = await get_business_segment(
        session=session,
        tenant=tenant,
        company_id=company_id,
        segment_id=segment_id,
    )
    if segment is None:
        return None
    if segment.status is CostCenterStatus.INACTIVE:
        raise CostCenterStateConflictError(
            "Inactive Business Segment cannot be changed"
        )
    for field, value in segment_data.model_dump(exclude_unset=True).items():
        setattr(segment, field, value)
    segment.updated_at = datetime.now(UTC)
    await _commit(
        session,
        "Business Segment could not be updated due to a data conflict",
    )
    await session.refresh(segment)
    return segment


async def inactivate_business_segment(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    segment_id: UUID,
) -> CostCenterBusinessSegment | None:
    await _get_tenant_company(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    segment = await get_business_segment(
        session=session,
        tenant=tenant,
        company_id=company_id,
        segment_id=segment_id,
    )
    if segment is None:
        return None
    if segment.status is CostCenterStatus.INACTIVE:
        return segment
    segment.status = CostCenterStatus.INACTIVE
    segment.updated_at = datetime.now(UTC)
    await _commit(session, "Business Segment could not be inactivated")
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
    await _commit(
        session,
        "Cost Center Team could not be created due to a data conflict",
    )
    await session.refresh(cost_center_team)
    return cost_center_team


async def list_cost_center_teams(
    *, session: AsyncSession, tenant: Tenant, company_id: UUID
) -> Sequence[CostCenterTeam]:
    await _get_visible_company(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    result = await session.scalars(
        select(CostCenterTeam)
        .where(CostCenterTeam.company_id == company_id)
        .order_by(CostCenterTeam.name, CostCenterTeam.id)
    )
    return result.all()


async def get_cost_center_team(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    cost_center_team_id: UUID,
) -> CostCenterTeam | None:
    return await session.scalar(
        select(CostCenterTeam)
        .join(Company, CostCenterTeam.company_id == Company.id)
        .where(
            CostCenterTeam.id == cost_center_team_id,
            CostCenterTeam.company_id == company_id,
            Company.tenant_id == tenant.id,
        )
    )


async def update_cost_center_team(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    cost_center_team_id: UUID,
    team_data: CostCenterTeamUpdate,
) -> CostCenterTeam | None:
    await _get_tenant_company(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    cost_center_team = await get_cost_center_team(
        session=session,
        tenant=tenant,
        company_id=company_id,
        cost_center_team_id=cost_center_team_id,
    )
    if cost_center_team is None:
        return None
    if cost_center_team.status is CostCenterStatus.INACTIVE:
        raise CostCenterStateConflictError(
            "Inactive Cost Center Team cannot be changed"
        )
    for field, value in team_data.model_dump(exclude_unset=True).items():
        setattr(cost_center_team, field, value)
    cost_center_team.updated_at = datetime.now(UTC)
    await _commit(
        session,
        "Cost Center Team could not be updated due to a data conflict",
    )
    await session.refresh(cost_center_team)
    return cost_center_team


async def inactivate_cost_center_team(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    cost_center_team_id: UUID,
) -> CostCenterTeam | None:
    await _get_tenant_company(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    cost_center_team = await get_cost_center_team(
        session=session,
        tenant=tenant,
        company_id=company_id,
        cost_center_team_id=cost_center_team_id,
    )
    if cost_center_team is None:
        return None
    if cost_center_team.status is CostCenterStatus.INACTIVE:
        return cost_center_team
    cost_center_team.status = CostCenterStatus.INACTIVE
    cost_center_team.updated_at = datetime.now(UTC)
    await _commit(session, "Cost Center Team could not be inactivated")
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
    await _commit(
        session,
        "Team could not be created due to a data conflict",
    )
    await session.refresh(team)
    return team


async def assign_team_cost_center(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    team_id: UUID,
    assignment_data: CostCenterTeamAssignment,
) -> Team | None:
    await _get_tenant_company(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    team = await session.scalar(
        select(Team)
        .join(Company, Team.company_id == Company.id)
        .where(
            Team.id == team_id,
            Team.company_id == company_id,
            Company.tenant_id == tenant.id,
        )
    )
    if team is None:
        return None
    if team.status is TeamStatus.INACTIVE:
        raise CostCenterStateConflictError("Inactive Team cannot be changed")
    if assignment_data.cost_center_team_id is not None:
        cost_center_team = await session.scalar(
            select(CostCenterTeam).where(
                CostCenterTeam.id == assignment_data.cost_center_team_id,
                CostCenterTeam.company_id == company_id,
            )
        )
        if cost_center_team is None:
            raise CostCenterInputError(
                "Cost Center Team does not belong to the Company"
            )
        if cost_center_team.status is not CostCenterStatus.ACTIVE:
            raise CostCenterStateConflictError("Cost Center Team is not active")
    team.cost_center_team_id = assignment_data.cost_center_team_id
    team.updated_at = datetime.now(UTC)
    await _commit(session, "Team assignment could not be saved")
    await session.refresh(team)
    return team


async def inactivate_team(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    team_id: UUID,
) -> Team | None:
    await _get_tenant_company(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    team = await session.scalar(
        select(Team)
        .join(Company, Team.company_id == Company.id)
        .where(
            Team.id == team_id,
            Team.company_id == company_id,
            Company.tenant_id == tenant.id,
        )
    )
    if team is None:
        return None
    if team.status is TeamStatus.INACTIVE:
        return team
    team.status = TeamStatus.INACTIVE
    team.updated_at = datetime.now(UTC)
    await _commit(session, "Team could not be inactivated")
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
    await _commit(
        session,
        "Location Cost Center could not be created due to a data conflict",
    )
    await session.refresh(location_cost_center)
    return location_cost_center


async def list_location_cost_centers(
    *, session: AsyncSession, tenant: Tenant, company_id: UUID
) -> Sequence[CostCenterLocation]:
    await _get_visible_company(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    result = await session.scalars(
        select(CostCenterLocation)
        .where(CostCenterLocation.company_id == company_id)
        .order_by(CostCenterLocation.name, CostCenterLocation.id)
    )
    return result.all()


async def get_location_cost_center(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    location_cost_center_id: UUID,
) -> CostCenterLocation | None:
    return await session.scalar(
        select(CostCenterLocation)
        .join(Company, CostCenterLocation.company_id == Company.id)
        .where(
            CostCenterLocation.id == location_cost_center_id,
            CostCenterLocation.company_id == company_id,
            Company.tenant_id == tenant.id,
        )
    )


async def update_location_cost_center(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    location_cost_center_id: UUID,
    location_data: LocationCostCenterUpdate,
) -> CostCenterLocation | None:
    await _get_tenant_company(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    location_cost_center = await get_location_cost_center(
        session=session,
        tenant=tenant,
        company_id=company_id,
        location_cost_center_id=location_cost_center_id,
    )
    if location_cost_center is None:
        return None
    if location_cost_center.status is CostCenterStatus.INACTIVE:
        raise CostCenterStateConflictError(
            "Inactive Location Cost Center cannot be changed"
        )
    for field, value in location_data.model_dump(exclude_unset=True).items():
        setattr(location_cost_center, field, value)
    location_cost_center.updated_at = datetime.now(UTC)
    await _commit(
        session,
        "Location Cost Center could not be updated due to a data conflict",
    )
    await session.refresh(location_cost_center)
    return location_cost_center


async def inactivate_location_cost_center(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    location_cost_center_id: UUID,
) -> CostCenterLocation | None:
    await _get_tenant_company(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    location_cost_center = await get_location_cost_center(
        session=session,
        tenant=tenant,
        company_id=company_id,
        location_cost_center_id=location_cost_center_id,
    )
    if location_cost_center is None:
        return None
    if location_cost_center.status is CostCenterStatus.INACTIVE:
        return location_cost_center
    location_cost_center.status = CostCenterStatus.INACTIVE
    location_cost_center.updated_at = datetime.now(UTC)
    await _commit(session, "Location Cost Center could not be inactivated")
    await session.refresh(location_cost_center)
    return location_cost_center
