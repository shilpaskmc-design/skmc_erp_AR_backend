from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.core.company.model import Company, CompanyStatus
from skmc_erp.core.company_location.model import (
    CompanyLocation,
    CompanyLocationStatus,
)
from skmc_erp.core.company_location.schema import CompanyLocationCreate
from skmc_erp.core.geography.model import (
    Country,
    CountryStatus,
    CountrySubdivision,
    CountrySubdivisionStatus,
)
from skmc_erp.core.tenant.model import Tenant


class CompanyLocationNotFoundError(Exception):
    """The Company is not visible within the resolved Tenant."""


class CompanyLocationInputError(Exception):
    """A supplied Location reference or relationship is invalid."""


class CompanyLocationStateConflictError(Exception):
    """The requested Location conflicts with current business state."""


async def create_company_location(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    location_data: CompanyLocationCreate,
) -> CompanyLocation:
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

    location = CompanyLocation(
        company_id=company.id,
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
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise CompanyLocationStateConflictError(
            "Company Location could not be created due to a data conflict"
        ) from exc

    await session.refresh(location)
    return location
