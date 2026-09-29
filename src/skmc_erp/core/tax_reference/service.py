from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.core.company.model import Company, CompanyStatus
from skmc_erp.core.tax_reference.model import CompanyHsnSacCode, CompanyHsnSacTaxRate, TaxRate, TaxReferenceStatus, TaxType
from skmc_erp.core.tax_reference.schema import CompanyHsnSacCodeCreate, CompanyHsnSacCodeUpdate, CompanyHsnSacTaxRateCreate
from skmc_erp.core.tenant.model import Tenant


class HsnSacNotFoundError(Exception):
    pass


class HsnSacInputError(Exception):
    pass


class HsnSacStateConflictError(Exception):
    pass


async def _company(session: AsyncSession, tenant: Tenant, company_id: UUID) -> Company:
    company = await session.scalar(select(Company).where(Company.id == company_id, Company.tenant_id == tenant.id))
    if company is None:
        raise HsnSacNotFoundError("Company not found")
    return company


async def _mutable_company(
    session: AsyncSession, tenant: Tenant, company_id: UUID
) -> Company:
    company = await _company(session, tenant, company_id)
    if company.status is CompanyStatus.INACTIVE:
        raise HsnSacStateConflictError("Company is inactive")
    return company


async def create_hsn_sac_code(*, session: AsyncSession, tenant: Tenant, company_id: UUID, code_data: CompanyHsnSacCodeCreate) -> CompanyHsnSacCode:
    await _mutable_company(session, tenant, company_id)
    item = CompanyHsnSacCode(company_id=company_id, **code_data.model_dump(), status=TaxReferenceStatus.ACTIVE)
    session.add(item)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HsnSacStateConflictError("HSN/SAC Code conflicts with existing Company configuration") from exc
    await session.refresh(item)
    return item


async def list_hsn_sac_codes(*, session: AsyncSession, tenant: Tenant, company_id: UUID) -> Sequence[CompanyHsnSacCode]:
    await _company(session, tenant, company_id)
    result = await session.scalars(select(CompanyHsnSacCode).where(CompanyHsnSacCode.company_id == company_id).order_by(CompanyHsnSacCode.classification_type, CompanyHsnSacCode.code))
    return result.all()


async def get_hsn_sac_code(*, session: AsyncSession, tenant: Tenant, company_id: UUID, code_id: UUID) -> CompanyHsnSacCode | None:
    return await session.scalar(select(CompanyHsnSacCode).join(Company, CompanyHsnSacCode.company_id == Company.id).where(CompanyHsnSacCode.id == code_id, CompanyHsnSacCode.company_id == company_id, Company.tenant_id == tenant.id))


async def update_hsn_sac_code(*, session: AsyncSession, tenant: Tenant, company_id: UUID, code_id: UUID, code_data: CompanyHsnSacCodeUpdate) -> CompanyHsnSacCode | None:
    await _mutable_company(session, tenant, company_id)
    item = await get_hsn_sac_code(session=session, tenant=tenant, company_id=company_id, code_id=code_id)
    if item is None:
        return None
    if item.status is TaxReferenceStatus.INACTIVE:
        raise HsnSacStateConflictError("Inactive HSN/SAC Code cannot be changed")
    item.description = code_data.description
    item.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(item)
    return item


async def inactivate_hsn_sac_code(*, session: AsyncSession, tenant: Tenant, company_id: UUID, code_id: UUID) -> CompanyHsnSacCode | None:
    await _mutable_company(session, tenant, company_id)
    item = await get_hsn_sac_code(session=session, tenant=tenant, company_id=company_id, code_id=code_id)
    if item is None:
        return None
    if item.status is TaxReferenceStatus.INACTIVE:
        return item
    item.status = TaxReferenceStatus.INACTIVE
    item.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(item)
    return item


async def create_hsn_sac_tax_rate(*, session: AsyncSession, tenant: Tenant, company_id: UUID, code_id: UUID, mapping_data: CompanyHsnSacTaxRateCreate) -> CompanyHsnSacTaxRate:
    await _mutable_company(session, tenant, company_id)
    code = await get_hsn_sac_code(session=session, tenant=tenant, company_id=company_id, code_id=code_id)
    if code is None:
        raise HsnSacNotFoundError("HSN/SAC Code not found")
    if code.status is TaxReferenceStatus.INACTIVE:
        raise HsnSacStateConflictError("Inactive HSN/SAC Code cannot be changed")
    tax_rate = await session.scalar(select(TaxRate).join(TaxType, TaxRate.tax_type_id == TaxType.id).where(TaxRate.id == mapping_data.tax_rate_id, TaxType.code == "GST"))
    if tax_rate is None:
        raise HsnSacInputError("GST Tax Rate does not exist")
    mapping = CompanyHsnSacTaxRate(company_hsn_sac_code_id=code.id, **mapping_data.model_dump(), status=TaxReferenceStatus.ACTIVE)
    session.add(mapping)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HsnSacStateConflictError("HSN/SAC Tax Rate conflicts with an existing active effective period") from exc
    await session.refresh(mapping)
    return mapping


async def list_hsn_sac_tax_rates(*, session: AsyncSession, tenant: Tenant, company_id: UUID, code_id: UUID) -> Sequence[CompanyHsnSacTaxRate]:
    code = await get_hsn_sac_code(session=session, tenant=tenant, company_id=company_id, code_id=code_id)
    if code is None:
        raise HsnSacNotFoundError("HSN/SAC Code not found")
    result = await session.scalars(select(CompanyHsnSacTaxRate).where(CompanyHsnSacTaxRate.company_hsn_sac_code_id == code.id).order_by(CompanyHsnSacTaxRate.valid_from, CompanyHsnSacTaxRate.id))
    return result.all()


async def _mapping(session: AsyncSession, tenant: Tenant, company_id: UUID, code_id: UUID, mapping_id: UUID) -> CompanyHsnSacTaxRate | None:
    code = await get_hsn_sac_code(session=session, tenant=tenant, company_id=company_id, code_id=code_id)
    if code is None:
        return None
    return await session.scalar(select(CompanyHsnSacTaxRate).where(CompanyHsnSacTaxRate.id == mapping_id, CompanyHsnSacTaxRate.company_hsn_sac_code_id == code.id))


async def end_hsn_sac_tax_rate(*, session: AsyncSession, tenant: Tenant, company_id: UUID, code_id: UUID, mapping_id: UUID, end_date) -> CompanyHsnSacTaxRate | None:
    await _mutable_company(session, tenant, company_id)
    code = await get_hsn_sac_code(session=session, tenant=tenant, company_id=company_id, code_id=code_id)
    if code is not None and code.status is TaxReferenceStatus.INACTIVE:
        raise HsnSacStateConflictError("Inactive HSN/SAC Code cannot be changed")
    mapping = await _mapping(session, tenant, company_id, code_id, mapping_id)
    if mapping is None:
        return None
    if end_date < mapping.valid_from:
        raise HsnSacInputError("end_date must be on or after valid_from")
    mapping.valid_to = end_date
    mapping.updated_at = datetime.now(UTC)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HsnSacStateConflictError("HSN/SAC Tax Rate could not be ended due to a data conflict") from exc
    await session.refresh(mapping)
    return mapping


async def inactivate_hsn_sac_tax_rate(*, session: AsyncSession, tenant: Tenant, company_id: UUID, code_id: UUID, mapping_id: UUID) -> CompanyHsnSacTaxRate | None:
    await _mutable_company(session, tenant, company_id)
    code = await get_hsn_sac_code(session=session, tenant=tenant, company_id=company_id, code_id=code_id)
    if code is not None and code.status is TaxReferenceStatus.INACTIVE:
        raise HsnSacStateConflictError("Inactive HSN/SAC Code cannot be changed")
    mapping = await _mapping(session, tenant, company_id, code_id, mapping_id)
    if mapping is None:
        return None
    mapping.status = TaxReferenceStatus.INACTIVE
    mapping.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(mapping)
    return mapping
