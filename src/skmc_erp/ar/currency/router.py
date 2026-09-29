from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.ar.currency.schema import (
    CompanyARCurrencyCreate,
    CompanyARCurrencyResponse,
    CompanyARCurrencyUpdate,
)
from skmc_erp.ar.currency.service import (
    CompanyARCurrencyInputError,
    CompanyARCurrencyStateConflictError,
    enable_company_currency,
    get_company_currency,
    inactivate_company_currency,
    list_company_currencies,
    update_company_currency,
)
from skmc_erp.core.tenant.dependencies import get_temporary_tenant_context
from skmc_erp.core.tenant.model import Tenant
from skmc_erp.database import get_db_session

router = APIRouter(prefix="/companies/{company_id}/currencies", tags=["company_currencies"])


@router.post("", response_model=CompanyARCurrencyResponse, status_code=status.HTTP_201_CREATED)
async def enable_company_currency_endpoint(
    company_id: UUID,
    currency_data: CompanyARCurrencyCreate,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyARCurrencyResponse:
    try:
        company_currency = await enable_company_currency(
            session=session,
            tenant=tenant,
            company_id=company_id,
            currency_data=currency_data,
        )
    except CompanyARCurrencyInputError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except CompanyARCurrencyStateConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return CompanyARCurrencyResponse.model_validate(company_currency)


@router.get("", response_model=list[CompanyARCurrencyResponse])
async def list_company_currencies_endpoint(
    company_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[CompanyARCurrencyResponse]:
    company_currencies = await list_company_currencies(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    if not company_currencies:
        return []

    return [CompanyARCurrencyResponse.model_validate(cc) for cc in company_currencies]


@router.get("/{currency_id}", response_model=CompanyARCurrencyResponse)
async def get_company_currency_endpoint(
    company_id: UUID,
    currency_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyARCurrencyResponse:
    company_currency = await get_company_currency(
        session=session,
        tenant=tenant,
        company_id=company_id,
        currency_id=currency_id,
    )
    if company_currency is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Currency not found",
        )
    return CompanyARCurrencyResponse.model_validate(company_currency)


@router.patch("/{currency_id}", response_model=CompanyARCurrencyResponse)
async def update_company_currency_endpoint(
    company_id: UUID,
    currency_id: UUID,
    update_data: CompanyARCurrencyUpdate,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyARCurrencyResponse:
    try:
        company_currency = await update_company_currency(
            session=session,
            tenant=tenant,
            company_id=company_id,
            currency_id=currency_id,
            update_data=update_data,
        )
    except CompanyARCurrencyInputError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except CompanyARCurrencyStateConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    if company_currency is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Currency not found",
        )
    return CompanyARCurrencyResponse.model_validate(company_currency)


@router.post("/{currency_id}/inactivate", response_model=CompanyARCurrencyResponse)
async def inactivate_company_currency_endpoint(
    company_id: UUID,
    currency_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyARCurrencyResponse:
    try:
        company_currency = await inactivate_company_currency(
            session=session,
            tenant=tenant,
            company_id=company_id,
            currency_id=currency_id,
        )
    except CompanyARCurrencyStateConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    if company_currency is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Currency not found",
        )
    return CompanyARCurrencyResponse.model_validate(company_currency)
