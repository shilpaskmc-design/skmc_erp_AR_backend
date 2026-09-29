from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.ar.reminder.schema import ReminderPolicyPut, ReminderPolicyResponse, ReminderScheduleRuleCreate, ReminderScheduleRuleResponse
from skmc_erp.ar.reminder.service import ReminderInputError, ReminderStateConflictError, create_schedule_rule, get_reminder_policy, inactivate_schedule_rule, list_schedule_rules, put_reminder_policy
from skmc_erp.core.tenant.dependencies import get_temporary_tenant_context
from skmc_erp.core.tenant.model import Tenant
from skmc_erp.database import get_db_session

router = APIRouter(prefix="/companies/{company_id}/reminders", tags=["reminders"])


@router.get("/policy", response_model=ReminderPolicyResponse)
async def get_policy_endpoint(company_id: UUID, tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)], session: Annotated[AsyncSession, Depends(get_db_session)]) -> ReminderPolicyResponse:
    try:
        policy = await get_reminder_policy(session=session, tenant=tenant, company_id=company_id)
    except ReminderInputError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if policy is None:
        raise HTTPException(status_code=404, detail="Reminder Policy not found")
    return ReminderPolicyResponse.model_validate(policy)


@router.put("/policy", response_model=ReminderPolicyResponse)
async def put_policy_endpoint(company_id: UUID, policy_data: ReminderPolicyPut, tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)], session: Annotated[AsyncSession, Depends(get_db_session)]) -> ReminderPolicyResponse:
    try:
        policy = await put_reminder_policy(session=session, tenant=tenant, company_id=company_id, policy_data=policy_data)
    except ReminderInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ReminderPolicyResponse.model_validate(policy)


@router.get("/schedule-rules", response_model=list[ReminderScheduleRuleResponse])
async def list_rules_endpoint(company_id: UUID, tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)], session: Annotated[AsyncSession, Depends(get_db_session)]) -> list[ReminderScheduleRuleResponse]:
    try:
        rules = await list_schedule_rules(session=session, tenant=tenant, company_id=company_id)
    except ReminderInputError:
        return []
    return [ReminderScheduleRuleResponse.model_validate(item) for item in rules]


@router.post("/schedule-rules", response_model=ReminderScheduleRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule_endpoint(company_id: UUID, rule_data: ReminderScheduleRuleCreate, tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)], session: Annotated[AsyncSession, Depends(get_db_session)]) -> ReminderScheduleRuleResponse:
    try:
        rule = await create_schedule_rule(session=session, tenant=tenant, company_id=company_id, rule_data=rule_data)
    except ReminderInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ReminderStateConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ReminderScheduleRuleResponse.model_validate(rule)


@router.post("/schedule-rules/{rule_id}/inactivate", response_model=ReminderScheduleRuleResponse)
async def inactivate_rule_endpoint(company_id: UUID, rule_id: UUID, tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)], session: Annotated[AsyncSession, Depends(get_db_session)]) -> ReminderScheduleRuleResponse:
    try:
        rule = await inactivate_schedule_rule(session=session, tenant=tenant, company_id=company_id, rule_id=rule_id)
    except ReminderInputError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if rule is None:
        raise HTTPException(status_code=404, detail="Reminder Schedule Rule not found")
    return ReminderScheduleRuleResponse.model_validate(rule)
