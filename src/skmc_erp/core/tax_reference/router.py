from typing import Annotated, Never
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.core.tax_reference.schema import CompanyHsnSacCodeCreate, CompanyHsnSacCodeResponse, CompanyHsnSacCodeUpdate, CompanyHsnSacTaxRateCreate, CompanyHsnSacTaxRateEnd, CompanyHsnSacTaxRateResponse
from skmc_erp.core.tax_reference.service import HsnSacInputError, HsnSacNotFoundError, HsnSacStateConflictError, create_hsn_sac_code, create_hsn_sac_tax_rate, end_hsn_sac_tax_rate, get_hsn_sac_code, inactivate_hsn_sac_code, inactivate_hsn_sac_tax_rate, list_hsn_sac_codes, list_hsn_sac_tax_rates, update_hsn_sac_code
from skmc_erp.core.tenant.dependencies import get_temporary_tenant_context
from skmc_erp.core.tenant.model import Tenant
from skmc_erp.database import get_db_session

router = APIRouter(prefix="/companies/{company_id}/hsn-sac-codes", tags=["company-hsn-sac-codes"])


def _raise(exc: Exception) -> Never:
    code = 404 if isinstance(exc, HsnSacNotFoundError) else 422 if isinstance(exc, HsnSacInputError) else 409
    raise HTTPException(status_code=code, detail=str(exc)) from exc


@router.post("", response_model=CompanyHsnSacCodeResponse, status_code=status.HTTP_201_CREATED)
async def create_code_endpoint(company_id: UUID, code_data: CompanyHsnSacCodeCreate, tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)], session: Annotated[AsyncSession, Depends(get_db_session)]) -> CompanyHsnSacCodeResponse:
    try:
        item = await create_hsn_sac_code(session=session, tenant=tenant, company_id=company_id, code_data=code_data)
    except (HsnSacNotFoundError, HsnSacInputError, HsnSacStateConflictError) as exc:
        _raise(exc)
    return CompanyHsnSacCodeResponse.model_validate(item)


@router.get("", response_model=list[CompanyHsnSacCodeResponse])
async def list_codes_endpoint(company_id: UUID, tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)], session: Annotated[AsyncSession, Depends(get_db_session)]) -> list[CompanyHsnSacCodeResponse]:
    try:
        items = await list_hsn_sac_codes(session=session, tenant=tenant, company_id=company_id)
    except HsnSacNotFoundError:
        return []
    return [CompanyHsnSacCodeResponse.model_validate(item) for item in items]


@router.get("/{code_id}", response_model=CompanyHsnSacCodeResponse)
async def get_code_endpoint(company_id: UUID, code_id: UUID, tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)], session: Annotated[AsyncSession, Depends(get_db_session)]) -> CompanyHsnSacCodeResponse:
    item = await get_hsn_sac_code(session=session, tenant=tenant, company_id=company_id, code_id=code_id)
    if item is None:
        raise HTTPException(status_code=404, detail="HSN/SAC Code not found")
    return CompanyHsnSacCodeResponse.model_validate(item)


@router.patch("/{code_id}", response_model=CompanyHsnSacCodeResponse)
async def update_code_endpoint(company_id: UUID, code_id: UUID, code_data: CompanyHsnSacCodeUpdate, tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)], session: Annotated[AsyncSession, Depends(get_db_session)]) -> CompanyHsnSacCodeResponse:
    try:
        item = await update_hsn_sac_code(session=session, tenant=tenant, company_id=company_id, code_id=code_id, code_data=code_data)
    except (HsnSacNotFoundError, HsnSacStateConflictError) as exc:
        _raise(exc)
    if item is None:
        raise HTTPException(status_code=404, detail="HSN/SAC Code not found")
    return CompanyHsnSacCodeResponse.model_validate(item)


@router.post("/{code_id}/inactivate", response_model=CompanyHsnSacCodeResponse)
async def inactivate_code_endpoint(company_id: UUID, code_id: UUID, tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)], session: Annotated[AsyncSession, Depends(get_db_session)]) -> CompanyHsnSacCodeResponse:
    try:
        item = await inactivate_hsn_sac_code(session=session, tenant=tenant, company_id=company_id, code_id=code_id)
    except (HsnSacNotFoundError, HsnSacStateConflictError) as exc:
        _raise(exc)
    if item is None:
        raise HTTPException(status_code=404, detail="HSN/SAC Code not found")
    return CompanyHsnSacCodeResponse.model_validate(item)


@router.post("/{code_id}/tax-rates", response_model=CompanyHsnSacTaxRateResponse, status_code=status.HTTP_201_CREATED)
async def create_mapping_endpoint(company_id: UUID, code_id: UUID, mapping_data: CompanyHsnSacTaxRateCreate, tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)], session: Annotated[AsyncSession, Depends(get_db_session)]) -> CompanyHsnSacTaxRateResponse:
    try:
        mapping = await create_hsn_sac_tax_rate(session=session, tenant=tenant, company_id=company_id, code_id=code_id, mapping_data=mapping_data)
    except (HsnSacNotFoundError, HsnSacInputError, HsnSacStateConflictError) as exc:
        _raise(exc)
    return CompanyHsnSacTaxRateResponse.model_validate(mapping)


@router.get("/{code_id}/tax-rates", response_model=list[CompanyHsnSacTaxRateResponse])
async def list_mappings_endpoint(company_id: UUID, code_id: UUID, tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)], session: Annotated[AsyncSession, Depends(get_db_session)]) -> list[CompanyHsnSacTaxRateResponse]:
    try:
        mappings = await list_hsn_sac_tax_rates(session=session, tenant=tenant, company_id=company_id, code_id=code_id)
    except HsnSacNotFoundError as exc:
        _raise(exc)
    return [CompanyHsnSacTaxRateResponse.model_validate(item) for item in mappings]


@router.post("/{code_id}/tax-rates/{mapping_id}/end", response_model=CompanyHsnSacTaxRateResponse)
async def end_mapping_endpoint(company_id: UUID, code_id: UUID, mapping_id: UUID, end_data: CompanyHsnSacTaxRateEnd, tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)], session: Annotated[AsyncSession, Depends(get_db_session)]) -> CompanyHsnSacTaxRateResponse:
    try:
        mapping = await end_hsn_sac_tax_rate(session=session, tenant=tenant, company_id=company_id, code_id=code_id, mapping_id=mapping_id, end_date=end_data.end_date)
    except (HsnSacInputError, HsnSacNotFoundError, HsnSacStateConflictError) as exc:
        _raise(exc)
    if mapping is None:
        raise HTTPException(status_code=404, detail="HSN/SAC Tax Rate not found")
    return CompanyHsnSacTaxRateResponse.model_validate(mapping)


@router.post("/{code_id}/tax-rates/{mapping_id}/inactivate", response_model=CompanyHsnSacTaxRateResponse)
async def inactivate_mapping_endpoint(company_id: UUID, code_id: UUID, mapping_id: UUID, tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)], session: Annotated[AsyncSession, Depends(get_db_session)]) -> CompanyHsnSacTaxRateResponse:
    try:
        mapping = await inactivate_hsn_sac_tax_rate(session=session, tenant=tenant, company_id=company_id, code_id=code_id, mapping_id=mapping_id)
    except (HsnSacNotFoundError, HsnSacStateConflictError) as exc:
        _raise(exc)
    if mapping is None:
        raise HTTPException(status_code=404, detail="HSN/SAC Tax Rate not found")
    return CompanyHsnSacTaxRateResponse.model_validate(mapping)
