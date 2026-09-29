from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.core.company.model import (
    Company,
    CompanyLegalNameVersion,
    CompanyStatus,
)
from skmc_erp.core.company.schema import CompanyCreate, CompanyUpdate, validate_phone
from skmc_erp.core.currency.model import Currency, CurrencyStatus
from skmc_erp.core.entity_type.model import EntityType, EntityTypeStatus
from skmc_erp.core.geography.model import Country, CountryStatus
from skmc_erp.core.organisation.model import Organisation, OrganisationStatus
from skmc_erp.core.tenant.model import Tenant


class CompanyInputError(Exception):
    """A supplied Company reference or relationship is invalid."""


class CompanyStateConflictError(Exception):
    """A referenced record exists but cannot be used for creation."""


async def create_company(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_data: CompanyCreate,
) -> Company:
    organisation: Organisation | None = None
    if company_data.organisation_id is not None:
        organisation = await session.get(
            Organisation,
            company_data.organisation_id,
        )
        if organisation is None:
            raise CompanyInputError("Organisation does not exist")
        if organisation.tenant_id != tenant.id:
            raise CompanyInputError(
                "Organisation does not belong to the current Tenant"
            )
        if organisation.status is not OrganisationStatus.ACTIVE:
            raise CompanyStateConflictError("Organisation is not active")

    entity_type: EntityType | None = None
    if company_data.entity_type_id is not None:
        entity_type = await session.get(EntityType, company_data.entity_type_id)
        if entity_type is None:
            raise CompanyInputError("Entity Type does not exist")
        if entity_type.status is not EntityTypeStatus.ACTIVE:
            raise CompanyStateConflictError("Entity Type is not active")

    country: Country | None = None
    if company_data.country_code is not None:
        country = await session.get(Country, company_data.country_code)
        if country is None:
            raise CompanyInputError("Country does not exist")
        if country.status is not CountryStatus.ACTIVE:
            raise CompanyStateConflictError("Country is not active")

    if (
        entity_type is not None
        and country is not None
        and entity_type.country_code != country.code
    ):
        raise CompanyInputError(
            "Entity Type is not valid for the selected Country"
        )

    currency: Currency | None = None
    if company_data.base_currency_code is not None:
        currency = await session.get(Currency, company_data.base_currency_code)
        if currency is None:
            raise CompanyInputError("Currency does not exist")
        if currency.status is not CurrencyStatus.ACTIVE:
            raise CompanyStateConflictError("Currency is not active")

    company = Company(
        tenant_id=tenant.id,
        organisation_id=(organisation.id if organisation is not None else None),
        legal_name=company_data.legal_name,
        display_name=company_data.display_name,
        entity_type_id=(entity_type.id if entity_type is not None else None),
        country_code=(country.code if country is not None else None),
        email=company_data.email,
        phone=company_data.phone,
        website=company_data.website,
        base_timezone=company_data.base_timezone,
        base_currency_code=(currency.code if currency is not None else None),
        business_nature=company_data.business_nature,
        status=CompanyStatus.DRAFT,
    )
    session.add(company)

    try:
        await session.flush()
        session.add(
            CompanyLegalNameVersion(
                company_id=company.id,
                legal_name=company.legal_name,
                valid_from=date.today(),
                valid_to=None,
            )
        )
        await session.flush()
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise CompanyStateConflictError(
            "Company could not be created due to a data conflict"
        ) from exc

    await session.refresh(company)
    return company


async def list_companies(
    *, session: AsyncSession, tenant: Tenant
) -> Sequence[Company]:
    result = await session.scalars(
        select(Company)
        .where(Company.tenant_id == tenant.id)
        .order_by(Company.company_code)
    )
    return result.all()


async def get_company(
    *, session: AsyncSession, tenant: Tenant, company_id: UUID
) -> Company | None:
    return await session.scalar(
        select(Company).where(
            Company.id == company_id,
            Company.tenant_id == tenant.id,
        )
    )


async def update_company(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    company_data: CompanyUpdate,
    commit: bool = True,
) -> Company | None:
    company = await get_company(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    if company is None:
        return None
    if company.status is CompanyStatus.INACTIVE:
        raise CompanyStateConflictError("Inactive Company cannot be changed")

    changes = company_data.model_dump(exclude_unset=True)
    legal_name_changed = (
        "legal_name" in changes and changes["legal_name"] != company.legal_name
    )
    if legal_name_changed:
        current_version = await session.scalar(
            select(CompanyLegalNameVersion)
            .where(
                CompanyLegalNameVersion.company_id == company.id,
                CompanyLegalNameVersion.valid_to.is_(None),
            )
            .with_for_update()
        )
        if current_version is None:
            raise CompanyStateConflictError(
                "Company has no current legal-name version"
            )
        effective_date = date.today()
        if current_version.valid_from >= effective_date:
            raise CompanyStateConflictError(
                "Company legal name has already changed today"
            )
        current_version.valid_to = effective_date - timedelta(days=1)
        session.add(
            CompanyLegalNameVersion(
                company_id=company.id,
                legal_name=changes["legal_name"],
                valid_from=effective_date,
                valid_to=None,
            )
        )

    if "phone" in changes and changes["phone"] is not None:
        try:
            changes["phone"] = validate_phone(changes["phone"], company.country_code)
        except ValueError as exc:
            raise CompanyInputError("invalid phone number") from exc

    for field, value in changes.items():
        setattr(company, field, value)
    company.updated_at = datetime.now(UTC)

    try:
        await session.flush()
        if commit:
            await session.commit()
    except IntegrityError as exc:
        if commit:
            await session.rollback()
        raise CompanyStateConflictError(
            "Company could not be updated due to a data conflict"
        ) from exc

    if commit:
        await session.refresh(company)
    return company


async def list_company_legal_name_history(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
) -> Sequence[CompanyLegalNameVersion] | None:
    company = await get_company(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    if company is None:
        return None
    result = await session.scalars(
        select(CompanyLegalNameVersion)
        .where(CompanyLegalNameVersion.company_id == company.id)
        .order_by(
            CompanyLegalNameVersion.valid_from,
            CompanyLegalNameVersion.created_at,
            CompanyLegalNameVersion.id,
        )
    )
    return result.all()


async def inactivate_company(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
) -> Company | None:
    company = await get_company(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    if company is None:
        return None
    if company.status is CompanyStatus.INACTIVE:
        return company
    if company.status is not CompanyStatus.ACTIVE:
        raise CompanyStateConflictError(
            "Only an ACTIVE Company can be inactivated"
        )

    company.status = CompanyStatus.INACTIVE
    company.updated_at = datetime.now(UTC)

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise CompanyStateConflictError(
            "Company could not be inactivated due to a data conflict"
        ) from exc

    await session.refresh(company)
    return company
