from datetime import UTC, date, datetime
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError

from skmc_erp.ar.catalogue.model import CatalogueStatus, ServiceType, Sku
from skmc_erp.ar.catalogue.service import (
    CatalogueInputError,
    CatalogueStateConflictError,
    validate_catalogue_tax_configuration,
)
from skmc_erp.ar.company_readiness.schema import (
    CompanyReadinessResponse,
    ReadinessCheck,
)
from skmc_erp.ar.document_presentation.model import (
    CompanyDocumentTemplate,
    DocumentPresentationStatus,
)
from skmc_erp.ar.document_presentation.schema import (
    CompanyDocumentTemplateSelection,
)
from skmc_erp.ar.numbering.model import (
    DocumentSequence,
    DocumentSequenceStatus,
    DocumentType,
)
from skmc_erp.ar.numbering.schema import DocumentSequenceCreate
from skmc_erp.ar.payment_term.model import PaymentTerm, PaymentTermStatus
from skmc_erp.ar.payment_term.schema import PaymentTermCreate
from skmc_erp.core.bank_account.model import (
    CompanyBankAccount,
    CompanyBankAccountStatus,
)
from skmc_erp.core.bank_account.schema import CompanyBankAccountCreate
from skmc_erp.core.company.model import (
    Company,
    CompanyBusinessNature,
    CompanyStatus,
)
from skmc_erp.core.company_gst_registration.model import (
    CompanyGSTRegistration,
    CompanyGSTRegistrationStatus,
    GSTRegistrationType,
    GSTRegistrationTypeStatus,
)
from skmc_erp.core.company_identifier.model import (
    CompanyIdentifier,
    CompanyIdentifierStatus,
    CompanyIdentifierType,
    CompanyIdentifierTypeStatus,
    EntityTypeIdentifierRule,
    IdentifierRequirementLevel,
)
from skmc_erp.core.company_location.model import (
    CompanyLocation,
    CompanyLocationStatus,
)
from skmc_erp.core.currency.model import Currency, CurrencyStatus
from skmc_erp.core.entity_type.model import EntityType, EntityTypeStatus
from skmc_erp.core.financial_year.model import (
    CompanyFiscalSettings,
    FinancialYear,
    FinancialYearStatus,
)
from skmc_erp.core.geography.model import (
    Country,
    CountryStatus,
    CountrySubdivision,
    CountrySubdivisionStatus,
)
from skmc_erp.core.tax_reference.model import HsnSacClassificationType
from skmc_erp.core.tenant.model import Tenant
from skmc_erp.core.uom.service import UomInputError, validate_uom_code


class CompanyActivationConflictError(Exception):
    def __init__(
        self,
        message: str,
        readiness: CompanyReadinessResponse | None = None,
    ) -> None:
        super().__init__(message)
        self.readiness = readiness


def _check(code: str, message: str) -> ReadinessCheck:
    return ReadinessCheck(code=code, message=message)


def _record(
    condition: bool,
    *,
    code: str,
    failure_message: str,
    success_message: str,
    blocking: list[ReadinessCheck],
    passed: list[ReadinessCheck],
) -> None:
    target = passed if condition else blocking
    target.append(_check(code, success_message if condition else failure_message))


async def _evaluate_identity(
    session: AsyncSession,
    company: Company,
    blocking: list[ReadinessCheck],
    passed: list[ReadinessCheck],
) -> None:
    _record(
        bool(company.legal_name and company.legal_name.strip()),
        code="COMPANY_LEGAL_NAME",
        failure_message="Company legal name is required",
        success_message="Company legal name is configured",
        blocking=blocking,
        passed=passed,
    )

    country = (
        await session.get(Country, company.country_code)
        if company.country_code is not None
        else None
    )
    country_valid = country is not None and country.status is CountryStatus.ACTIVE
    _record(
        country_valid,
        code="COMPANY_COUNTRY",
        failure_message="An active Company country is required",
        success_message="Company country is active",
        blocking=blocking,
        passed=passed,
    )

    entity_type = (
        await session.get(EntityType, company.entity_type_id)
        if company.entity_type_id is not None
        else None
    )
    entity_valid = (
        entity_type is not None
        and entity_type.status is EntityTypeStatus.ACTIVE
        and entity_type.country_code == company.country_code
    )
    _record(
        entity_valid,
        code="COMPANY_ENTITY_TYPE",
        failure_message=(
            "An active Entity Type compatible with the Company country is required"
        ),
        success_message="Company Entity Type is active and jurisdiction-compatible",
        blocking=blocking,
        passed=passed,
    )

    timezone_valid = False
    if company.base_timezone:
        try:
            ZoneInfo(company.base_timezone)
            timezone_valid = True
        except ZoneInfoNotFoundError:
            pass
    _record(
        timezone_valid,
        code="COMPANY_TIMEZONE",
        failure_message="A valid IANA Company base time zone is required",
        success_message="Company base time zone is valid",
        blocking=blocking,
        passed=passed,
    )

    currency = (
        await session.get(Currency, company.base_currency_code)
        if company.base_currency_code is not None
        else None
    )
    _record(
        currency is not None and currency.status is CurrencyStatus.ACTIVE,
        code="COMPANY_BASE_CURRENCY",
        failure_message="An active Company base currency is required",
        success_message="Company base currency is active",
        blocking=blocking,
        passed=passed,
    )

    _record(
        company.business_nature in {
            CompanyBusinessNature.SERVICES,
            CompanyBusinessNature.GOODS,
            CompanyBusinessNature.BOTH,
        },
        code="COMPANY_BUSINESS_NATURE",
        failure_message="Company Business Nature must be SERVICES, GOODS, or BOTH",
        success_message="Company Business Nature is configured",
        blocking=blocking,
        passed=passed,
    )

    if not country_valid or not entity_valid:
        return

    identifier_rows = (
        await session.execute(
            select(CompanyIdentifierType, CompanyIdentifier)
            .outerjoin(
                CompanyIdentifier,
                (CompanyIdentifier.identifier_type_id == CompanyIdentifierType.id)
                & (CompanyIdentifier.company_id == company.id)
                & (CompanyIdentifier.status == CompanyIdentifierStatus.ACTIVE),
            )
            .where(
                CompanyIdentifierType.country_code == company.country_code,
                CompanyIdentifierType.status == CompanyIdentifierTypeStatus.ACTIVE,
            )
        )
    ).all()
    identifiers = {
        identifier_type.code: identifier
        for identifier_type, identifier in identifier_rows
    }
    _record(
        identifiers.get("PAN") is not None,
        code="MISSING_PAN",
        failure_message="An active PAN Company Identifier is required",
        success_message="An active PAN Company Identifier is configured",
        blocking=blocking,
        passed=passed,
    )

    required_rows = (
        await session.execute(
            select(CompanyIdentifierType, CompanyIdentifier)
            .join(
                EntityTypeIdentifierRule,
                EntityTypeIdentifierRule.identifier_type_id
                == CompanyIdentifierType.id,
            )
            .outerjoin(
                CompanyIdentifier,
                (CompanyIdentifier.identifier_type_id == CompanyIdentifierType.id)
                & (CompanyIdentifier.company_id == company.id)
                & (CompanyIdentifier.status == CompanyIdentifierStatus.ACTIVE),
            )
            .where(
                EntityTypeIdentifierRule.entity_type_id == entity_type.id,
                EntityTypeIdentifierRule.requirement_level
                == IdentifierRequirementLevel.REQUIRED,
                CompanyIdentifierType.code != "PAN",
            )
            .order_by(CompanyIdentifierType.code)
        )
    ).all()
    missing_required = [
        identifier_type.code
        for identifier_type, identifier in required_rows
        if identifier is None
        or identifier_type.status is not CompanyIdentifierTypeStatus.ACTIVE
        or identifier_type.country_code != company.country_code
    ]
    _record(
        not missing_required,
        code="MISSING_REQUIRED_ENTITY_IDENTIFIER",
        failure_message=(
            "Missing active required Entity Type identifiers: "
            + ", ".join(missing_required)
        ),
        success_message="All Entity Type-required identifiers are configured",
        blocking=blocking,
        passed=passed,
    )


async def _evaluate_registered_office(
    session: AsyncSession,
    company: Company,
    blocking: list[ReadinessCheck],
    passed: list[ReadinessCheck],
) -> None:
    office = await session.scalar(
        select(CompanyLocation).where(
            CompanyLocation.company_id == company.id,
            CompanyLocation.status == CompanyLocationStatus.ACTIVE,
            CompanyLocation.is_registered_office.is_(True),
        )
    )
    usable = False
    if office is not None:
        country = await session.get(Country, office.country_code)
        subdivision_valid = True
        if office.subdivision_code is not None:
            subdivision = await session.scalar(
                select(CountrySubdivision).where(
                    CountrySubdivision.code == office.subdivision_code,
                    CountrySubdivision.country_code == office.country_code,
                )
            )
            subdivision_valid = (
                subdivision is not None
                and subdivision.status is CountrySubdivisionStatus.ACTIVE
            )
        usable = (
            bool(office.location_code.strip())
            and bool(office.location_name.strip())
            and bool(office.address_line_1.strip())
            and bool(office.city.strip())
            and country is not None
            and country.status is CountryStatus.ACTIVE
            and subdivision_valid
        )
    _record(
        usable,
        code="MISSING_REGISTERED_OFFICE",
        failure_message="A usable active Registered Office is required",
        success_message="A usable active Registered Office is configured",
        blocking=blocking,
        passed=passed,
    )


async def _evaluate_fiscal(
    session: AsyncSession,
    company: Company,
    as_of: date,
    blocking: list[ReadinessCheck],
    passed: list[ReadinessCheck],
) -> FinancialYear | None:
    settings = await session.get(CompanyFiscalSettings, company.id)
    _record(
        settings is not None,
        code="MISSING_FISCAL_SETTINGS",
        failure_message="Company Fiscal Settings are required",
        success_message="Company Fiscal Settings are configured",
        blocking=blocking,
        passed=passed,
    )
    financial_year = await session.scalar(
        select(FinancialYear).where(
            FinancialYear.company_id == company.id,
            FinancialYear.start_date <= as_of,
            FinancialYear.end_date >= as_of,
            FinancialYear.status == FinancialYearStatus.OPEN,
        )
    )
    _record(
        financial_year is not None,
        code="MISSING_CURRENT_FINANCIAL_YEAR",
        failure_message="An OPEN Financial Year covering the current date is required",
        success_message="An OPEN current Financial Year is configured",
        blocking=blocking,
        passed=passed,
    )
    return financial_year


async def _evaluate_gst(
    session: AsyncSession,
    company: Company,
    as_of: date,
    blocking: list[ReadinessCheck],
    passed: list[ReadinessCheck],
) -> None:
    registrations = (
        await session.scalars(
            select(CompanyGSTRegistration).where(
                CompanyGSTRegistration.company_id == company.id,
                CompanyGSTRegistration.status
                == CompanyGSTRegistrationStatus.ACTIVE,
            )
        )
    ).all()
    _record(
        bool(registrations),
        code="MISSING_GST_REGISTRATION",
        failure_message="At least one active Company GST Registration is required",
        success_message="An active Company GST Registration is configured",
        blocking=blocking,
        passed=passed,
    )
    if not registrations:
        return

    invalid: list[str] = []
    unmapped: list[str] = []
    for registration in registrations:
        registration_type = (
            await session.get(
                GSTRegistrationType, registration.gst_registration_type_id
            )
            if registration.gst_registration_type_id is not None
            else None
        )
        subdivision = await session.scalar(
            select(CountrySubdivision).where(
                CountrySubdivision.code == registration.subdivision_code,
                CountrySubdivision.country_code == "IN",
            )
        )
        if (
            company.country_code != "IN"
            or registration_type is None
            or registration_type.status is not GSTRegistrationTypeStatus.ACTIVE
            or subdivision is None
            or subdivision.status is not CountrySubdivisionStatus.ACTIVE
            or subdivision.gst_state_code is None
            or not registration.gstin.startswith(subdivision.gst_state_code)
            or (registration.valid_from is not None and registration.valid_from > as_of)
            or (registration.valid_to is not None and registration.valid_to < as_of)
        ):
            invalid.append(registration.gstin)
        mapped_location = await session.scalar(
            select(CompanyLocation.id).where(
                CompanyLocation.company_id == company.id,
                CompanyLocation.gst_registration_id == registration.id,
                CompanyLocation.status == CompanyLocationStatus.ACTIVE,
                CompanyLocation.subdivision_code == registration.subdivision_code,
            )
        )
        if mapped_location is None:
            unmapped.append(registration.gstin)

    _record(
        not invalid,
        code="INVALID_ACTIVE_GST_REGISTRATION",
        failure_message="Invalid active GST Registrations: " + ", ".join(invalid),
        success_message="All active GST Registrations are currently usable",
        blocking=blocking,
        passed=passed,
    )
    _record(
        not unmapped,
        code="MISSING_GST_LOCATION_MAPPING",
        failure_message=(
            "Active GST Registrations without an active mapped Location: "
            + ", ".join(unmapped)
        ),
        success_message="Every active GST Registration has an active mapped Location",
        blocking=blocking,
        passed=passed,
    )


async def _catalogue_item_is_ready(
    session: AsyncSession,
    company: Company,
    item: ServiceType | Sku,
) -> bool:
    expected = (
        HsnSacClassificationType.SAC
        if isinstance(item, ServiceType)
        else HsnSacClassificationType.HSN
    )
    try:
        await validate_catalogue_tax_configuration(
            session=session,
            company=company,
            hsn_sac_code_id=item.company_hsn_sac_code_id,
            expected_classification=expected,
            base_tax_treatment_id=item.base_tax_treatment_id,
            tax_rate_id=item.selected_tax_rate_id,
        )
        if item.uom is not None:
            await validate_uom_code(session=session, uom_code=item.uom)
        elif isinstance(item, Sku):
            return False
    except (CatalogueInputError, CatalogueStateConflictError, UomInputError):
        return False
    return True


async def _evaluate_catalogue(
    session: AsyncSession,
    company: Company,
    blocking: list[ReadinessCheck],
    passed: list[ReadinessCheck],
) -> None:
    services = (
        await session.scalars(
            select(ServiceType).where(
                ServiceType.company_id == company.id,
                ServiceType.status == CatalogueStatus.ACTIVE,
            )
        )
    ).all()
    skus = (
        await session.scalars(
            select(Sku).where(
                Sku.company_id == company.id,
                Sku.status == CatalogueStatus.ACTIVE,
            )
        )
    ).all()
    needs_services = company.business_nature in {
        CompanyBusinessNature.SERVICES,
        CompanyBusinessNature.BOTH,
    }
    needs_skus = company.business_nature in {
        CompanyBusinessNature.GOODS,
        CompanyBusinessNature.BOTH,
    }
    if needs_services:
        _record(
            bool(services),
            code="MISSING_SERVICE_CATALOGUE",
            failure_message="At least one active billing-ready Service Type is required",
            success_message="The active Service catalogue is present",
            blocking=blocking,
            passed=passed,
        )
    if needs_skus:
        _record(
            bool(skus),
            code="MISSING_SKU_CATALOGUE",
            failure_message="At least one active billing-ready SKU is required",
            success_message="The active SKU catalogue is present",
            blocking=blocking,
            passed=passed,
        )

    incomplete: list[str] = []
    for item in [*services, *skus]:
        if not await _catalogue_item_is_ready(session, company, item):
            item_type = "Service Type" if isinstance(item, ServiceType) else "SKU"
            incomplete.append(f"{item_type} {item.id}")
    _record(
        not incomplete,
        code="INCOMPLETE_ACTIVE_CATALOGUE_ITEM",
        failure_message="Incomplete active catalogue items: " + ", ".join(incomplete),
        success_message="Every active catalogue item is billing-ready",
        blocking=blocking,
        passed=passed,
    )


async def _evaluate_defaults(
    session: AsyncSession,
    company: Company,
    blocking: list[ReadinessCheck],
    passed: list[ReadinessCheck],
) -> None:
    terms = (
        await session.scalars(
            select(PaymentTerm).where(
                PaymentTerm.company_id == company.id,
                PaymentTerm.status == PaymentTermStatus.ACTIVE,
            )
        )
    ).all()
    usable_terms: list[PaymentTerm] = []
    for term in terms:
        try:
            PaymentTermCreate(
                name=term.name,
                code=term.code,
                term_type=term.term_type,
                credit_days=term.credit_days,
                is_default=term.is_default,
            )
            usable_terms.append(term)
        except ValidationError:
            pass
    active_term = next(iter(usable_terms), None)
    default_term = next((term for term in usable_terms if term.is_default), None)
    _record(
        active_term is not None,
        code="MISSING_PAYMENT_TERM",
        failure_message="At least one active usable Company Payment Term is required",
        success_message="An active usable Company Payment Term is configured",
        blocking=blocking,
        passed=passed,
    )
    _record(
        default_term is not None,
        code="MISSING_DEFAULT_PAYMENT_TERM",
        failure_message="An active usable default Company Payment Term is required",
        success_message="An active usable default Company Payment Term is configured",
        blocking=blocking,
        passed=passed,
    )

    banks = (
        await session.scalars(
            select(CompanyBankAccount).where(
                CompanyBankAccount.company_id == company.id,
                CompanyBankAccount.status == CompanyBankAccountStatus.ACTIVE,
            )
        )
    ).all()
    usable_banks: list[CompanyBankAccount] = []
    for bank in banks:
        bank_country = (
            await session.get(Country, bank.bank_country_code)
            if bank.bank_country_code is not None
            else None
        )
        bank_currency = await session.get(Currency, bank.currency_code)
        if (
            bank_country is None
            or bank_country.status is not CountryStatus.ACTIVE
            or bank_currency is None
            or bank_currency.status is not CurrencyStatus.ACTIVE
        ):
            continue
        try:
            CompanyBankAccountCreate(
                bank_country_code=bank.bank_country_code,
                account_holder_name=bank.account_holder_name,
                bank_name=bank.bank_name,
                account_number=bank.account_number,
                branch_name=bank.branch_name,
                ifsc=bank.ifsc,
                swift=bank.swift,
                iban=bank.iban,
                currency_code=bank.currency_code,
                account_type=bank.account_type,
                gl_account_id=None,
                is_default_for_billing=bank.is_default_for_billing,
            )
            usable_banks.append(bank)
        except ValidationError:
            pass
    active_bank = next(iter(usable_banks), None)
    default_bank = next(
        (bank for bank in usable_banks if bank.is_default_for_billing), None
    )
    _record(
        active_bank is not None,
        code="MISSING_BANK_ACCOUNT",
        failure_message="At least one active usable Company Bank Account is required",
        success_message="An active usable Company Bank Account is configured",
        blocking=blocking,
        passed=passed,
    )
    _record(
        default_bank is not None,
        code="MISSING_DEFAULT_BILLING_BANK",
        failure_message="An active usable default billing Bank Account is required",
        success_message="An active usable default billing Bank Account is configured",
        blocking=blocking,
        passed=passed,
    )


async def _evaluate_numbering_and_presentation(
    session: AsyncSession,
    company: Company,
    financial_year: FinancialYear | None,
    blocking: list[ReadinessCheck],
    passed: list[ReadinessCheck],
) -> None:
    for document_type in DocumentType:
        sequences: list[DocumentSequence] = []
        if financial_year is not None:
            sequences = list(
                (
                    await session.scalars(
                        select(DocumentSequence).where(
                            DocumentSequence.company_id == company.id,
                            DocumentSequence.financial_year_id
                            == financial_year.id,
                            DocumentSequence.document_type == document_type,
                            DocumentSequence.status
                            == DocumentSequenceStatus.ACTIVE,
                        )
                    )
                ).all()
            )
        usable_sequence = False
        for sequence in sequences:
            try:
                DocumentSequenceCreate(
                    financial_year_id=sequence.financial_year_id,
                    document_type=sequence.document_type,
                    series_name=sequence.series_name,
                    format=sequence.format,
                    prefix=sequence.prefix,
                    start_number=sequence.start_number,
                    next_number=sequence.next_number,
                    padding=sequence.padding,
                    priority=sequence.priority,
                )
                usable_sequence = True
                break
            except ValidationError:
                pass
        _record(
            usable_sequence,
            code=f"MISSING_{document_type.value}_NUMBERING",
            failure_message=(
                f"Active {document_type.value} numbering is required for the "
                "current Financial Year"
            ),
            success_message=(
                f"Active {document_type.value} numbering is configured for the "
                "current Financial Year"
            ),
            blocking=blocking,
            passed=passed,
        )

    templates = (
        await session.scalars(
            select(CompanyDocumentTemplate).where(
                CompanyDocumentTemplate.company_id == company.id,
                CompanyDocumentTemplate.document_type.is_(None),
                CompanyDocumentTemplate.status
                == DocumentPresentationStatus.ACTIVE,
            )
        )
    ).all()
    usable_template = False
    for template in templates:
        try:
            CompanyDocumentTemplateSelection(template_key=template.template_key)
            usable_template = True
            break
        except ValidationError:
            pass
    _record(
        usable_template,
        code="MISSING_DOCUMENT_PRESENTATION",
        failure_message="An active usable Company-wide document presentation is required",
        success_message="An active usable Company-wide document presentation is configured",
        blocking=blocking,
        passed=passed,
    )


async def evaluate_company_readiness(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    company: Company | None = None,
    as_of: date | None = None,
) -> CompanyReadinessResponse | None:
    if company is None:
        company = await session.scalar(
            select(Company).where(
                Company.id == company_id,
                Company.tenant_id == tenant.id,
            )
        )
    elif company.id != company_id or company.tenant_id != tenant.id:
        return None
    if company is None:
        return None

    blocking: list[ReadinessCheck] = []
    passed: list[ReadinessCheck] = []
    warnings: list[ReadinessCheck] = []
    if company.status is CompanyStatus.INACTIVE:
        blocking.append(
            _check("COMPANY_INACTIVE", "Inactive Company cannot be reactivated")
        )
    else:
        passed.append(
            _check("COMPANY_LIFECYCLE", "Company lifecycle permits activation")
        )

    current_date = as_of or date.today()
    await _evaluate_identity(session, company, blocking, passed)
    await _evaluate_registered_office(session, company, blocking, passed)
    financial_year = await _evaluate_fiscal(
        session, company, current_date, blocking, passed
    )
    await _evaluate_gst(session, company, current_date, blocking, passed)
    await _evaluate_catalogue(session, company, blocking, passed)
    await _evaluate_defaults(session, company, blocking, passed)
    await _evaluate_numbering_and_presentation(
        session, company, financial_year, blocking, passed
    )
    return CompanyReadinessResponse(
        company_id=company.id,
        status=company.status,
        ready_for_activation=not blocking,
        blocking_checks=blocking,
        passed_checks=passed,
        non_blocking_warnings=warnings,
    )


async def activate_company(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
) -> Company | None:
    company = await session.scalar(
        select(Company)
        .where(Company.id == company_id, Company.tenant_id == tenant.id)
        .with_for_update()
    )
    if company is None:
        return None
    readiness = await evaluate_company_readiness(
        session=session,
        tenant=tenant,
        company_id=company_id,
        company=company,
    )
    if readiness is None:
        return None
    if not readiness.ready_for_activation:
        raise CompanyActivationConflictError(
            "Company is not ready for activation", readiness
        )
    if company.status is CompanyStatus.ACTIVE:
        return company
    if company.status is not CompanyStatus.DRAFT:
        raise CompanyActivationConflictError(
            "Only a DRAFT Company can be activated", readiness
        )
    company.status = CompanyStatus.ACTIVE
    company.updated_at = datetime.now(UTC)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise CompanyActivationConflictError(
            "Company could not be activated due to a data conflict"
        ) from exc
    await session.refresh(company)
    return company
