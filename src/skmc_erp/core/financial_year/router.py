from typing import Annotated, Never
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.core.financial_year.schema import (
    CompanyFiscalSettingsResponse,
    CompanyFiscalSettingsUpdate,
    FinancialYearCreate,
    FinancialYearResponse,
)
from skmc_erp.core.financial_year.service import (
    FinancialYearInputError,
    FinancialYearNotFoundError,
    FinancialYearStateConflictError,
    configure_company_fiscal_settings,
    create_financial_year,
)
from skmc_erp.core.tenant.dependencies import get_temporary_tenant_context
from skmc_erp.core.tenant.model import Tenant
from skmc_erp.database import get_db_session

router = APIRouter(prefix="/companies/{company_id}", tags=["financial-years"])


def _raise_http_error(exc: Exception) -> Never:
    if isinstance(exc, FinancialYearNotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, FinancialYearInputError):
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    else:
        status_code = status.HTTP_409_CONFLICT
    raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.put(
    "/financial-year-settings",
    response_model=CompanyFiscalSettingsResponse,
)
async def configure_company_fiscal_settings_endpoint(
    company_id: UUID,
    settings_data: CompanyFiscalSettingsUpdate,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyFiscalSettingsResponse:
    try:
        settings = await configure_company_fiscal_settings(
            session=session,
            tenant=tenant,
            company_id=company_id,
            settings_data=settings_data,
        )
    except (
        FinancialYearNotFoundError,
        FinancialYearInputError,
        FinancialYearStateConflictError,
    ) as exc:
        _raise_http_error(exc)

    return CompanyFiscalSettingsResponse.model_validate(settings)


@router.post(
    "/financial-years",
    response_model=FinancialYearResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_financial_year_endpoint(
    company_id: UUID,
    financial_year_data: FinancialYearCreate,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> FinancialYearResponse:
    try:
        financial_year = await create_financial_year(
            session=session,
            tenant=tenant,
            company_id=company_id,
            financial_year_data=financial_year_data,
        )
    except (
        FinancialYearNotFoundError,
        FinancialYearInputError,
        FinancialYearStateConflictError,
    ) as exc:
        _raise_http_error(exc)

    return FinancialYearResponse.model_validate(financial_year)
