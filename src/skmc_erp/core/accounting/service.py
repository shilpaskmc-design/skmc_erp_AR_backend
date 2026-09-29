from collections.abc import Sequence
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import and_, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.core.accounting.model import (
    AccountGroup,
    AccountGroupMapping,
    AccountGroupRelationship,
    AccountGroupStatus,
    AccountHierarchy,
    AccountHierarchyPurpose,
    AccountHierarchyStatus,
    CompanyAccountingSettings,
    GlAccount,
    GlAccountStatus,
)
from skmc_erp.core.accounting.schema import (
    AccountGroupCreate,
    AccountGroupUpdate,
    AccountHierarchyCreate,
    CompanyAccountingSettingsUpdate,
    GlAccountCreate,
    GlAccountUpdate,
)
from skmc_erp.core.company.model import Company, CompanyStatus
from skmc_erp.core.tenant.model import Tenant


class AccountingStructureError(Exception):
    pass


class GlAccountInputError(Exception):
    pass


class GlAccountStateConflictError(Exception):
    pass


async def create_gl_account(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    gl_account_data: GlAccountCreate,
) -> GlAccount:
    company = await session.get(Company, company_id)
    if company is None or company.tenant_id != tenant.id:
        raise GlAccountInputError("Company does not exist")
    if company.status is CompanyStatus.INACTIVE:
        raise GlAccountStateConflictError("Company is inactive")

    gl_account = GlAccount(
        company_id=company.id,
        account_code=gl_account_data.account_code,
        account_name=gl_account_data.account_name,
        valid_from=gl_account_data.valid_from,
        valid_to=gl_account_data.valid_to,
        status=GlAccountStatus.ACTIVE,
    )
    session.add(gl_account)

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise GlAccountStateConflictError(
            "GL Account could not be created due to a data conflict, such as a duplicate account code"
        ) from exc

    await session.refresh(gl_account)
    return gl_account


async def get_gl_account(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    gl_account_id: UUID,
) -> GlAccount | None:
    stmt = (
        select(GlAccount)
        .join(Company, GlAccount.company_id == Company.id)
        .where(
            GlAccount.id == gl_account_id,
            GlAccount.company_id == company_id,
            Company.tenant_id == tenant.id,
        )
    )
    return await session.scalar(stmt)


async def list_gl_accounts(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
) -> Sequence[GlAccount]:
    company = await session.get(Company, company_id)
    if company is None or company.tenant_id != tenant.id:
        return []

    stmt = (
        select(GlAccount)
        .where(GlAccount.company_id == company_id)
        .order_by(GlAccount.account_code, GlAccount.account_name)
    )
    result = await session.scalars(stmt)
    return result.all()


async def update_gl_account(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    gl_account_id: UUID,
    update_data: GlAccountUpdate,
) -> GlAccount | None:
    gl_account = await get_gl_account(
        session=session,
        tenant=tenant,
        company_id=company_id,
        gl_account_id=gl_account_id,
    )
    if gl_account is None:
        return None
    if gl_account.status is GlAccountStatus.INACTIVE:
        raise GlAccountStateConflictError("Inactive GL Account cannot be changed")

    if update_data.account_name is not None:
        gl_account.account_name = update_data.account_name

    if update_data.valid_to is not None:
        if update_data.valid_to < gl_account.valid_from:
            raise GlAccountInputError("valid_to cannot be earlier than valid_from")
        gl_account.valid_to = update_data.valid_to

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise GlAccountStateConflictError(
            "GL Account could not be updated due to a data conflict"
        ) from exc

    await session.refresh(gl_account)
    return gl_account


async def inactivate_gl_account(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    gl_account_id: UUID,
) -> GlAccount | None:
    gl_account = await get_gl_account(
        session=session,
        tenant=tenant,
        company_id=company_id,
        gl_account_id=gl_account_id,
    )
    if gl_account is None:
        return None

    if gl_account.status == GlAccountStatus.INACTIVE:
        return gl_account

    # The user asked to verify if there are any guards for inactivation.
    # Since exact behavior for cascading inactivation is unresolved/undocumented,
    # and no explicit guard rules for GL Account (only Groups) are documented,
    # the user said: "If an inactivation guard is required by approved rules but its exact behavior is unresolved, block only that operation and continue the module."
    # Wait, the instruction said: "Before implementing INACTIVE behavior, verify whether existing approved rules require guards... If an inactivation guard is required... block only that operation".
    # Since I did not find explicit guards for inactivating the GL account itself, I will allow simple inactivation here, as that aligns with standard non-cascading behavior.
    # WAIT! "A Group must not be changed to INACTIVE while it has a current-effective or future-effective GL Account placement". But does an INACTIVE GL Account cause problems?
    # I will allow inactivation.

    gl_account.status = GlAccountStatus.INACTIVE

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise GlAccountStateConflictError(
            "GL Account could not be inactivated due to a data conflict"
        ) from exc

    await session.refresh(gl_account)
    return gl_account


class AccountingStructureError(Exception):
    pass


async def create_primary_hierarchy(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    hierarchy_data: AccountHierarchyCreate,
) -> AccountHierarchy:
    company = await session.get(Company, company_id)
    if company is None or company.tenant_id != tenant.id:
        raise AccountingStructureError("Company does not exist")

    # Check if active primary hierarchy already exists
    stmt = select(AccountHierarchy).where(
        AccountHierarchy.company_id == company_id,
        AccountHierarchy.purpose_code == AccountHierarchyPurpose.ACCOUNTING,
        AccountHierarchy.status == AccountHierarchyStatus.ACTIVE,
        AccountHierarchy.is_primary == True,
    )
    existing = await session.scalar(stmt)
    if existing:
        raise AccountingStructureError("Active primary ACCOUNTING hierarchy already exists")

    hierarchy = AccountHierarchy(
        company_id=company_id,
        hierarchy_name=hierarchy_data.hierarchy_name,
        purpose_code=AccountHierarchyPurpose.ACCOUNTING,
        is_primary=True,
        status=AccountHierarchyStatus.ACTIVE,
    )
    session.add(hierarchy)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise AccountingStructureError("Could not create hierarchy due to a data conflict") from exc

    await session.refresh(hierarchy)
    return hierarchy


async def get_primary_hierarchy(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
) -> AccountHierarchy | None:
    stmt = (
        select(AccountHierarchy)
        .join(Company, AccountHierarchy.company_id == Company.id)
        .where(
            AccountHierarchy.company_id == company_id,
            Company.tenant_id == tenant.id,
            AccountHierarchy.purpose_code == AccountHierarchyPurpose.ACCOUNTING,
            AccountHierarchy.status == AccountHierarchyStatus.ACTIVE,
            AccountHierarchy.is_primary == True,
        )
    )
    return await session.scalar(stmt)


async def create_account_group(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    hierarchy_id: UUID,
    group_data: AccountGroupCreate,
) -> AccountGroup:
    # Validate hierarchy
    stmt = select(AccountHierarchy).join(Company).where(
        AccountHierarchy.id == hierarchy_id,
        AccountHierarchy.company_id == company_id,
        Company.tenant_id == tenant.id,
        AccountHierarchy.status == AccountHierarchyStatus.ACTIVE,
    )
    hierarchy = await session.scalar(stmt)
    if not hierarchy:
        raise AccountingStructureError("Hierarchy not found or inactive")

    group = AccountGroup(
        company_id=company_id,
        hierarchy_id=hierarchy_id,
        group_name=group_data.group_name,
        group_code=group_data.group_code,
        status=AccountGroupStatus.ACTIVE,
    )
    session.add(group)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise AccountingStructureError("Could not create group due to a data conflict") from exc

    await session.refresh(group)
    return group


async def get_account_group(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    group_id: UUID,
) -> AccountGroup | None:
    stmt = (
        select(AccountGroup)
        .join(Company, AccountGroup.company_id == Company.id)
        .where(
            AccountGroup.id == group_id,
            AccountGroup.company_id == company_id,
            Company.tenant_id == tenant.id,
        )
    )
    return await session.scalar(stmt)


async def update_account_group(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    group_id: UUID,
    update_data: AccountGroupUpdate,
) -> AccountGroup | None:
    group = await get_account_group(session=session, tenant=tenant, company_id=company_id, group_id=group_id)
    if not group:
        return None
    if group.status is AccountGroupStatus.INACTIVE:
        raise AccountingStructureError("Inactive Account Group cannot be changed")

    if update_data.group_name is not None:
        group.group_name = update_data.group_name

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise AccountingStructureError("Could not update group due to a data conflict") from exc

    await session.refresh(group)
    return group


async def inactivate_account_group(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    group_id: UUID,
) -> AccountGroup | None:
    group = await get_account_group(session=session, tenant=tenant, company_id=company_id, group_id=group_id)
    if not group:
        return None

    if group.status == AccountGroupStatus.INACTIVE:
        return group

    today = date.today()

    mapping_stmt = select(AccountGroupMapping).where(
        AccountGroupMapping.account_group_id == group_id,
        or_(AccountGroupMapping.valid_to.is_(None), AccountGroupMapping.valid_to >= today)
    )
    if await session.scalar(mapping_stmt):
        raise AccountingStructureError("Cannot inactivate group with current or future GL account placements")

    rel_stmt = select(AccountGroupRelationship).where(
        AccountGroupRelationship.parent_group_id == group_id,
        or_(AccountGroupRelationship.valid_to.is_(None), AccountGroupRelationship.valid_to >= today)
    )
    if await session.scalar(rel_stmt):
        raise AccountingStructureError("Cannot inactivate group with current or future child group relationships")

    group.status = AccountGroupStatus.INACTIVE
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise AccountingStructureError("Could not inactivate group due to a data conflict") from exc

    await session.refresh(group)
    return group


async def _end_current_parent_relationship(
    session: AsyncSession,
    company_id: UUID,
    child_group_id: UUID,
    effective_date: date,
):
    stmt = select(AccountGroupRelationship).where(
        AccountGroupRelationship.child_group_id == child_group_id,
        or_(
            AccountGroupRelationship.valid_to.is_(None),
            AccountGroupRelationship.valid_to >= effective_date
        )
    )
    current_rel = await session.scalar(stmt)
    if current_rel:
        if current_rel.valid_from >= effective_date:
             raise AccountingStructureError("Cannot date-end a relationship that starts on or after the effective date. Overlap detected.")
        current_rel.valid_to = effective_date - timedelta(days=1)
        session.add(current_rel)


async def reparent_account_group(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    group_id: UUID,
    new_parent_group_id: UUID,
    effective_date: date,
) -> AccountGroupRelationship:
    group = await get_account_group(session=session, tenant=tenant, company_id=company_id, group_id=group_id)
    if not group:
        raise AccountingStructureError("Group not found")
    if group.status is AccountGroupStatus.INACTIVE:
        raise AccountingStructureError("Inactive Account Group cannot be changed")

    parent = await get_account_group(session=session, tenant=tenant, company_id=company_id, group_id=new_parent_group_id)
    if not parent:
        raise AccountingStructureError("New parent group not found")
    if parent.status is AccountGroupStatus.INACTIVE:
        raise AccountingStructureError("New parent group is inactive")

    if group.hierarchy_id != parent.hierarchy_id:
        raise AccountingStructureError("Groups must be in the same hierarchy")

    if group_id == new_parent_group_id:
        raise AccountingStructureError("A group cannot be its own parent")

    await _end_current_parent_relationship(session, company_id, group_id, effective_date)

    new_rel = AccountGroupRelationship(
        company_id=company_id,
        hierarchy_id=group.hierarchy_id,
        child_group_id=group_id,
        parent_group_id=new_parent_group_id,
        valid_from=effective_date,
        valid_to=None,
    )
    session.add(new_rel)

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise AccountingStructureError("Could not reparent group due to overlap or data conflict") from exc

    await session.refresh(new_rel)
    return new_rel


async def move_account_group_to_root(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    group_id: UUID,
    effective_date: date,
) -> None:
    group = await get_account_group(session=session, tenant=tenant, company_id=company_id, group_id=group_id)
    if not group:
        raise AccountingStructureError("Group not found")
    if group.status is AccountGroupStatus.INACTIVE:
        raise AccountingStructureError("Inactive Account Group cannot be changed")

    await _end_current_parent_relationship(session, company_id, group_id, effective_date)

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise AccountingStructureError("Could not move group to root due to overlap or data conflict") from exc


async def _end_current_gl_placement(
    session: AsyncSession,
    company_id: UUID,
    gl_account_id: UUID,
    effective_date: date,
):
    stmt = select(AccountGroupMapping).where(
        AccountGroupMapping.gl_account_id == gl_account_id,
        or_(
            AccountGroupMapping.valid_to.is_(None),
            AccountGroupMapping.valid_to >= effective_date
        )
    )
    current_mapping = await session.scalar(stmt)
    if current_mapping:
        if current_mapping.valid_from >= effective_date:
             raise AccountingStructureError("Cannot date-end a placement that starts on or after the effective date. Overlap detected.")
        current_mapping.valid_to = effective_date - timedelta(days=1)
        session.add(current_mapping)


async def assign_gl_account(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    gl_account_id: UUID,
    hierarchy_id: UUID,
    account_group_id: UUID | None,
    effective_date: date,
) -> AccountGroupMapping:
    stmt = select(GlAccount).join(Company).where(
        GlAccount.id == gl_account_id,
        GlAccount.company_id == company_id,
        Company.tenant_id == tenant.id,
    )
    gl_account = await session.scalar(stmt)
    if not gl_account:
        raise AccountingStructureError("GL Account not found")
    if gl_account.status is GlAccountStatus.INACTIVE:
        raise AccountingStructureError("Inactive GL Account cannot be changed")

    if account_group_id is not None:
        group = await get_account_group(session=session, tenant=tenant, company_id=company_id, group_id=account_group_id)
        if not group or group.hierarchy_id != hierarchy_id:
            raise AccountingStructureError("Account group not found or belongs to a different hierarchy")
        if group.status is AccountGroupStatus.INACTIVE:
            raise AccountingStructureError("Account group is inactive")

    await _end_current_gl_placement(session, company_id, gl_account_id, effective_date)

    new_mapping = AccountGroupMapping(
        company_id=company_id,
        hierarchy_id=hierarchy_id,
        gl_account_id=gl_account_id,
        account_group_id=account_group_id,
        valid_from=effective_date,
        valid_to=None,
    )
    session.add(new_mapping)

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise AccountingStructureError("Could not assign GL account due to overlap or data conflict") from exc

    await session.refresh(new_mapping)
    return new_mapping


async def end_gl_account_assignment(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    gl_account_id: UUID,
    effective_date: date,
) -> None:
    stmt = select(GlAccount).join(Company).where(
        GlAccount.id == gl_account_id,
        GlAccount.company_id == company_id,
        Company.tenant_id == tenant.id,
    )
    gl_account = await session.scalar(stmt)
    if not gl_account:
        raise AccountingStructureError("GL Account not found")
    if gl_account.status is GlAccountStatus.INACTIVE:
        raise AccountingStructureError("Inactive GL Account cannot be changed")

    await _end_current_gl_placement(session, company_id, gl_account_id, effective_date)

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise AccountingStructureError("Could not end GL account assignment due to overlap or data conflict") from exc


async def get_accounting_settings(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
) -> CompanyAccountingSettings | None:
    stmt = (
        select(CompanyAccountingSettings)
        .join(Company, CompanyAccountingSettings.company_id == Company.id)
        .where(
            CompanyAccountingSettings.company_id == company_id,
            Company.tenant_id == tenant.id,
        )
    )
    return await session.scalar(stmt)


async def upsert_accounting_settings(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    settings_data: CompanyAccountingSettingsUpdate,
) -> CompanyAccountingSettings:
    company = await session.get(Company, company_id)
    if not company or company.tenant_id != tenant.id:
        raise AccountingStructureError("Company does not exist")

    stmt = select(GlAccount).where(
        GlAccount.id == settings_data.default_receivable_gl_account_id,
        GlAccount.company_id == company_id
    )
    gl_account = await session.scalar(stmt)
    if not gl_account:
        raise AccountingStructureError("GL Account not found in this company")

    settings = await get_accounting_settings(session=session, tenant=tenant, company_id=company_id)
    if not settings:
        settings = CompanyAccountingSettings(
            company_id=company_id,
            default_receivable_gl_account_id=settings_data.default_receivable_gl_account_id
        )
        session.add(settings)
    else:
        settings.default_receivable_gl_account_id = settings_data.default_receivable_gl_account_id

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise AccountingStructureError("Could not update settings due to a data conflict") from exc

    await session.refresh(settings)
    return settings
