from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.ar.currency.model import CompanyARCurrency, CompanyARCurrencyStatus
from skmc_erp.ar.currency.schema import CompanyARCurrencyCreate, CompanyARCurrencyUpdate
from skmc_erp.core.company.model import Company
from skmc_erp.core.currency.model import Currency
from skmc_erp.core.tenant.model import Tenant


class CompanyARCurrencyInputError(Exception):
    pass


class CompanyARCurrencyStateConflictError(Exception):
    pass


async def enable_company_currency(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    currency_data: CompanyARCurrencyCreate,
) -> CompanyARCurrency:
    company = await session.get(Company, company_id)
    if company is None or company.tenant_id != tenant.id:
        raise CompanyARCurrencyInputError("Company does not exist")

    currency = await session.get(Currency, currency_data.currency_code)
    if currency is None:
        raise CompanyARCurrencyInputError("Currency does not exist")

    # The database constraints enforce logic such as:
    # "NOT is_default_billing OR billing_enabled"
    # "NOT is_default_receipt OR receipt_enabled"
    # We validate this upfront to provide better error messages.
    if currency_data.is_default_billing and not currency_data.billing_enabled:
        raise CompanyARCurrencyInputError(
            "Currency must be billing_enabled to be the default billing currency"
        )
    if currency_data.is_default_receipt and not currency_data.receipt_enabled:
        raise CompanyARCurrencyInputError(
            "Currency must be receipt_enabled to be the default receipt currency"
        )

    if not currency_data.billing_enabled and not currency_data.receipt_enabled:
        raise CompanyARCurrencyInputError(
            "An ACTIVE currency must have either billing_enabled or receipt_enabled set to True"
        )

    company_currency = CompanyARCurrency(
        company_id=company.id,
        currency_code=currency_data.currency_code,
        billing_enabled=currency_data.billing_enabled,
        receipt_enabled=currency_data.receipt_enabled,
        is_default_billing=currency_data.is_default_billing,
        is_default_receipt=currency_data.is_default_receipt,
        status=CompanyARCurrencyStatus.ACTIVE,
    )
    session.add(company_currency)

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise CompanyARCurrencyStateConflictError(
            "Currency could not be enabled due to a data conflict, such as a duplicate currency code or active default"
        ) from exc

    await session.refresh(company_currency)
    return company_currency


async def get_company_currency(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    currency_id: UUID,
) -> CompanyARCurrency | None:
    stmt = (
        select(CompanyARCurrency)
        .join(Company, CompanyARCurrency.company_id == Company.id)
        .where(
            CompanyARCurrency.id == currency_id,
            CompanyARCurrency.company_id == company_id,
            Company.tenant_id == tenant.id,
        )
    )
    return await session.scalar(stmt)


async def list_company_currencies(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
) -> Sequence[CompanyARCurrency]:
    company = await session.get(Company, company_id)
    if company is None or company.tenant_id != tenant.id:
        return []

    stmt = (
        select(CompanyARCurrency)
        .where(CompanyARCurrency.company_id == company_id)
        .order_by(CompanyARCurrency.currency_code)
    )
    result = await session.scalars(stmt)
    return result.all()


async def update_company_currency(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    currency_id: UUID,
    update_data: CompanyARCurrencyUpdate,
) -> CompanyARCurrency | None:
    company_currency = await get_company_currency(
        session=session,
        tenant=tenant,
        company_id=company_id,
        currency_id=currency_id,
    )
    if company_currency is None:
        return None

    # Apply updates
    billing_enabled = (
        update_data.billing_enabled
        if update_data.billing_enabled is not None
        else company_currency.billing_enabled
    )
    receipt_enabled = (
        update_data.receipt_enabled
        if update_data.receipt_enabled is not None
        else company_currency.receipt_enabled
    )
    is_default_billing = (
        update_data.is_default_billing
        if update_data.is_default_billing is not None
        else company_currency.is_default_billing
    )
    is_default_receipt = (
        update_data.is_default_receipt
        if update_data.is_default_receipt is not None
        else company_currency.is_default_receipt
    )

    if is_default_billing and not billing_enabled:
        raise CompanyARCurrencyInputError(
            "Currency must be billing_enabled to be the default billing currency"
        )
    if is_default_receipt and not receipt_enabled:
        raise CompanyARCurrencyInputError(
            "Currency must be receipt_enabled to be the default receipt currency"
        )

    # Allow disabling both only if status is going to be INACTIVE, but we don't expose status update here.
    # Therefore, if active, it must have at least one enabled.
    if company_currency.status == CompanyARCurrencyStatus.ACTIVE and not billing_enabled and not receipt_enabled:
        raise CompanyARCurrencyInputError(
            "An ACTIVE currency must have either billing_enabled or receipt_enabled set to True"
        )

    if update_data.billing_enabled is not None:
        company_currency.billing_enabled = update_data.billing_enabled
    if update_data.receipt_enabled is not None:
        company_currency.receipt_enabled = update_data.receipt_enabled
    if update_data.is_default_billing is not None:
        company_currency.is_default_billing = update_data.is_default_billing
    if update_data.is_default_receipt is not None:
        company_currency.is_default_receipt = update_data.is_default_receipt

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise CompanyARCurrencyStateConflictError(
            "Currency could not be updated due to a data conflict, such as a duplicate active default"
        ) from exc

    await session.refresh(company_currency)
    return company_currency


async def inactivate_company_currency(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    currency_id: UUID,
) -> CompanyARCurrency | None:
    company_currency = await get_company_currency(
        session=session,
        tenant=tenant,
        company_id=company_id,
        currency_id=currency_id,
    )
    if company_currency is None:
        return None

    if company_currency.status == CompanyARCurrencyStatus.INACTIVE:
        return company_currency

    company_currency.status = CompanyARCurrencyStatus.INACTIVE

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise CompanyARCurrencyStateConflictError(
            "Currency could not be inactivated due to a data conflict"
        ) from exc

    await session.refresh(company_currency)
    return company_currency
