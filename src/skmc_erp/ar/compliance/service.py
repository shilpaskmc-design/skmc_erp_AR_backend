from typing import Sequence
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.ar.compliance.model import CompanyLut, CompanyLutStatus
from skmc_erp.ar.compliance.schema import CompanyLutCreate
from skmc_erp.core.company.model import Company
from skmc_erp.core.company_gst_registration.model import CompanyGSTRegistration
from skmc_erp.core.financial_year.model import FinancialYear
from skmc_erp.core.tenant.model import Tenant


class CompanyLutInputError(Exception):
    pass


class CompanyLutStateConflictError(Exception):
    pass


class CompanyLutNotFoundError(Exception):
    pass


async def _verify_company_tenant_access(session: AsyncSession, tenant: Tenant, company_id: UUID) -> None:
    stmt = select(Company.id).where(
        and_(Company.id == company_id, Company.tenant_id == tenant.id)
    )
    result = await session.execute(stmt)
    if result.scalar_one_or_none() is None:
        raise CompanyLutNotFoundError("Company not found or access denied")


async def _verify_gst_registration_company(
    session: AsyncSession, company_id: UUID, gst_registration_id: UUID
) -> None:
    stmt = select(CompanyGSTRegistration.id).where(
        and_(
            CompanyGSTRegistration.id == gst_registration_id,
            CompanyGSTRegistration.company_id == company_id,
        )
    )
    result = await session.execute(stmt)
    if result.scalar_one_or_none() is None:
        raise CompanyLutStateConflictError("GST Registration must belong to the same Company")


async def _verify_financial_year_company(
    session: AsyncSession, company_id: UUID, financial_year_id: UUID
) -> None:
    stmt = select(FinancialYear.id).where(
        and_(
            FinancialYear.id == financial_year_id,
            FinancialYear.company_id == company_id,
        )
    )
    result = await session.execute(stmt)
    if result.scalar_one_or_none() is None:
        raise CompanyLutStateConflictError("Financial Year must belong to the same Company")


async def _check_active_lut_uniqueness(
    session: AsyncSession, company_id: UUID, gst_registration_id: UUID, financial_year_id: UUID
) -> None:
    stmt = select(CompanyLut.id).where(
        and_(
            CompanyLut.company_id == company_id,
            CompanyLut.gst_registration_id == gst_registration_id,
            CompanyLut.financial_year_id == financial_year_id,
            CompanyLut.status == CompanyLutStatus.ACTIVE,
        )
    )
    result = await session.execute(stmt)
    if result.scalar_one_or_none() is not None:
        raise CompanyLutStateConflictError(
            "An ACTIVE LUT already exists for this GST Registration and Financial Year"
        )


async def list_company_luts(
    session: AsyncSession, tenant: Tenant, company_id: UUID
) -> Sequence[CompanyLut]:
    await _verify_company_tenant_access(session, tenant, company_id)
    stmt = (
        select(CompanyLut)
        .where(CompanyLut.company_id == company_id)
        .order_by(CompanyLut.valid_from.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_company_lut(
    session: AsyncSession, tenant: Tenant, company_id: UUID, lut_id: UUID
) -> CompanyLut:
    await _verify_company_tenant_access(session, tenant, company_id)
    stmt = select(CompanyLut).where(
        and_(CompanyLut.id == lut_id, CompanyLut.company_id == company_id)
    )
    result = await session.execute(stmt)
    lut = result.scalar_one_or_none()
    if not lut:
        raise CompanyLutNotFoundError("Company LUT not found")
    return lut


async def create_company_lut(
    session: AsyncSession, tenant: Tenant, company_id: UUID, payload: CompanyLutCreate
) -> CompanyLut:
    await _verify_company_tenant_access(session, tenant, company_id)
    await _verify_gst_registration_company(session, company_id, payload.gst_registration_id)
    await _verify_financial_year_company(session, company_id, payload.financial_year_id)
    await _check_active_lut_uniqueness(
        session, company_id, payload.gst_registration_id, payload.financial_year_id
    )

    if payload.valid_to and payload.valid_to < payload.valid_from:
        raise CompanyLutStateConflictError("valid_to cannot be earlier than valid_from")

    lut = CompanyLut(
        company_id=company_id,
        gst_registration_id=payload.gst_registration_id,
        financial_year_id=payload.financial_year_id,
        lut_reference=payload.lut_reference,
        valid_from=payload.valid_from,
        valid_to=payload.valid_to,
        status=CompanyLutStatus.ACTIVE,
    )
    session.add(lut)
    await session.commit()
    await session.refresh(lut)
    return lut


async def inactivate_company_lut(
    session: AsyncSession, tenant: Tenant, company_id: UUID, lut_id: UUID
) -> CompanyLut:
    await _verify_company_tenant_access(session, tenant, company_id)

    stmt = select(CompanyLut).where(
        and_(CompanyLut.id == lut_id, CompanyLut.company_id == company_id)
    )
    result = await session.execute(stmt)
    lut = result.scalar_one_or_none()
    if not lut:
        raise CompanyLutNotFoundError("Company LUT not found")

    if lut.status == CompanyLutStatus.INACTIVE:
        return lut  # Idempotent

    lut.status = CompanyLutStatus.INACTIVE
    await session.commit()
    await session.refresh(lut)
    return lut


async def activate_company_lut(
    session: AsyncSession, tenant: Tenant, company_id: UUID, lut_id: UUID
) -> CompanyLut:
    await _verify_company_tenant_access(session, tenant, company_id)

    stmt = select(CompanyLut).where(
        and_(CompanyLut.id == lut_id, CompanyLut.company_id == company_id)
    )
    result = await session.execute(stmt)
    lut = result.scalar_one_or_none()
    if not lut:
        raise CompanyLutNotFoundError("Company LUT not found")

    if lut.status == CompanyLutStatus.ACTIVE:
        return lut  # Idempotent

    await _check_active_lut_uniqueness(
        session, company_id, lut.gst_registration_id, lut.financial_year_id
    )

    lut.status = CompanyLutStatus.ACTIVE
    await session.commit()
    await session.refresh(lut)
    return lut
