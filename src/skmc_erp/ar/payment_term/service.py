from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.ar.payment_term.model import PaymentTerm, PaymentTermStatus, PaymentTermType
from skmc_erp.ar.payment_term.schema import PaymentTermCreate, PaymentTermUpdate
from skmc_erp.core.company.model import Company
from skmc_erp.core.tenant.model import Tenant


class PaymentTermInputError(Exception):
    pass


class PaymentTermStateConflictError(Exception):
    pass


async def create_payment_term(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    payment_term_data: PaymentTermCreate,
) -> PaymentTerm:
    company = await session.get(Company, company_id)
    if company is None or company.tenant_id != tenant.id:
        raise PaymentTermInputError("Company does not exist")

    payment_term = PaymentTerm(
        company_id=company.id,
        name=payment_term_data.name,
        code=payment_term_data.code,
        term_type=payment_term_data.term_type,
        credit_days=payment_term_data.credit_days,
        is_default=payment_term_data.is_default,
        status=PaymentTermStatus.ACTIVE,
    )
    session.add(payment_term)

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise PaymentTermStateConflictError(
            "Payment Term could not be created due to a data conflict, such as a duplicate code or active default"
        ) from exc

    await session.refresh(payment_term)
    return payment_term


async def get_payment_term(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    payment_term_id: UUID,
) -> PaymentTerm | None:
    stmt = (
        select(PaymentTerm)
        .join(Company, PaymentTerm.company_id == Company.id)
        .where(
            PaymentTerm.id == payment_term_id,
            PaymentTerm.company_id == company_id,
            Company.tenant_id == tenant.id,
        )
    )
    return await session.scalar(stmt)


async def list_payment_terms(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
) -> Sequence[PaymentTerm]:
    company = await session.get(Company, company_id)
    if company is None or company.tenant_id != tenant.id:
        return []

    stmt = (
        select(PaymentTerm)
        .where(PaymentTerm.company_id == company_id)
        .order_by(PaymentTerm.name)
    )
    result = await session.scalars(stmt)
    return result.all()


async def update_payment_term(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    payment_term_id: UUID,
    update_data: PaymentTermUpdate,
) -> PaymentTerm | None:
    payment_term = await get_payment_term(
        session=session,
        tenant=tenant,
        company_id=company_id,
        payment_term_id=payment_term_id,
    )
    if payment_term is None:
        return None

    if update_data.name is not None:
        payment_term.name = update_data.name

    if update_data.credit_days is not None:
        if payment_term.term_type == PaymentTermType.IMMEDIATE and update_data.credit_days != 0:
            raise PaymentTermInputError("credit_days must be 0 for IMMEDIATE term type")
        if payment_term.term_type == PaymentTermType.NET_DAYS and update_data.credit_days <= 0:
            raise PaymentTermInputError("credit_days must be > 0 for NET_DAYS term type")
        payment_term.credit_days = update_data.credit_days

    if update_data.is_default is not None:
        payment_term.is_default = update_data.is_default

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise PaymentTermStateConflictError(
            "Payment Term could not be updated due to a data conflict, such as a duplicate active default"
        ) from exc

    await session.refresh(payment_term)
    return payment_term


async def inactivate_payment_term(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    payment_term_id: UUID,
) -> PaymentTerm | None:
    payment_term = await get_payment_term(
        session=session,
        tenant=tenant,
        company_id=company_id,
        payment_term_id=payment_term_id,
    )
    if payment_term is None:
        return None

    if payment_term.status == PaymentTermStatus.INACTIVE:
        return payment_term

    payment_term.status = PaymentTermStatus.INACTIVE

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise PaymentTermStateConflictError(
            "Payment Term could not be inactivated due to a data conflict"
        ) from exc

    await session.refresh(payment_term)
    return payment_term
