from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.ar.reminder.model import ReminderPolicy, ReminderScheduleRule, ReminderScheduleRuleStatus
from skmc_erp.ar.reminder.schema import ReminderPolicyPut, ReminderScheduleRuleCreate
from skmc_erp.core.company.model import Company
from skmc_erp.core.tenant.model import Tenant


class ReminderInputError(Exception):
    pass


class ReminderStateConflictError(Exception):
    pass


async def _company(session: AsyncSession, tenant: Tenant, company_id: UUID) -> Company:
    company = await session.get(Company, company_id)
    if company is None or company.tenant_id != tenant.id:
        raise ReminderInputError("Company does not exist")
    return company


async def get_reminder_policy(*, session: AsyncSession, tenant: Tenant, company_id: UUID) -> ReminderPolicy | None:
    await _company(session, tenant, company_id)
    return await session.scalar(select(ReminderPolicy).where(ReminderPolicy.company_id == company_id))


async def put_reminder_policy(*, session: AsyncSession, tenant: Tenant, company_id: UUID, policy_data: ReminderPolicyPut) -> ReminderPolicy:
    policy = await get_reminder_policy(session=session, tenant=tenant, company_id=company_id)
    if policy is None:
        policy = ReminderPolicy(company_id=company_id)
        session.add(policy)
    for field, value in policy_data.model_dump().items():
        setattr(policy, field, value)
    await session.commit()
    await session.refresh(policy)
    return policy


async def list_schedule_rules(*, session: AsyncSession, tenant: Tenant, company_id: UUID) -> Sequence[ReminderScheduleRule]:
    policy = await get_reminder_policy(session=session, tenant=tenant, company_id=company_id)
    if policy is None:
        return []
    result = await session.scalars(select(ReminderScheduleRule).where(ReminderScheduleRule.reminder_policy_id == policy.id).order_by(ReminderScheduleRule.offset_days))
    return result.all()


async def create_schedule_rule(*, session: AsyncSession, tenant: Tenant, company_id: UUID, rule_data: ReminderScheduleRuleCreate) -> ReminderScheduleRule:
    policy = await get_reminder_policy(session=session, tenant=tenant, company_id=company_id)
    if policy is None:
        raise ReminderInputError("Reminder Policy does not exist")
    rule = ReminderScheduleRule(reminder_policy_id=policy.id, **rule_data.model_dump(), status=ReminderScheduleRuleStatus.ACTIVE)
    session.add(rule)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ReminderStateConflictError("Reminder Schedule Rule conflicts with an existing offset") from exc
    await session.refresh(rule)
    return rule


async def inactivate_schedule_rule(*, session: AsyncSession, tenant: Tenant, company_id: UUID, rule_id: UUID) -> ReminderScheduleRule | None:
    policy = await get_reminder_policy(session=session, tenant=tenant, company_id=company_id)
    if policy is None:
        return None
    rule = await session.scalar(select(ReminderScheduleRule).where(ReminderScheduleRule.id == rule_id, ReminderScheduleRule.reminder_policy_id == policy.id))
    if rule is None:
        return None
    rule.status = ReminderScheduleRuleStatus.INACTIVE
    await session.commit()
    await session.refresh(rule)
    return rule
