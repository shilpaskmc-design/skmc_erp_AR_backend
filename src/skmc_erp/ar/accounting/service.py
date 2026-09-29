from datetime import date, timedelta
from typing import Sequence
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.ar.accounting.model import (
    AccountingMappingStatus,
    RevenueGlMapping,
    TaxGlAccountMapping,
)
from skmc_erp.ar.accounting.schema import (
    APPROVED_SUPPLY_TYPES,
    RevenueGlMappingCreate,
    RevenueGlMappingEnd,
    TaxGlAccountMappingCreate,
    TaxGlAccountMappingEnd,
    TaxGlAccountMappingRemap,
)
from skmc_erp.ar.catalogue.model import CatalogueStatus, ServiceType, Sku
from skmc_erp.core.accounting.model import GlAccount
from skmc_erp.core.company.model import Company
from skmc_erp.core.company_location.model import CompanyLocation
from skmc_erp.core.tax_reference.model import TaxStatutoryCode
from skmc_erp.core.tenant.model import Tenant


class AccountingMappingInputError(Exception):
    pass


class AccountingMappingStateConflictError(Exception):
    pass


class RevenueGlMappingAmbiguityError(AccountingMappingStateConflictError):
    pass


class AccountingMappingNotFoundError(Exception):
    pass


async def _verify_company_tenant_access(
    session: AsyncSession, tenant: Tenant, company_id: UUID
) -> None:
    stmt = select(Company.id).where(
        and_(Company.id == company_id, Company.tenant_id == tenant.id)
    )
    result = await session.execute(stmt)
    if result.scalar_one_or_none() is None:
        raise AccountingMappingNotFoundError("Company not found or access denied")


async def _verify_gl_account_company(
    session: AsyncSession, company_id: UUID, gl_account_id: UUID, require_active: bool = False
) -> None:
    stmt = select(GlAccount).where(
        and_(GlAccount.id == gl_account_id, GlAccount.company_id == company_id)
    )
    result = await session.execute(stmt)
    account = result.scalar_one_or_none()
    if account is None:
        raise AccountingMappingStateConflictError("GL Account must belong to the same Company")
    if require_active and account.status != "ACTIVE":
        raise AccountingMappingStateConflictError("GL Account must be ACTIVE for creation of a new mapping")


async def _verify_service_type_company(
    session: AsyncSession, company_id: UUID, service_type_id: UUID, require_active: bool = False
) -> None:
    stmt = select(ServiceType).where(
        and_(ServiceType.id == service_type_id, ServiceType.company_id == company_id)
    )
    result = await session.execute(stmt)
    st = result.scalar_one_or_none()
    if st is None:
        raise AccountingMappingStateConflictError("Service Type must belong to the same Company")
    if require_active and st.status != CatalogueStatus.ACTIVE:
        raise AccountingMappingStateConflictError("Service Type must be ACTIVE for creation of a new mapping")


async def _verify_sku_company(
    session: AsyncSession, company_id: UUID, sku_id: UUID, require_active: bool = False
) -> None:
    stmt = select(Sku).where(
        and_(Sku.id == sku_id, Sku.company_id == company_id)
    )
    result = await session.execute(stmt)
    sku = result.scalar_one_or_none()
    if sku is None:
        raise AccountingMappingStateConflictError("SKU must belong to the same Company")
    if require_active and sku.status != CatalogueStatus.ACTIVE:
        raise AccountingMappingStateConflictError("SKU must be ACTIVE for creation of a new mapping")


async def _verify_company_location_company(
    session: AsyncSession, company_id: UUID, company_location_id: UUID, require_active: bool = False
) -> None:
    stmt = select(CompanyLocation).where(
        and_(CompanyLocation.id == company_location_id, CompanyLocation.company_id == company_id)
    )
    result = await session.execute(stmt)
    loc = result.scalar_one_or_none()
    if loc is None:
        raise AccountingMappingStateConflictError("Company Location must belong to the same Company")
    if require_active and loc.status != "ACTIVE":
        raise AccountingMappingStateConflictError("Company Location must be ACTIVE for creation of a new mapping")


async def _verify_tax_statutory_code(
    session: AsyncSession, tax_statutory_code_id: UUID
) -> None:
    stmt = select(TaxStatutoryCode.id).where(
        TaxStatutoryCode.id == tax_statutory_code_id
    )
    result = await session.execute(stmt)
    if result.scalar_one_or_none() is None:
        raise AccountingMappingStateConflictError("Tax Statutory Code does not exist")


async def _check_tax_mapping_overlap(
    session: AsyncSession,
    company_id: UUID,
    tax_statutory_code_id: UUID,
    valid_from: date,
    valid_to: date | None,
    exclude_mapping_id: UUID | None = None,
) -> None:
    conditions = [
        TaxGlAccountMapping.company_id == company_id,
        TaxGlAccountMapping.tax_statutory_code_id == tax_statutory_code_id,
        TaxGlAccountMapping.valid_from <= (valid_to if valid_to else date.max),
    ]
    if valid_from is not None:
        conditions.append(
            or_(
                TaxGlAccountMapping.valid_to >= valid_from,
                TaxGlAccountMapping.valid_to.is_(None),
            )
        )

    if exclude_mapping_id:
        conditions.append(TaxGlAccountMapping.id != exclude_mapping_id)

    stmt = select(TaxGlAccountMapping.id).where(and_(*conditions)).limit(1)
    result = await session.execute(stmt)
    if result.scalar_one_or_none() is not None:
        raise AccountingMappingStateConflictError("Effective date range overlaps with an existing mapping")


async def _check_revenue_mapping_overlap(
    session: AsyncSession,
    company_id: UUID,
    service_type_id: UUID | None,
    sku_id: UUID | None,
    supply_type_code: str | None,
    company_location_id: UUID | None,
    valid_from: date,
    valid_to: date | None,
    exclude_mapping_id: UUID | None = None,
) -> None:
    conditions = [
        RevenueGlMapping.company_id == company_id,
        RevenueGlMapping.status == AccountingMappingStatus.ACTIVE,
        RevenueGlMapping.valid_from <= (valid_to if valid_to else date.max),
    ]

    if valid_from is not None:
        conditions.append(
            or_(
                RevenueGlMapping.valid_to >= valid_from,
                RevenueGlMapping.valid_to.is_(None),
            )
        )

    if service_type_id is not None:
        conditions.append(RevenueGlMapping.service_type_id == service_type_id)
    else:
        conditions.append(RevenueGlMapping.service_type_id.is_(None))

    if sku_id is not None:
        conditions.append(RevenueGlMapping.sku_id == sku_id)
    else:
        conditions.append(RevenueGlMapping.sku_id.is_(None))

    if supply_type_code is not None:
        conditions.append(RevenueGlMapping.supply_type_code == supply_type_code)
    else:
        conditions.append(RevenueGlMapping.supply_type_code.is_(None))

    if company_location_id is not None:
        conditions.append(RevenueGlMapping.company_location_id == company_location_id)
    else:
        conditions.append(RevenueGlMapping.company_location_id.is_(None))

    if exclude_mapping_id:
        conditions.append(RevenueGlMapping.id != exclude_mapping_id)

    stmt = select(RevenueGlMapping.id).where(and_(*conditions)).limit(1)
    result = await session.execute(stmt)
    if result.scalar_one_or_none() is not None:
        raise AccountingMappingStateConflictError(
            "Effective date range overlaps with an existing Revenue GL mapping for the same criteria"
        )


# --- Tax GL Account Mappings ---

async def list_tax_gl_account_mappings(
    session: AsyncSession, tenant: Tenant, company_id: UUID
) -> Sequence[TaxGlAccountMapping]:
    await _verify_company_tenant_access(session, tenant, company_id)
    stmt = (
        select(TaxGlAccountMapping)
        .where(TaxGlAccountMapping.company_id == company_id)
        .order_by(TaxGlAccountMapping.valid_from.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def assign_tax_gl_account_mapping(
    session: AsyncSession, tenant: Tenant, company_id: UUID, payload: TaxGlAccountMappingCreate
) -> TaxGlAccountMapping:
    await _verify_company_tenant_access(session, tenant, company_id)
    await _verify_gl_account_company(session, company_id, payload.gl_account_id)
    await _verify_tax_statutory_code(session, payload.tax_statutory_code_id)
    await _check_tax_mapping_overlap(
        session, company_id, payload.tax_statutory_code_id, payload.valid_from, None
    )

    mapping = TaxGlAccountMapping(
        company_id=company_id,
        tax_statutory_code_id=payload.tax_statutory_code_id,
        gl_account_id=payload.gl_account_id,
        valid_from=payload.valid_from,
        valid_to=None,
        status=AccountingMappingStatus.ACTIVE,
    )
    session.add(mapping)
    await session.commit()
    await session.refresh(mapping)
    return mapping


async def remap_tax_gl_account_mapping(
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    mapping_id: UUID,
    payload: TaxGlAccountMappingRemap,
) -> TaxGlAccountMapping:
    await _verify_company_tenant_access(session, tenant, company_id)

    stmt = select(TaxGlAccountMapping).where(
        and_(
            TaxGlAccountMapping.id == mapping_id,
            TaxGlAccountMapping.company_id == company_id,
        )
    )
    result = await session.execute(stmt)
    old_mapping = result.scalar_one_or_none()
    if not old_mapping:
        raise AccountingMappingNotFoundError("Tax GL Account mapping not found")

    if old_mapping.status != AccountingMappingStatus.ACTIVE:
        raise AccountingMappingStateConflictError("Cannot remap an inactive mapping")

    if payload.valid_from <= old_mapping.valid_from:
        raise AccountingMappingStateConflictError("New mapping valid_from must be after the old mapping valid_from")

    await _verify_gl_account_company(session, company_id, payload.gl_account_id)

    new_valid_from = payload.valid_from
    old_valid_to = new_valid_from - timedelta(days=1)

    await _check_tax_mapping_overlap(
        session, company_id, old_mapping.tax_statutory_code_id, new_valid_from, None, exclude_mapping_id=mapping_id
    )

    old_mapping.valid_to = old_valid_to
    old_mapping.status = AccountingMappingStatus.INACTIVE

    new_mapping = TaxGlAccountMapping(
        company_id=company_id,
        tax_statutory_code_id=old_mapping.tax_statutory_code_id,
        gl_account_id=payload.gl_account_id,
        valid_from=new_valid_from,
        valid_to=None,
        status=AccountingMappingStatus.ACTIVE,
    )
    session.add(new_mapping)
    await session.commit()
    await session.refresh(new_mapping)
    return new_mapping


async def end_tax_gl_account_mapping(
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    mapping_id: UUID,
    payload: TaxGlAccountMappingEnd,
) -> TaxGlAccountMapping:
    await _verify_company_tenant_access(session, tenant, company_id)

    stmt = select(TaxGlAccountMapping).where(
        and_(
            TaxGlAccountMapping.id == mapping_id,
            TaxGlAccountMapping.company_id == company_id,
        )
    )
    result = await session.execute(stmt)
    mapping = result.scalar_one_or_none()
    if not mapping:
        raise AccountingMappingNotFoundError("Tax GL Account mapping not found")

    if mapping.status != AccountingMappingStatus.ACTIVE:
        raise AccountingMappingStateConflictError("Cannot end an inactive mapping")

    if payload.valid_to < mapping.valid_from:
        raise AccountingMappingStateConflictError("valid_to cannot be earlier than valid_from")

    mapping.valid_to = payload.valid_to
    mapping.status = AccountingMappingStatus.INACTIVE
    await session.commit()
    await session.refresh(mapping)
    return mapping


# --- Revenue GL Mappings ---

async def assign_revenue_gl_mapping(
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    payload: RevenueGlMappingCreate,
) -> RevenueGlMapping:
    await _verify_company_tenant_access(session, tenant, company_id)

    has_service = payload.service_type_id is not None
    has_sku = payload.sku_id is not None
    if has_service == has_sku:
        raise AccountingMappingInputError(
            "Revenue GL mapping must specify exactly one of service_type_id or sku_id"
        )

    if payload.supply_type_code is not None:
        if payload.supply_type_code not in APPROVED_SUPPLY_TYPES:
            raise AccountingMappingInputError(
                f"Invalid or unapproved supply_type_code: {payload.supply_type_code}"
            )

    if payload.valid_to is not None and payload.valid_to < payload.valid_from:
        raise AccountingMappingStateConflictError(
            "valid_to cannot be earlier than valid_from"
        )

    if payload.service_type_id:
        await _verify_service_type_company(
            session, company_id, payload.service_type_id, require_active=True
        )
    if payload.sku_id:
        await _verify_sku_company(
            session, company_id, payload.sku_id, require_active=True
        )
    if payload.company_location_id:
        await _verify_company_location_company(
            session, company_id, payload.company_location_id, require_active=True
        )
    await _verify_gl_account_company(
        session, company_id, payload.gl_account_id, require_active=True
    )

    await _check_revenue_mapping_overlap(
        session,
        company_id,
        payload.service_type_id,
        payload.sku_id,
        payload.supply_type_code,
        payload.company_location_id,
        payload.valid_from,
        payload.valid_to,
    )

    mapping = RevenueGlMapping(
        company_id=company_id,
        service_type_id=payload.service_type_id,
        sku_id=payload.sku_id,
        supply_type_code=payload.supply_type_code,
        company_location_id=payload.company_location_id,
        gl_account_id=payload.gl_account_id,
        valid_from=payload.valid_from,
        valid_to=payload.valid_to,
        status=AccountingMappingStatus.ACTIVE,
    )
    session.add(mapping)
    await session.commit()
    await session.refresh(mapping)
    return mapping


async def list_revenue_gl_mappings(
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    service_type_id: UUID | None = None,
    sku_id: UUID | None = None,
    supply_type_code: str | None = None,
    company_location_id: UUID | None = None,
    status_filter: str | None = None,
) -> Sequence[RevenueGlMapping]:
    await _verify_company_tenant_access(session, tenant, company_id)
    conditions = [RevenueGlMapping.company_id == company_id]
    if service_type_id is not None:
        conditions.append(RevenueGlMapping.service_type_id == service_type_id)
    if sku_id is not None:
        conditions.append(RevenueGlMapping.sku_id == sku_id)
    if supply_type_code is not None:
        conditions.append(RevenueGlMapping.supply_type_code == supply_type_code)
    if company_location_id is not None:
        conditions.append(RevenueGlMapping.company_location_id == company_location_id)
    if status_filter is not None:
        conditions.append(RevenueGlMapping.status == status_filter)

    stmt = (
        select(RevenueGlMapping)
        .where(and_(*conditions))
        .order_by(RevenueGlMapping.valid_from.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_revenue_gl_mapping(
    session: AsyncSession, tenant: Tenant, company_id: UUID, mapping_id: UUID
) -> RevenueGlMapping:
    await _verify_company_tenant_access(session, tenant, company_id)
    stmt = select(RevenueGlMapping).where(
        and_(
            RevenueGlMapping.id == mapping_id,
            RevenueGlMapping.company_id == company_id,
        )
    )
    result = await session.execute(stmt)
    mapping = result.scalar_one_or_none()
    if not mapping:
        raise AccountingMappingNotFoundError("Revenue GL mapping not found")
    return mapping


async def end_revenue_gl_mapping(
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    mapping_id: UUID,
    payload: RevenueGlMappingEnd,
) -> RevenueGlMapping:
    await _verify_company_tenant_access(session, tenant, company_id)
    stmt = select(RevenueGlMapping).where(
        and_(
            RevenueGlMapping.id == mapping_id,
            RevenueGlMapping.company_id == company_id,
        )
    )
    result = await session.execute(stmt)
    mapping = result.scalar_one_or_none()
    if not mapping:
        raise AccountingMappingNotFoundError("Revenue GL mapping not found")

    if mapping.status != AccountingMappingStatus.ACTIVE:
        raise AccountingMappingStateConflictError("Cannot end an inactive mapping")

    if payload.valid_to < mapping.valid_from:
        raise AccountingMappingStateConflictError("valid_to cannot be earlier than valid_from")

    mapping.valid_to = payload.valid_to
    mapping.status = AccountingMappingStatus.INACTIVE
    await session.commit()
    await session.refresh(mapping)
    return mapping


async def inactivate_revenue_gl_mapping(
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    mapping_id: UUID,
) -> RevenueGlMapping:
    await _verify_company_tenant_access(session, tenant, company_id)
    stmt = select(RevenueGlMapping).where(
        and_(
            RevenueGlMapping.id == mapping_id,
            RevenueGlMapping.company_id == company_id,
        )
    )
    result = await session.execute(stmt)
    mapping = result.scalar_one_or_none()
    if not mapping:
        raise AccountingMappingNotFoundError("Revenue GL mapping not found")

    if mapping.status != AccountingMappingStatus.ACTIVE:
        raise AccountingMappingStateConflictError("Mapping is already inactive")

    mapping.status = AccountingMappingStatus.INACTIVE
    await session.commit()
    await session.refresh(mapping)
    return mapping


async def resolve_revenue_gl_mapping(
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    service_type_id: UUID | None,
    sku_id: UUID | None,
    supply_type_code: str | None,
    company_location_id: UUID | None,
    effective_on: date,
) -> RevenueGlMapping:
    await _verify_company_tenant_access(session, tenant, company_id)

    has_service = service_type_id is not None
    has_sku = sku_id is not None
    if has_service == has_sku:
        raise AccountingMappingInputError(
            "Resolver requires exactly one of service_type_id or sku_id"
        )

    item_filter = (
        RevenueGlMapping.service_type_id == service_type_id
        if has_service
        else RevenueGlMapping.sku_id == sku_id
    )

    stmt = select(RevenueGlMapping).where(
        and_(
            RevenueGlMapping.company_id == company_id,
            RevenueGlMapping.status == AccountingMappingStatus.ACTIVE,
            RevenueGlMapping.valid_from <= effective_on,
            or_(
                RevenueGlMapping.valid_to.is_(None),
                effective_on <= RevenueGlMapping.valid_to,
            ),
            item_filter,
        )
    )
    result = await session.execute(stmt)
    candidates = result.scalars().all()

    tier1: list[RevenueGlMapping] = []
    tier2: list[RevenueGlMapping] = []
    tier3: list[RevenueGlMapping] = []
    tier4: list[RevenueGlMapping] = []

    for r in candidates:
        if r.supply_type_code is not None:
            if supply_type_code is None or r.supply_type_code != supply_type_code:
                continue
            supply_matched_specific = True
        else:
            supply_matched_specific = False

        if r.company_location_id is not None:
            if company_location_id is None or r.company_location_id != company_location_id:
                continue
            loc_matched_specific = True
        else:
            loc_matched_specific = False

        if supply_matched_specific and loc_matched_specific:
            tier1.append(r)
        elif supply_matched_specific:
            tier2.append(r)
        elif loc_matched_specific:
            tier3.append(r)
        else:
            tier4.append(r)

    if tier1:
        if len(tier1) > 1:
            raise RevenueGlMappingAmbiguityError(
                "Multiple active Revenue GL mappings match at precedence level 1 (Item + Supply + Location)"
            )
        return tier1[0]

    if tier2:
        if len(tier2) > 1:
            raise RevenueGlMappingAmbiguityError(
                "Multiple active Revenue GL mappings match at precedence level 2 (Item + Supply)"
            )
        return tier2[0]

    if tier3:
        if len(tier3) > 1:
            raise RevenueGlMappingAmbiguityError(
                "Multiple active Revenue GL mappings match at precedence level 3 (Item + Location)"
            )
        return tier3[0]

    if tier4:
        if len(tier4) > 1:
            raise RevenueGlMappingAmbiguityError(
                "Multiple active Revenue GL mappings match at precedence level 4 (Item only)"
            )
        return tier4[0]

    raise AccountingMappingNotFoundError(
        "No active Revenue GL mapping found for the specified criteria"
    )
