from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.core.company.model import Company, CompanyStatus
from skmc_erp.core.company.schema import CompanyCreate
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
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise CompanyStateConflictError(
            "Company could not be created due to a data conflict"
        ) from exc

    await session.refresh(company)
    return company
