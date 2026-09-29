from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.core.fx.schema import ExchangeRateCreate, ExchangeRateResponse
from skmc_erp.core.fx.service import ExchangeRateInputError, ExchangeRateStateConflictError, create_exchange_rate, get_exchange_rate, inactivate_exchange_rate, list_exchange_rates
from skmc_erp.core.tenant.dependencies import get_temporary_tenant_context
from skmc_erp.core.tenant.model import Tenant
from skmc_erp.database import get_db_session

router = APIRouter(prefix="/companies/{company_id}/exchange-rates", tags=["exchange_rates"])


@router.post("", response_model=ExchangeRateResponse, status_code=status.HTTP_201_CREATED)
async def create_exchange_rate_endpoint(company_id: UUID, rate_data: ExchangeRateCreate, tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)], session: Annotated[AsyncSession, Depends(get_db_session)]) -> ExchangeRateResponse:
    try:
        rate = await create_exchange_rate(session=session, tenant=tenant, company_id=company_id, rate_data=rate_data)
    except ExchangeRateInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ExchangeRateStateConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ExchangeRateResponse.model_validate(rate)


@router.get("", response_model=list[ExchangeRateResponse])
async def list_exchange_rates_endpoint(company_id: UUID, tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)], session: Annotated[AsyncSession, Depends(get_db_session)]) -> list[ExchangeRateResponse]:
    try:
        rates = await list_exchange_rates(session=session, tenant=tenant, company_id=company_id)
    except ExchangeRateInputError:
        return []
    return [ExchangeRateResponse.model_validate(item) for item in rates]


@router.get("/{rate_id}", response_model=ExchangeRateResponse)
async def get_exchange_rate_endpoint(company_id: UUID, rate_id: UUID, tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)], session: Annotated[AsyncSession, Depends(get_db_session)]) -> ExchangeRateResponse:
    rate = await get_exchange_rate(session=session, tenant=tenant, company_id=company_id, rate_id=rate_id)
    if rate is None:
        raise HTTPException(status_code=404, detail="Exchange Rate not found")
    return ExchangeRateResponse.model_validate(rate)


@router.post("/{rate_id}/inactivate", response_model=ExchangeRateResponse)
async def inactivate_exchange_rate_endpoint(company_id: UUID, rate_id: UUID, tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)], session: Annotated[AsyncSession, Depends(get_db_session)]) -> ExchangeRateResponse:
    rate = await inactivate_exchange_rate(session=session, tenant=tenant, company_id=company_id, rate_id=rate_id)
    if rate is None:
        raise HTTPException(status_code=404, detail="Exchange Rate not found")
    return ExchangeRateResponse.model_validate(rate)
