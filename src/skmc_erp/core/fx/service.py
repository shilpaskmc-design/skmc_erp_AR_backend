from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.core.company.model import Company
from skmc_erp.core.currency.model import Currency
from skmc_erp.core.fx.model import ExchangeRate, ExchangeRateStatus
from skmc_erp.core.fx.schema import ExchangeRateCreate
from skmc_erp.core.tenant.model import Tenant


class ExchangeRateInputError(Exception):
    pass


class ExchangeRateStateConflictError(Exception):
    pass


async def _company(session: AsyncSession, tenant: Tenant, company_id: UUID) -> Company:
    company = await session.get(Company, company_id)
    if company is None or company.tenant_id != tenant.id:
        raise ExchangeRateInputError("Company does not exist")
    return company


async def create_exchange_rate(*, session: AsyncSession, tenant: Tenant, company_id: UUID, rate_data: ExchangeRateCreate) -> ExchangeRate:
    await _company(session, tenant, company_id)
    for code in (rate_data.from_currency_code, rate_data.to_currency_code):
        if await session.get(Currency, code) is None:
            raise ExchangeRateInputError(f"Currency {code} does not exist")
    rate = ExchangeRate(company_id=company_id, **rate_data.model_dump(), status=ExchangeRateStatus.ACTIVE)
    session.add(rate)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ExchangeRateStateConflictError("Exchange Rate conflicts with an existing active effective period") from exc
    await session.refresh(rate)
    return rate


async def list_exchange_rates(*, session: AsyncSession, tenant: Tenant, company_id: UUID) -> Sequence[ExchangeRate]:
    await _company(session, tenant, company_id)
    result = await session.scalars(select(ExchangeRate).where(ExchangeRate.company_id == company_id).order_by(ExchangeRate.effective_from, ExchangeRate.id))
    return result.all()


async def get_exchange_rate(*, session: AsyncSession, tenant: Tenant, company_id: UUID, rate_id: UUID) -> ExchangeRate | None:
    return await session.scalar(select(ExchangeRate).join(Company, ExchangeRate.company_id == Company.id).where(ExchangeRate.id == rate_id, ExchangeRate.company_id == company_id, Company.tenant_id == tenant.id))


async def inactivate_exchange_rate(*, session: AsyncSession, tenant: Tenant, company_id: UUID, rate_id: UUID) -> ExchangeRate | None:
    rate = await get_exchange_rate(session=session, tenant=tenant, company_id=company_id, rate_id=rate_id)
    if rate is None:
        return None
    rate.status = ExchangeRateStatus.INACTIVE
    await session.commit()
    await session.refresh(rate)
    return rate
