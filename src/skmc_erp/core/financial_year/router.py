from datetime import date
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
    get_company_fiscal_settings,
    get_financial_year,
    get_open_financial_year_for_date,
    list_financial_years,
    transition_financial_year,
)
from skmc_erp.core.financial_year.model import FinancialYearStatus
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


@router.get(
    "/financial-year-settings",
    response_model=CompanyFiscalSettingsResponse,
)
async def get_company_fiscal_settings_endpoint(
    company_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyFiscalSettingsResponse:
    try:
        settings = await get_company_fiscal_settings(
            session=session, tenant=tenant, company_id=company_id
        )
    except (FinancialYearNotFoundError, FinancialYearStateConflictError) as exc:
        _raise_http_error(exc)
    if settings is None:
        raise HTTPException(status_code=404, detail="Fiscal Settings not found")
    return CompanyFiscalSettingsResponse.model_validate(settings)


@router.get("/financial-years", response_model=list[FinancialYearResponse])
async def list_financial_years_endpoint(
    company_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[FinancialYearResponse]:
    try:
        years = await list_financial_years(
            session=session, tenant=tenant, company_id=company_id
        )
    except FinancialYearNotFoundError:
        return []
    return [FinancialYearResponse.model_validate(item) for item in years]


@router.get(
    "/financial-years/open",
    response_model=FinancialYearResponse,
)
async def get_open_financial_year_endpoint(
    company_id: UUID,
    as_of_date: date,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> FinancialYearResponse:
    try:
        financial_year = await get_open_financial_year_for_date(
            session=session,
            tenant=tenant,
            company_id=company_id,
            as_of_date=as_of_date,
        )
    except FinancialYearNotFoundError as exc:
        _raise_http_error(exc)
    if financial_year is None:
        raise HTTPException(status_code=404, detail="Open Financial Year not found")
    return FinancialYearResponse.model_validate(financial_year)


@router.get(
    "/financial-years/{financial_year_id}",
    response_model=FinancialYearResponse,
)
async def get_financial_year_endpoint(
    company_id: UUID,
    financial_year_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> FinancialYearResponse:
    financial_year = await get_financial_year(
        session=session,
        tenant=tenant,
        company_id=company_id,
        financial_year_id=financial_year_id,
    )
    if financial_year is None:
        raise HTTPException(status_code=404, detail="Financial Year not found")
    return FinancialYearResponse.model_validate(financial_year)


async def _transition_endpoint(
    company_id: UUID,
    financial_year_id: UUID,
    target_status: FinancialYearStatus,
    tenant: Tenant,
    session: AsyncSession,
) -> FinancialYearResponse:
    try:
        financial_year = await transition_financial_year(
            session=session,
            tenant=tenant,
            company_id=company_id,
            financial_year_id=financial_year_id,
            target_status=target_status,
        )
    except FinancialYearStateConflictError as exc:
        _raise_http_error(exc)
    if financial_year is None:
        raise HTTPException(status_code=404, detail="Financial Year not found")
    return FinancialYearResponse.model_validate(financial_year)


@router.post("/financial-years/{financial_year_id}/open", response_model=FinancialYearResponse)
async def open_financial_year_endpoint(
    company_id: UUID,
    financial_year_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> FinancialYearResponse:
    return await _transition_endpoint(
        company_id, financial_year_id, FinancialYearStatus.OPEN, tenant, session
    )


@router.post("/financial-years/{financial_year_id}/close", response_model=FinancialYearResponse)
async def close_financial_year_endpoint(
    company_id: UUID,
    financial_year_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> FinancialYearResponse:
    return await _transition_endpoint(
        company_id, financial_year_id, FinancialYearStatus.CLOSED, tenant, session
    )
