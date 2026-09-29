from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.core.company.model import Company, CompanyStatus
from skmc_erp.core.company_gst_registration.model import (
    CompanyGSTRegistration,
    CompanyGSTRegistrationStatus,
)
from skmc_erp.core.company_location.model import (
    CompanyLocation,
    CompanyLocationStatus,
    CompanyLocationVersion,
)
from skmc_erp.core.company_location.schema import (
    CompanyLocationCreate,
    CompanyLocationUpdate,
    LocationCostCenterAssignment,
)
from skmc_erp.core.cost_center.model import CostCenterLocation, CostCenterStatus
from skmc_erp.core.geography.model import (
    Country,
    CountryStatus,
    CountrySubdivision,
    CountrySubdivisionStatus,
)
from skmc_erp.core.tenant.model import Tenant


class CompanyLocationNotFoundError(Exception):
    """The Company or Location is not visible within the resolved Tenant."""


class CompanyLocationInputError(Exception):
    """A supplied Location reference or relationship is invalid."""


class CompanyLocationStateConflictError(Exception):
    """The requested Location conflicts with current business state."""


ADDRESS_FIELDS = (
    "address_line_1",
    "address_line_2",
    "city",
    "district",
    "country_code",
    "subdivision_code",
    "postal_code",
)


def _business_date() -> date:
    return date.today()


async def _get_company_location_for_update(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    location_id: UUID,
) -> CompanyLocation | None:
    return await session.scalar(
        select(CompanyLocation)
        .join(Company, CompanyLocation.company_id == Company.id)
        .where(
            CompanyLocation.id == location_id,
            CompanyLocation.company_id == company_id,
            Company.tenant_id == tenant.id,
        )
        .with_for_update()
    )


async def create_company_location(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    location_data: CompanyLocationCreate,
    commit: bool = True,
) -> CompanyLocation:
    company = await session.scalar(
        select(Company)
        .where(
            Company.id == company_id,
            Company.tenant_id == tenant.id,
        )
        .with_for_update()
    )
    if company is None:
        raise CompanyLocationNotFoundError("Company not found")
    if company.status is CompanyStatus.INACTIVE:
        raise CompanyLocationStateConflictError("Company is inactive")

    country = await session.get(Country, location_data.country_code)
    if country is None:
        raise CompanyLocationInputError("Country does not exist")
    if country.status is not CountryStatus.ACTIVE:
        raise CompanyLocationStateConflictError("Country is not active")

    subdivision: CountrySubdivision | None = None
    if location_data.subdivision_code is not None:
        subdivision = await session.scalar(
            select(CountrySubdivision).where(
                CountrySubdivision.code == location_data.subdivision_code
            )
        )
        if subdivision is None:
            raise CompanyLocationInputError("Country Subdivision does not exist")
        if subdivision.status is not CountrySubdivisionStatus.ACTIVE:
            raise CompanyLocationStateConflictError(
                "Country Subdivision is not active"
            )
        if subdivision.country_code != country.code:
            raise CompanyLocationInputError(
                "Country Subdivision does not belong to the selected Country"
            )

    if location_data.is_registered_office:
        registered_office_id = await session.scalar(
            select(CompanyLocation.id)
            .where(
                CompanyLocation.company_id == company.id,
                CompanyLocation.status == CompanyLocationStatus.ACTIVE,
                CompanyLocation.is_registered_office.is_(True),
            )
            .limit(1)
        )
        if registered_office_id is not None:
            raise CompanyLocationStateConflictError(
                "Company already has an active Registered Office"
            )

    location_code = location_data.location_code
    if location_code is None:
        location_code = await session.scalar(
            text("SELECT core.next_company_location_code(:company_id)"),
            {"company_id": company.id},
        )
        if not isinstance(location_code, str):
            raise CompanyLocationStateConflictError(
                "Company Location code could not be generated"
            )

    location = CompanyLocation(
        company_id=company.id,
        location_code=location_code,
        location_name=location_data.location_name,
        address_line_1=location_data.address_line_1,
        address_line_2=location_data.address_line_2,
        city=location_data.city,
        district=location_data.district,
        subdivision_code=(
            subdivision.code if subdivision is not None else None
        ),
        country_code=country.code,
        postal_code=location_data.postal_code,
        is_registered_office=location_data.is_registered_office,
        is_corporate_office=location_data.is_corporate_office,
        is_branch=location_data.is_branch,
        is_billing_office=location_data.is_billing_office,
        is_warehouse=location_data.is_warehouse,
        other_purpose=location_data.other_purpose,
        status=CompanyLocationStatus.ACTIVE,
    )
    session.add(location)

    try:
        await session.flush()
        session.add(
            CompanyLocationVersion(
                company_location_id=location.id,
                address_line_1=location.address_line_1,
                address_line_2=location.address_line_2,
                city=location.city,
                district=location.district,
                subdivision_code=location.subdivision_code,
                country_code=location.country_code,
                postal_code=location.postal_code,
                valid_from=_business_date(),
                valid_to=None,
            )
        )
        await session.flush()
        if commit:
            await session.commit()
    except IntegrityError as exc:
        if commit:
            await session.rollback()
        raise CompanyLocationStateConflictError(
            "Company Location could not be created due to a data conflict"
        ) from exc

    if commit:
        await session.refresh(location)
    return location


async def list_company_locations(
    *, session: AsyncSession, tenant: Tenant, company_id: UUID
) -> Sequence[CompanyLocation]:
    company = await session.scalar(
        select(Company).where(
            Company.id == company_id,
            Company.tenant_id == tenant.id,
        )
    )
    if company is None:
        raise CompanyLocationNotFoundError("Company not found")

    result = await session.scalars(
        select(CompanyLocation)
        .where(CompanyLocation.company_id == company_id)
        .order_by(CompanyLocation.location_name, CompanyLocation.id)
    )
    return result.all()


async def get_company_location(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    location_id: UUID,
) -> CompanyLocation | None:
    return await session.scalar(
        select(CompanyLocation)
        .join(Company, CompanyLocation.company_id == Company.id)
        .where(
            CompanyLocation.id == location_id,
            CompanyLocation.company_id == company_id,
            Company.tenant_id == tenant.id,
        )
    )


async def update_company_location(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    location_id: UUID,
    location_data: CompanyLocationUpdate,
    commit: bool = True,
) -> CompanyLocation | None:
    location = await _get_company_location_for_update(
        session=session,
        tenant=tenant,
        company_id=company_id,
        location_id=location_id,
    )
    if location is None:
        return None
    if location.status is CompanyLocationStatus.INACTIVE:
        raise CompanyLocationStateConflictError(
            "Inactive Company Location cannot be changed"
        )

    changes = location_data.model_dump(exclude_unset=True)
    candidate_country_code = changes.get("country_code", location.country_code)
    candidate_subdivision_code = changes.get(
        "subdivision_code", location.subdivision_code
    )

    if "country_code" in changes or "subdivision_code" in changes:
        country = await session.get(Country, candidate_country_code)
        if country is None:
            raise CompanyLocationInputError("Country does not exist")
        if country.status is not CountryStatus.ACTIVE:
            raise CompanyLocationStateConflictError("Country is not active")

        if candidate_subdivision_code is not None:
            subdivision = await session.scalar(
                select(CountrySubdivision).where(
                    CountrySubdivision.code == candidate_subdivision_code
                )
            )
            if subdivision is None:
                raise CompanyLocationInputError(
                    "Country Subdivision does not exist"
                )
            if subdivision.status is not CountrySubdivisionStatus.ACTIVE:
                raise CompanyLocationStateConflictError(
                    "Country Subdivision is not active"
                )
            if subdivision.country_code != candidate_country_code:
                raise CompanyLocationInputError(
                    "Country Subdivision does not belong to the selected Country"
                )

    candidate_registration_id = changes.get(
        "gst_registration_id", location.gst_registration_id
    )
    if candidate_registration_id is not None:
        registration = await session.scalar(
            select(CompanyGSTRegistration).where(
                CompanyGSTRegistration.id == candidate_registration_id,
                CompanyGSTRegistration.company_id == company_id,
            )
        )
        if registration is None:
            raise CompanyLocationInputError(
                "GST Registration does not belong to the Company"
            )
        if candidate_subdivision_code is None:
            raise CompanyLocationInputError(
                "A GST-linked Location requires a Country Subdivision"
            )
        if registration.subdivision_code != candidate_subdivision_code:
            raise CompanyLocationInputError(
                "GST Registration jurisdiction does not match the Location"
            )
        if (
            registration.status is CompanyGSTRegistrationStatus.INACTIVE
            and location.gst_registration_id != registration.id
        ):
            raise CompanyLocationStateConflictError(
                "Inactive GST Registration cannot receive a new Location assignment"
            )

    purpose_fields = (
        "is_registered_office",
        "is_corporate_office",
        "is_branch",
        "is_billing_office",
        "is_warehouse",
    )
    has_purpose = any(
        changes.get(field, getattr(location, field)) for field in purpose_fields
    ) or changes.get("other_purpose", location.other_purpose) is not None
    if not has_purpose:
        raise CompanyLocationInputError(
            "At least one Location purpose must be selected"
        )

    candidate_registered_office = changes.get(
        "is_registered_office", location.is_registered_office
    )
    if (
        candidate_registered_office
        and location.status is CompanyLocationStatus.ACTIVE
    ):
        other_registered_office = await session.scalar(
            select(CompanyLocation.id)
            .where(
                CompanyLocation.company_id == company_id,
                CompanyLocation.id != location.id,
                CompanyLocation.status == CompanyLocationStatus.ACTIVE,
                CompanyLocation.is_registered_office.is_(True),
            )
            .limit(1)
        )
        if other_registered_office is not None:
            raise CompanyLocationStateConflictError(
                "Company already has an active Registered Office"
            )

    address_changed = any(
        field in changes and changes[field] != getattr(location, field)
        for field in ADDRESS_FIELDS
    )
    if address_changed:
        current_version = await session.scalar(
            select(CompanyLocationVersion)
            .where(
                CompanyLocationVersion.company_location_id == location.id,
                CompanyLocationVersion.valid_to.is_(None),
            )
            .with_for_update()
        )
        if current_version is None:
            raise CompanyLocationStateConflictError(
                "Company Location has no current address version"
            )
        effective_date = _business_date()
        if current_version.valid_from >= effective_date:
            raise CompanyLocationStateConflictError(
                "Company Location address has already changed today"
            )
        current_version.valid_to = effective_date - timedelta(days=1)
        session.add(
            CompanyLocationVersion(
                company_location_id=location.id,
                address_line_1=changes.get(
                    "address_line_1", location.address_line_1
                ),
                address_line_2=changes.get(
                    "address_line_2", location.address_line_2
                ),
                city=changes.get("city", location.city),
                district=changes.get("district", location.district),
                subdivision_code=candidate_subdivision_code,
                country_code=candidate_country_code,
                postal_code=changes.get("postal_code", location.postal_code),
                valid_from=effective_date,
                valid_to=None,
            )
        )

    for field, value in changes.items():
        setattr(location, field, value)
    location.updated_at = datetime.now(UTC)

    try:
        await session.flush()
        if commit:
            await session.commit()
    except IntegrityError as exc:
        if commit:
            await session.rollback()
        raise CompanyLocationStateConflictError(
            "Company Location could not be updated due to a data conflict"
        ) from exc

    if commit:
        await session.refresh(location)
    return location


async def list_company_location_address_history(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    location_id: UUID,
    as_of: date | None = None,
) -> Sequence[CompanyLocationVersion] | None:
    location = await get_company_location(
        session=session,
        tenant=tenant,
        company_id=company_id,
        location_id=location_id,
    )
    if location is None:
        return None
    query = select(CompanyLocationVersion).where(
        CompanyLocationVersion.company_location_id == location.id
    )
    if as_of is not None:
        query = query.where(
            CompanyLocationVersion.valid_from <= as_of,
            (
                CompanyLocationVersion.valid_to.is_(None)
                | (CompanyLocationVersion.valid_to >= as_of)
            ),
        )
    result = await session.scalars(
        query
        .order_by(
            CompanyLocationVersion.valid_from,
            CompanyLocationVersion.created_at,
            CompanyLocationVersion.id,
        )
    )
    return result.all()


async def assign_location_cost_center(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    location_id: UUID,
    assignment_data: LocationCostCenterAssignment,
) -> CompanyLocation | None:
    company = await session.scalar(
        select(Company).where(
            Company.id == company_id,
            Company.tenant_id == tenant.id,
        )
    )
    if company is None:
        raise CompanyLocationNotFoundError("Company not found")
    if company.status is CompanyStatus.INACTIVE:
        raise CompanyLocationStateConflictError("Company is inactive")

    location = await _get_company_location_for_update(
        session=session,
        tenant=tenant,
        company_id=company_id,
        location_id=location_id,
    )
    if location is None:
        return None
    if location.status is CompanyLocationStatus.INACTIVE:
        raise CompanyLocationStateConflictError(
            "Inactive Company Location cannot be changed"
        )
    if assignment_data.cost_center_location_id is not None:
        cost_center = await session.scalar(
            select(CostCenterLocation).where(
                CostCenterLocation.id
                == assignment_data.cost_center_location_id,
                CostCenterLocation.company_id == company_id,
            )
        )
        if cost_center is None:
            raise CompanyLocationInputError(
                "Location Cost Center does not belong to the Company"
            )
        if cost_center.status is not CostCenterStatus.ACTIVE:
            raise CompanyLocationStateConflictError(
                "Location Cost Center is not active"
            )
    location.cost_center_location_id = assignment_data.cost_center_location_id
    location.updated_at = datetime.now(UTC)
    try:
        await session.flush()
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise CompanyLocationStateConflictError(
            "Location Cost Center assignment could not be saved"
        ) from exc
    await session.refresh(location)
    return location


async def inactivate_company_location(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    location_id: UUID,
) -> CompanyLocation | None:
    location = await _get_company_location_for_update(
        session=session,
        tenant=tenant,
        company_id=company_id,
        location_id=location_id,
    )
    if location is None:
        return None
    if location.status is CompanyLocationStatus.INACTIVE:
        return location

    location.status = CompanyLocationStatus.INACTIVE
    location.updated_at = datetime.now(UTC)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise CompanyLocationStateConflictError(
            "Company Location could not be inactivated due to a data conflict"
        ) from exc

    await session.refresh(location)
    return location
