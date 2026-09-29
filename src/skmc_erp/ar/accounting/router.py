from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.ar.accounting import service
from skmc_erp.ar.accounting.schema import (
    RevenueGlMappingCreate,
    RevenueGlMappingEnd,
    RevenueGlMappingResponse,
    TaxGlAccountMappingCreate,
    TaxGlAccountMappingEnd,
    TaxGlAccountMappingRemap,
    TaxGlAccountMappingResponse,
)
from skmc_erp.ar.accounting.service import (
    AccountingMappingInputError,
    AccountingMappingNotFoundError,
    AccountingMappingStateConflictError,
)
from skmc_erp.core.tenant.dependencies import get_temporary_tenant_context
from skmc_erp.core.tenant.model import Tenant
from skmc_erp.database import get_db_session

router = APIRouter(prefix="/companies/{company_id}", tags=["ar_accounting"])


@router.get(
    "/tax-gl-mappings",
    response_model=list[TaxGlAccountMappingResponse],
    summary="List Tax GL Account Mappings",
)
async def list_tax_gl_account_mappings_endpoint(
    company_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[TaxGlAccountMappingResponse]:
    try:
        mappings = await service.list_tax_gl_account_mappings(session, tenant, company_id)
        return [TaxGlAccountMappingResponse.model_validate(m) for m in mappings]
    except AccountingMappingNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/tax-gl-mappings",
    response_model=TaxGlAccountMappingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign Tax GL Account Mapping",
)
async def assign_tax_gl_account_mapping_endpoint(
    company_id: UUID,
    payload: TaxGlAccountMappingCreate,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TaxGlAccountMappingResponse:
    try:
        mapping = await service.assign_tax_gl_account_mapping(session, tenant, company_id, payload)
        return TaxGlAccountMappingResponse.model_validate(mapping)
    except AccountingMappingInputError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except AccountingMappingStateConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except AccountingMappingNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/tax-gl-mappings/{mapping_id}/remap",
    response_model=TaxGlAccountMappingResponse,
    summary="Remap Tax GL Account Mapping",
)
async def remap_tax_gl_account_mapping_endpoint(
    company_id: UUID,
    mapping_id: UUID,
    payload: TaxGlAccountMappingRemap,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TaxGlAccountMappingResponse:
    try:
        mapping = await service.remap_tax_gl_account_mapping(
            session, tenant, company_id, mapping_id, payload
        )
        return TaxGlAccountMappingResponse.model_validate(mapping)
    except AccountingMappingInputError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except AccountingMappingStateConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except AccountingMappingNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/tax-gl-mappings/{mapping_id}/end",
    response_model=TaxGlAccountMappingResponse,
    summary="End Tax GL Account Mapping",
)
async def end_tax_gl_account_mapping_endpoint(
    company_id: UUID,
    mapping_id: UUID,
    payload: TaxGlAccountMappingEnd,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TaxGlAccountMappingResponse:
    try:
        mapping = await service.end_tax_gl_account_mapping(
            session, tenant, company_id, mapping_id, payload
        )
        return TaxGlAccountMappingResponse.model_validate(mapping)
    except AccountingMappingInputError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except AccountingMappingStateConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except AccountingMappingNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# --- Revenue GL Mappings ---

@router.get(
    "/revenue-gl-mappings",
    response_model=list[RevenueGlMappingResponse],
    summary="List Revenue GL Mappings",
)
async def list_revenue_gl_mappings_endpoint(
    company_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    service_type_id: Annotated[UUID | None, Query()] = None,
    sku_id: Annotated[UUID | None, Query()] = None,
    supply_type_code: Annotated[str | None, Query()] = None,
    company_location_id: Annotated[UUID | None, Query()] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> list[RevenueGlMappingResponse]:
    try:
        mappings = await service.list_revenue_gl_mappings(
            session,
            tenant,
            company_id,
            service_type_id=service_type_id,
            sku_id=sku_id,
            supply_type_code=supply_type_code,
            company_location_id=company_location_id,
            status_filter=status_filter,
        )
        return [RevenueGlMappingResponse.model_validate(m) for m in mappings]
    except AccountingMappingNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/revenue-gl-mappings",
    response_model=RevenueGlMappingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign Revenue GL Mapping",
)
async def assign_revenue_gl_mapping_endpoint(
    company_id: UUID,
    payload: RevenueGlMappingCreate,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RevenueGlMappingResponse:
    try:
        mapping = await service.assign_revenue_gl_mapping(
            session, tenant, company_id, payload
        )
        return RevenueGlMappingResponse.model_validate(mapping)
    except AccountingMappingInputError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    except AccountingMappingStateConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(e)
        )
    except AccountingMappingNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/revenue-gl-mappings/{mapping_id}",
    response_model=RevenueGlMappingResponse,
    summary="Get Revenue GL Mapping by ID",
)
async def get_revenue_gl_mapping_endpoint(
    company_id: UUID,
    mapping_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RevenueGlMappingResponse:
    try:
        mapping = await service.get_revenue_gl_mapping(
            session, tenant, company_id, mapping_id
        )
        return RevenueGlMappingResponse.model_validate(mapping)
    except AccountingMappingNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/revenue-gl-mappings/{mapping_id}/end",
    response_model=RevenueGlMappingResponse,
    summary="End Revenue GL Mapping",
)
async def end_revenue_gl_mapping_endpoint(
    company_id: UUID,
    mapping_id: UUID,
    payload: RevenueGlMappingEnd,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RevenueGlMappingResponse:
    try:
        mapping = await service.end_revenue_gl_mapping(
            session, tenant, company_id, mapping_id, payload
        )
        return RevenueGlMappingResponse.model_validate(mapping)
    except AccountingMappingInputError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    except AccountingMappingStateConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(e)
        )
    except AccountingMappingNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/revenue-gl-mappings/{mapping_id}/inactivate",
    response_model=RevenueGlMappingResponse,
    summary="Inactivate Revenue GL Mapping",
)
async def inactivate_revenue_gl_mapping_endpoint(
    company_id: UUID,
    mapping_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RevenueGlMappingResponse:
    try:
        mapping = await service.inactivate_revenue_gl_mapping(
            session, tenant, company_id, mapping_id
        )
        return RevenueGlMappingResponse.model_validate(mapping)
    except AccountingMappingStateConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(e)
        )
    except AccountingMappingNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
