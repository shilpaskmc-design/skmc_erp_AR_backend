from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.core.company_gst_registration.schema import (
    CompanyGSTRegistrationCreate,
    CompanyGSTRegistrationResponse,
    CompanyGSTRegistrationUpdate,
)
from skmc_erp.core.company_gst_registration.service import (
    CompanyGSTRegistrationInputError,
    CompanyGSTRegistrationNotFoundError,
    CompanyGSTRegistrationStateConflictError,
    create_company_gst_registration,
    get_company_gst_registration,
    list_company_gst_registrations,
    transition_company_gst_registration,
    update_company_gst_registration,
)
from skmc_erp.core.company_gst_registration.model import CompanyGSTRegistrationStatus
from skmc_erp.core.tenant.dependencies import get_temporary_tenant_context
from skmc_erp.core.tenant.model import Tenant
from skmc_erp.database import get_db_session


router = APIRouter(
    prefix="/companies/{company_id}/gst-registrations",
    tags=["company-gst-registrations"],
)


@router.post(
    "",
    response_model=CompanyGSTRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_company_gst_registration_endpoint(
    company_id: UUID,
    registration_data: CompanyGSTRegistrationCreate,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyGSTRegistrationResponse:
    try:
        registration = await create_company_gst_registration(
            session=session,
            tenant=tenant,
            company_id=company_id,
            registration_data=registration_data,
        )
    except CompanyGSTRegistrationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except CompanyGSTRegistrationInputError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except CompanyGSTRegistrationStateConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return CompanyGSTRegistrationResponse.model_validate(registration)


@router.get("", response_model=list[CompanyGSTRegistrationResponse])
async def list_company_gst_registrations_endpoint(
    company_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[CompanyGSTRegistrationResponse]:
    registrations = await list_company_gst_registrations(
        session=session, tenant=tenant, company_id=company_id
    )
    return [
        CompanyGSTRegistrationResponse.model_validate(item)
        for item in registrations
    ]


@router.get("/{registration_id}", response_model=CompanyGSTRegistrationResponse)
async def get_company_gst_registration_endpoint(
    company_id: UUID,
    registration_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyGSTRegistrationResponse:
    registration = await get_company_gst_registration(
        session=session,
        tenant=tenant,
        company_id=company_id,
        registration_id=registration_id,
    )
    if registration is None:
        raise HTTPException(status_code=404, detail="GST Registration not found")
    return CompanyGSTRegistrationResponse.model_validate(registration)


@router.patch("/{registration_id}", response_model=CompanyGSTRegistrationResponse)
async def update_company_gst_registration_endpoint(
    company_id: UUID,
    registration_id: UUID,
    registration_data: CompanyGSTRegistrationUpdate,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyGSTRegistrationResponse:
    try:
        registration = await update_company_gst_registration(
            session=session,
            tenant=tenant,
            company_id=company_id,
            registration_id=registration_id,
            registration_data=registration_data,
        )
    except CompanyGSTRegistrationInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except CompanyGSTRegistrationStateConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if registration is None:
        raise HTTPException(status_code=404, detail="GST Registration not found")
    return CompanyGSTRegistrationResponse.model_validate(registration)


async def _transition_endpoint(
    company_id: UUID,
    registration_id: UUID,
    target_status: CompanyGSTRegistrationStatus,
    tenant: Tenant,
    session: AsyncSession,
) -> CompanyGSTRegistrationResponse:
    try:
        registration = await transition_company_gst_registration(
            session=session,
            tenant=tenant,
            company_id=company_id,
            registration_id=registration_id,
            target_status=target_status,
        )
    except CompanyGSTRegistrationStateConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if registration is None:
        raise HTTPException(status_code=404, detail="GST Registration not found")
    return CompanyGSTRegistrationResponse.model_validate(registration)


@router.post("/{registration_id}/activate", response_model=CompanyGSTRegistrationResponse)
async def activate_company_gst_registration_endpoint(
    company_id: UUID,
    registration_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyGSTRegistrationResponse:
    return await _transition_endpoint(
        company_id,
        registration_id,
        CompanyGSTRegistrationStatus.ACTIVE,
        tenant,
        session,
    )


@router.post("/{registration_id}/inactivate", response_model=CompanyGSTRegistrationResponse)
async def inactivate_company_gst_registration_endpoint(
    company_id: UUID,
    registration_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyGSTRegistrationResponse:
    return await _transition_endpoint(
        company_id,
        registration_id,
        CompanyGSTRegistrationStatus.INACTIVE,
        tenant,
        session,
    )
