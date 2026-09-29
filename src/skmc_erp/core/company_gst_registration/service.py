from collections.abc import Sequence
from datetime import UTC, datetime
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
    CompanyGSTRegistrationUpdate,
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
    commit: bool = True,
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
        if commit:
            await session.commit()
    except IntegrityError as exc:
        if commit:
            await session.rollback()
        raise CompanyGSTRegistrationStateConflictError(
            "GST Registration could not be created due to a data conflict"
        ) from exc

    if commit:
        await session.refresh(registration)
    return registration


async def list_company_gst_registrations(
    *, session: AsyncSession, tenant: Tenant, company_id: UUID
) -> Sequence[CompanyGSTRegistration]:
    company = await session.scalar(
        select(Company).where(
            Company.id == company_id, Company.tenant_id == tenant.id
        )
    )
    if company is None:
        return []
    result = await session.scalars(
        select(CompanyGSTRegistration)
        .where(CompanyGSTRegistration.company_id == company_id)
        .order_by(CompanyGSTRegistration.gstin)
    )
    return result.all()


async def get_company_gst_registration(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    registration_id: UUID,
) -> CompanyGSTRegistration | None:
    return await session.scalar(
        select(CompanyGSTRegistration)
        .join(Company, CompanyGSTRegistration.company_id == Company.id)
        .where(
            CompanyGSTRegistration.id == registration_id,
            CompanyGSTRegistration.company_id == company_id,
            Company.tenant_id == tenant.id,
        )
    )


async def update_company_gst_registration(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    registration_id: UUID,
    registration_data: CompanyGSTRegistrationUpdate,
    commit: bool = True,
) -> CompanyGSTRegistration | None:
    registration = await get_company_gst_registration(
        session=session,
        tenant=tenant,
        company_id=company_id,
        registration_id=registration_id,
    )
    if registration is None:
        return None
    if registration.status is CompanyGSTRegistrationStatus.INACTIVE:
        raise CompanyGSTRegistrationStateConflictError(
            "Inactive GST Registration cannot be changed"
        )
    changes = registration_data.model_dump(exclude_unset=True)
    candidate_from = changes.get("valid_from", registration.valid_from)
    candidate_to = changes.get("valid_to", registration.valid_to)
    if (
        candidate_from is not None
        and candidate_to is not None
        and candidate_to < candidate_from
    ):
        raise CompanyGSTRegistrationInputError(
            "valid_to must be on or after valid_from"
        )
    if "gst_registration_type_id" in changes and changes["gst_registration_type_id"] is not None:
        registration_type = await session.get(
            GSTRegistrationType, changes["gst_registration_type_id"]
        )
        if registration_type is None:
            raise CompanyGSTRegistrationInputError(
                "GST Registration Type does not exist"
            )
        if registration_type.status is not GSTRegistrationTypeStatus.ACTIVE:
            raise CompanyGSTRegistrationStateConflictError(
                "GST Registration Type is not active"
            )
    if (
        registration.status is CompanyGSTRegistrationStatus.ACTIVE
        and "gst_registration_type_id" in changes
        and changes["gst_registration_type_id"] is None
    ):
        raise CompanyGSTRegistrationStateConflictError(
            "An active GST Registration requires a Registration Type"
        )
    for field, value in changes.items():
        setattr(registration, field, value)
    registration.updated_at = datetime.now(UTC)
    try:
        await session.flush()
        if commit:
            await session.commit()
    except IntegrityError as exc:
        if commit:
            await session.rollback()
        raise CompanyGSTRegistrationStateConflictError(
            "GST Registration could not be updated due to a data conflict"
        ) from exc
    if commit:
        await session.refresh(registration)
    return registration


async def transition_company_gst_registration(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    registration_id: UUID,
    target_status: CompanyGSTRegistrationStatus,
) -> CompanyGSTRegistration | None:
    registration = await get_company_gst_registration(
        session=session,
        tenant=tenant,
        company_id=company_id,
        registration_id=registration_id,
    )
    if registration is None:
        return None
    allowed = {
        CompanyGSTRegistrationStatus.DRAFT: CompanyGSTRegistrationStatus.ACTIVE,
        CompanyGSTRegistrationStatus.ACTIVE: CompanyGSTRegistrationStatus.INACTIVE,
    }
    if allowed.get(registration.status) is not target_status:
        raise CompanyGSTRegistrationStateConflictError(
            f"GST Registration cannot transition from {registration.status.value} "
            f"to {target_status.value}"
        )
    if (
        target_status is CompanyGSTRegistrationStatus.ACTIVE
        and registration.gst_registration_type_id is None
    ):
        raise CompanyGSTRegistrationStateConflictError(
            "GST Registration Type is required before activation"
        )
    if target_status is CompanyGSTRegistrationStatus.ACTIVE:
        registration_type = await session.get(
            GSTRegistrationType, registration.gst_registration_type_id
        )
        if (
            registration_type is None
            or registration_type.status is not GSTRegistrationTypeStatus.ACTIVE
        ):
            raise CompanyGSTRegistrationStateConflictError(
                "GST Registration Type is not active"
            )
    registration.status = target_status
    registration.updated_at = datetime.now(UTC)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise CompanyGSTRegistrationStateConflictError(
            "GST Registration transition conflicts with existing Company configuration"
        ) from exc
    await session.refresh(registration)
    return registration
