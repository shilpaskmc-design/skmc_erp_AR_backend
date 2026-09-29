from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.core.bank_account.schema import (
    CompanyBankAccountCreate,
    CompanyBankAccountResponse,
    CompanyBankAccountUpdate,
)
from skmc_erp.core.bank_account.service import (
    BankAccountInputError,
    BankAccountStateConflictError,
    create_bank_account,
    get_bank_account,
    inactivate_bank_account,
    list_bank_accounts,
    update_bank_account,
)
from skmc_erp.core.tenant.dependencies import get_temporary_tenant_context
from skmc_erp.core.tenant.model import Tenant
from skmc_erp.database import get_db_session

router = APIRouter(prefix="/companies/{company_id}/bank-accounts", tags=["bank_accounts"])


@router.post("", response_model=CompanyBankAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_bank_account_endpoint(
    company_id: UUID,
    bank_account_data: CompanyBankAccountCreate,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyBankAccountResponse:
    try:
        bank_account = await create_bank_account(
            session=session,
            tenant=tenant,
            company_id=company_id,
            bank_account_data=bank_account_data,
        )
    except BankAccountInputError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except BankAccountStateConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return CompanyBankAccountResponse.model_validate(bank_account)


@router.get("", response_model=list[CompanyBankAccountResponse])
async def list_bank_accounts_endpoint(
    company_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[CompanyBankAccountResponse]:
    bank_accounts = await list_bank_accounts(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    if not bank_accounts:
        return []

    return [CompanyBankAccountResponse.model_validate(acc) for acc in bank_accounts]


@router.get("/{bank_account_id}", response_model=CompanyBankAccountResponse)
async def get_bank_account_endpoint(
    company_id: UUID,
    bank_account_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyBankAccountResponse:
    bank_account = await get_bank_account(
        session=session,
        tenant=tenant,
        company_id=company_id,
        bank_account_id=bank_account_id,
    )
    if bank_account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bank Account not found",
        )
    return CompanyBankAccountResponse.model_validate(bank_account)


@router.patch("/{bank_account_id}", response_model=CompanyBankAccountResponse)
async def update_bank_account_endpoint(
    company_id: UUID,
    bank_account_id: UUID,
    update_data: CompanyBankAccountUpdate,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyBankAccountResponse:
    try:
        bank_account = await update_bank_account(
            session=session,
            tenant=tenant,
            company_id=company_id,
            bank_account_id=bank_account_id,
            update_data=update_data,
        )
    except BankAccountInputError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except BankAccountStateConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    if bank_account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bank Account not found",
        )
    return CompanyBankAccountResponse.model_validate(bank_account)


@router.post("/{bank_account_id}/inactivate", response_model=CompanyBankAccountResponse)
async def inactivate_bank_account_endpoint(
    company_id: UUID,
    bank_account_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyBankAccountResponse:
    try:
        bank_account = await inactivate_bank_account(
            session=session,
            tenant=tenant,
            company_id=company_id,
            bank_account_id=bank_account_id,
        )
    except BankAccountStateConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    if bank_account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bank Account not found",
        )
    return CompanyBankAccountResponse.model_validate(bank_account)
