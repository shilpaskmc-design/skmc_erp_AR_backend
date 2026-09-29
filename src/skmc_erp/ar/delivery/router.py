from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.ar.delivery.schema import CompanyInvoiceDeliverySettingsPut, CompanyInvoiceDeliverySettingsResponse
from skmc_erp.ar.delivery.service import DeliverySettingsInputError, get_delivery_settings, put_delivery_settings
from skmc_erp.core.tenant.dependencies import get_temporary_tenant_context
from skmc_erp.core.tenant.model import Tenant
from skmc_erp.database import get_db_session

router = APIRouter(prefix="/companies/{company_id}/invoice-delivery-settings", tags=["invoice_delivery_settings"])


@router.get("", response_model=CompanyInvoiceDeliverySettingsResponse)
async def get_delivery_settings_endpoint(company_id: UUID, tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)], session: Annotated[AsyncSession, Depends(get_db_session)]) -> CompanyInvoiceDeliverySettingsResponse:
    try:
        settings = await get_delivery_settings(session=session, tenant=tenant, company_id=company_id)
    except DeliverySettingsInputError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if settings is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice Delivery Settings not found")
    return CompanyInvoiceDeliverySettingsResponse.model_validate(settings)


@router.put("", response_model=CompanyInvoiceDeliverySettingsResponse)
async def put_delivery_settings_endpoint(company_id: UUID, settings_data: CompanyInvoiceDeliverySettingsPut, tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)], session: Annotated[AsyncSession, Depends(get_db_session)]) -> CompanyInvoiceDeliverySettingsResponse:
    try:
        settings = await put_delivery_settings(session=session, tenant=tenant, company_id=company_id, settings_data=settings_data)
    except DeliverySettingsInputError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return CompanyInvoiceDeliverySettingsResponse.model_validate(settings)
