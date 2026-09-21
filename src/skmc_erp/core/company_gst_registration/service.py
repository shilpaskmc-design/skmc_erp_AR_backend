from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.core.company.model import Company, CompanyStatus
from skmc_erp.core.company_gst_registration.model import (
    CompanyGSTRegistration,
    CompanyGSTRegistrationStatus,
    GSTRegistrationType,
    GSTRegistrationTypeStatus,
)
from skmc_erp.core.company_gst_registration.schema import (
    CompanyGSTRegistrationCreate,
)
from skmc_erp.core.geography.model import (
    CountrySubdivision,
    CountrySubdivisionStatus,
)
from skmc_erp.core.tenant.model import Tenant


class CompanyGSTRegistrationNotFoundError(Exception):
    """The Company is not visible within the resolved Tenant."""


class CompanyGSTRegistrationInputError(Exception):
    """A supplied GST Registration value or reference is invalid."""


class CompanyGSTRegistrationStateConflictError(Exception):
    """The requested registration conflicts with current business state."""


async def create_company_gst_registration(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    registration_data: CompanyGSTRegistrationCreate,
) -> CompanyGSTRegistration:
    company = await session.scalar(
        select(Company).where(
            Company.id == company_id,
            Company.tenant_id == tenant.id,
        )
    )
    if company is None:
        raise CompanyGSTRegistrationNotFoundError("Company not found")
    if company.status is CompanyStatus.INACTIVE:
        raise CompanyGSTRegistrationStateConflictError("Company is inactive")
    if company.country_code != "IN":
        raise CompanyGSTRegistrationStateConflictError(
            "Company must be registered in India"
        )

    subdivision = await session.scalar(
        select(CountrySubdivision).where(
            CountrySubdivision.code == registration_data.subdivision_code
        )
    )
    if subdivision is None:
        raise CompanyGSTRegistrationInputError(
            "Country Subdivision does not exist"
        )
    if subdivision.status is not CountrySubdivisionStatus.ACTIVE:
        raise CompanyGSTRegistrationStateConflictError(
            "Country Subdivision is not active"
        )
    if subdivision.country_code != "IN":
        raise CompanyGSTRegistrationInputError(
            "GST Registration requires an Indian State or Union Territory"
        )
    if subdivision.gst_state_code is None:
        raise CompanyGSTRegistrationStateConflictError(
            "Country Subdivision has no GST State code"
        )
    if not registration_data.gstin.startswith(subdivision.gst_state_code):
        raise CompanyGSTRegistrationInputError(
            "GSTIN State code does not match the selected Country Subdivision"
        )

    registration_type: GSTRegistrationType | None = None
    if registration_data.gst_registration_type_id is not None:
        registration_type = await session.get(
            GSTRegistrationType,
            registration_data.gst_registration_type_id,
        )
        if registration_type is None:
            raise CompanyGSTRegistrationInputError(
                "GST Registration Type does not exist"
            )
        if registration_type.status is not GSTRegistrationTypeStatus.ACTIVE:
            raise CompanyGSTRegistrationStateConflictError(
                "GST Registration Type is not active"
            )

    registration = CompanyGSTRegistration(
        company_id=company.id,
        gstin=registration_data.gstin,
        registered_legal_name=registration_data.registered_legal_name,
        gst_registration_type_id=(
            registration_type.id if registration_type is not None else None
        ),
        subdivision_code=subdivision.code,
        valid_from=registration_data.valid_from,
        valid_to=registration_data.valid_to,
        status=CompanyGSTRegistrationStatus.DRAFT,
    )
    session.add(registration)

    try:
        await session.flush()
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise CompanyGSTRegistrationStateConflictError(
            "GST Registration could not be created due to a data conflict"
        ) from exc

    await session.refresh(registration)
    return registration
