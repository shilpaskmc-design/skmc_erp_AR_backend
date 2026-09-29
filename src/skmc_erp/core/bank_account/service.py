from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.core.accounting.model import GlAccount
from skmc_erp.core.bank_account.model import CompanyBankAccount, CompanyBankAccountStatus
from skmc_erp.core.bank_account.schema import (
    IFSC_PATTERN,
    CompanyBankAccountCreate,
    CompanyBankAccountUpdate,
)
from skmc_erp.core.company.model import Company
from skmc_erp.core.currency.model import Currency
from skmc_erp.core.geography.model import Country
from skmc_erp.core.tenant.model import Tenant


class BankAccountInputError(Exception):
    pass


class BankAccountStateConflictError(Exception):
    pass


async def create_bank_account(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    bank_account_data: CompanyBankAccountCreate,
) -> CompanyBankAccount:
    company = await session.get(Company, company_id)
    if company is None or company.tenant_id != tenant.id:
        raise BankAccountInputError("Company does not exist")

    bank_country = await session.get(Country, bank_account_data.bank_country_code)
    if bank_country is None:
        raise BankAccountInputError("Bank country does not exist")

    currency = await session.get(Currency, bank_account_data.currency_code)
    if currency is None:
        raise BankAccountInputError("Currency does not exist")

    if bank_account_data.bank_country_code == "IN" and bank_account_data.ifsc:
        if not IFSC_PATTERN.match(bank_account_data.ifsc):
            raise BankAccountInputError("Invalid IFSC format for Indian bank account")

    if bank_account_data.gl_account_id is not None:
        gl_account = await session.get(GlAccount, bank_account_data.gl_account_id)
        if gl_account is None:
            raise BankAccountInputError("GL Account does not exist")
        if gl_account.company_id != company.id:
            raise BankAccountInputError("GL Account does not belong to the same Company")

    bank_account = CompanyBankAccount(
        company_id=company.id,
        bank_country_code=bank_account_data.bank_country_code,
        account_holder_name=bank_account_data.account_holder_name,
        bank_name=bank_account_data.bank_name,
        account_number=bank_account_data.account_number,
        branch_name=bank_account_data.branch_name,
        ifsc=bank_account_data.ifsc,
        swift=bank_account_data.swift,
        iban=bank_account_data.iban,
        currency_code=bank_account_data.currency_code,
        account_type=bank_account_data.account_type,
        gl_account_id=bank_account_data.gl_account_id,
        is_default_for_billing=bank_account_data.is_default_for_billing,
        status=CompanyBankAccountStatus.ACTIVE,
    )
    session.add(bank_account)

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise BankAccountStateConflictError(
            "Bank Account could not be created due to a data conflict, such as a duplicate active billing default"
        ) from exc

    await session.refresh(bank_account)
    return bank_account


async def get_bank_account(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    bank_account_id: UUID,
) -> CompanyBankAccount | None:
    stmt = (
        select(CompanyBankAccount)
        .join(Company, CompanyBankAccount.company_id == Company.id)
        .where(
            CompanyBankAccount.id == bank_account_id,
            CompanyBankAccount.company_id == company_id,
            Company.tenant_id == tenant.id,
        )
    )
    return await session.scalar(stmt)


async def list_bank_accounts(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
) -> Sequence[CompanyBankAccount]:
    company = await session.get(Company, company_id)
    if company is None or company.tenant_id != tenant.id:
        return []

    stmt = (
        select(CompanyBankAccount)
        .where(CompanyBankAccount.company_id == company_id)
        .order_by(CompanyBankAccount.bank_name, CompanyBankAccount.account_number)
    )
    result = await session.scalars(stmt)
    return result.all()


async def update_bank_account(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    bank_account_id: UUID,
    update_data: CompanyBankAccountUpdate,
) -> CompanyBankAccount | None:
    bank_account = await get_bank_account(
        session=session,
        tenant=tenant,
        company_id=company_id,
        bank_account_id=bank_account_id,
    )
    if bank_account is None:
        return None

    target_country_code = (
        update_data.bank_country_code
        if update_data.bank_country_code is not None
        else bank_account.bank_country_code
    )
    if update_data.bank_country_code is not None:
        bank_country = await session.get(Country, update_data.bank_country_code)
        if bank_country is None:
            raise BankAccountInputError("Bank country does not exist")
        bank_account.bank_country_code = update_data.bank_country_code

    target_ifsc = (
        update_data.ifsc if update_data.ifsc is not None else bank_account.ifsc
    )
    if target_country_code == "IN" and target_ifsc:
        if not IFSC_PATTERN.match(target_ifsc):
            raise BankAccountInputError("Invalid IFSC format for Indian bank account")

    if update_data.account_holder_name is not None:
        bank_account.account_holder_name = update_data.account_holder_name
    if update_data.bank_name is not None:
        bank_account.bank_name = update_data.bank_name
    if update_data.branch_name is not None:
        bank_account.branch_name = update_data.branch_name
    if update_data.ifsc is not None:
        bank_account.ifsc = update_data.ifsc
    if update_data.swift is not None:
        bank_account.swift = update_data.swift
    if update_data.iban is not None:
        bank_account.iban = update_data.iban
    if update_data.account_type is not None:
        bank_account.account_type = update_data.account_type

    if update_data.gl_account_id is not None:
        gl_account = await session.get(GlAccount, update_data.gl_account_id)
        if gl_account is None:
            raise BankAccountInputError("GL Account does not exist")
        if gl_account.company_id != company_id:
            raise BankAccountInputError("GL Account does not belong to the same Company")
        bank_account.gl_account_id = update_data.gl_account_id

    if update_data.is_default_for_billing is not None:
        bank_account.is_default_for_billing = update_data.is_default_for_billing

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise BankAccountStateConflictError(
            "Bank Account could not be updated due to a data conflict, such as a duplicate active billing default"
        ) from exc

    await session.refresh(bank_account)
    return bank_account


async def inactivate_bank_account(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    bank_account_id: UUID,
) -> CompanyBankAccount | None:
    bank_account = await get_bank_account(
        session=session,
        tenant=tenant,
        company_id=company_id,
        bank_account_id=bank_account_id,
    )
    if bank_account is None:
        return None

    if bank_account.status == CompanyBankAccountStatus.INACTIVE:
        return bank_account

    bank_account.status = CompanyBankAccountStatus.INACTIVE

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise BankAccountStateConflictError(
            "Bank Account could not be inactivated due to a data conflict"
        ) from exc

    await session.refresh(bank_account)
    return bank_account
