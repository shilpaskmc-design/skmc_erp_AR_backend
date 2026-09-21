from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.core.company.model import Company, CompanyStatus
from skmc_erp.core.financial_year.model import (
    CompanyFiscalSettings,
    FinancialYear,
    FinancialYearStatus,
    FiscalYearPattern,
)
from skmc_erp.core.financial_year.schema import (
    CompanyFiscalSettingsUpdate,
    FinancialYearCreate,
)
from skmc_erp.core.tenant.model import Tenant


class FinancialYearNotFoundError(Exception):
    """The Company is not visible within the resolved Tenant."""


class FinancialYearInputError(Exception):
    """Supplied Financial Year input is invalid."""


class FinancialYearStateConflictError(Exception):
    """The requested operation conflicts with current fiscal state."""


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
        raise FinancialYearNotFoundError("Company not found")
    if company.status is CompanyStatus.INACTIVE:
        raise FinancialYearStateConflictError("Company is inactive")
    return company


def resolve_fiscal_start(
    settings_data: CompanyFiscalSettingsUpdate,
) -> tuple[int, int]:
    if settings_data.fiscal_year_pattern is FiscalYearPattern.APR_MAR:
        return 4, 1
    if settings_data.fiscal_year_pattern is FiscalYearPattern.JAN_DEC:
        return 1, 1

    if (
        settings_data.custom_fiscal_year_start_month is None
        or settings_data.custom_fiscal_year_start_day is None
    ):
        raise FinancialYearInputError("CUSTOM fiscal settings are incomplete")
    return (
        settings_data.custom_fiscal_year_start_month,
        settings_data.custom_fiscal_year_start_day,
    )


def calculate_financial_year_dates(
    *,
    start_year: int,
    start_month: int,
    start_day: int,
) -> tuple[date, date]:
    start_date = date(start_year, start_month, start_day)
    next_start_date = date(start_year + 1, start_month, start_day)
    return start_date, next_start_date - timedelta(days=1)


def generate_financial_year_code(start_date: date, end_date: date) -> str:
    if (
        start_date.month == 1
        and start_date.day == 1
        and end_date.year == start_date.year
    ):
        return f"FY{start_date.year}"
    return f"FY{start_date.year}-{end_date.year % 100:02d}"


async def configure_company_fiscal_settings(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    settings_data: CompanyFiscalSettingsUpdate,
) -> CompanyFiscalSettings:
    company = await _get_tenant_company(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    start_month, start_day = resolve_fiscal_start(settings_data)

    settings = await session.get(CompanyFiscalSettings, company.id)
    if settings is None:
        settings = CompanyFiscalSettings(
            company_id=company.id,
            fiscal_year_pattern=settings_data.fiscal_year_pattern,
            start_month=start_month,
            start_day=start_day,
        )
        session.add(settings)
    else:
        settings.fiscal_year_pattern = settings_data.fiscal_year_pattern
        settings.start_month = start_month
        settings.start_day = start_day
        settings.updated_at = datetime.now(UTC)

    try:
        await session.flush()
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise FinancialYearStateConflictError(
            "Fiscal settings could not be saved due to a data conflict"
        ) from exc

    await session.refresh(settings)
    return settings


async def create_financial_year(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    financial_year_data: FinancialYearCreate,
) -> FinancialYear:
    company = await _get_tenant_company(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    settings = await session.get(CompanyFiscalSettings, company.id)
    if settings is None:
        raise FinancialYearStateConflictError(
            "Company fiscal settings are not configured"
        )

    start_date, end_date = calculate_financial_year_dates(
        start_year=financial_year_data.start_year,
        start_month=settings.start_month,
        start_day=settings.start_day,
    )
    overlap_id = await session.scalar(
        select(FinancialYear.id)
        .where(
            FinancialYear.company_id == company.id,
            FinancialYear.start_date <= end_date,
            FinancialYear.end_date >= start_date,
        )
        .limit(1)
    )
    if overlap_id is not None:
        raise FinancialYearStateConflictError(
            "Financial Year overlaps an existing Financial Year"
        )

    financial_year = FinancialYear(
        company_id=company.id,
        start_date=start_date,
        end_date=end_date,
        display_code=generate_financial_year_code(start_date, end_date),
        is_transition=False,
        status=FinancialYearStatus.DRAFT,
    )
    session.add(financial_year)

    try:
        await session.flush()
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise FinancialYearStateConflictError(
            "Financial Year could not be created due to a data conflict"
        ) from exc

    await session.refresh(financial_year)
    return financial_year
