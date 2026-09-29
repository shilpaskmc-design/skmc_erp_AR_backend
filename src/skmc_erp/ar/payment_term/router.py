from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.ar.payment_term.schema import (
    PaymentTermCreate,
    PaymentTermResponse,
    PaymentTermUpdate,
)
from skmc_erp.ar.payment_term.service import (
    PaymentTermInputError,
    PaymentTermStateConflictError,
    create_payment_term,
    get_payment_term,
    inactivate_payment_term,
    list_payment_terms,
    update_payment_term,
)
from skmc_erp.core.tenant.dependencies import get_temporary_tenant_context
from skmc_erp.core.tenant.model import Tenant
from skmc_erp.database import get_db_session

router = APIRouter(prefix="/companies/{company_id}/payment-terms", tags=["payment_terms"])


@router.post("", response_model=PaymentTermResponse, status_code=status.HTTP_201_CREATED)
async def create_payment_term_endpoint(
    company_id: UUID,
    payment_term_data: PaymentTermCreate,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PaymentTermResponse:
    try:
        payment_term = await create_payment_term(
            session=session,
            tenant=tenant,
            company_id=company_id,
            payment_term_data=payment_term_data,
        )
    except PaymentTermInputError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except PaymentTermStateConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return PaymentTermResponse.model_validate(payment_term)


@router.get("", response_model=list[PaymentTermResponse])
async def list_payment_terms_endpoint(
    company_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[PaymentTermResponse]:
    payment_terms = await list_payment_terms(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    if not payment_terms:
        return []

    return [PaymentTermResponse.model_validate(pt) for pt in payment_terms]


@router.get("/{payment_term_id}", response_model=PaymentTermResponse)
async def get_payment_term_endpoint(
    company_id: UUID,
    payment_term_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PaymentTermResponse:
    payment_term = await get_payment_term(
        session=session,
        tenant=tenant,
        company_id=company_id,
        payment_term_id=payment_term_id,
    )
    if payment_term is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment Term not found",
        )
    return PaymentTermResponse.model_validate(payment_term)


@router.patch("/{payment_term_id}", response_model=PaymentTermResponse)
async def update_payment_term_endpoint(
    company_id: UUID,
    payment_term_id: UUID,
    update_data: PaymentTermUpdate,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PaymentTermResponse:
    try:
        payment_term = await update_payment_term(
            session=session,
            tenant=tenant,
            company_id=company_id,
            payment_term_id=payment_term_id,
            update_data=update_data,
        )
    except PaymentTermInputError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except PaymentTermStateConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    if payment_term is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment Term not found",
        )
    return PaymentTermResponse.model_validate(payment_term)


@router.post("/{payment_term_id}/inactivate", response_model=PaymentTermResponse)
async def inactivate_payment_term_endpoint(
    company_id: UUID,
    payment_term_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PaymentTermResponse:
    try:
        payment_term = await inactivate_payment_term(
            session=session,
            tenant=tenant,
            company_id=company_id,
            payment_term_id=payment_term_id,
        )
    except PaymentTermStateConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    if payment_term is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment Term not found",
        )
    return PaymentTermResponse.model_validate(payment_term)
