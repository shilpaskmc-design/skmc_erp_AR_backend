from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.ar.fx.model import FXPolicyPurpose
from skmc_erp.ar.fx.schema import FXPolicyPut, FXPolicyResponse
from skmc_erp.ar.fx.service import FXPolicyInputError, get_fx_policy, list_fx_policies, put_fx_policy
from skmc_erp.core.tenant.dependencies import get_temporary_tenant_context
from skmc_erp.core.tenant.model import Tenant
from skmc_erp.database import get_db_session

router = APIRouter(prefix="/companies/{company_id}/fx-policies", tags=["fx_policies"])


@router.get("", response_model=list[FXPolicyResponse])
async def list_fx_policies_endpoint(company_id: UUID, tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)], session: Annotated[AsyncSession, Depends(get_db_session)]) -> list[FXPolicyResponse]:
    try:
        policies = await list_fx_policies(session=session, tenant=tenant, company_id=company_id)
    except FXPolicyInputError:
        return []
    return [FXPolicyResponse.model_validate(item) for item in policies]


@router.get("/{purpose}", response_model=FXPolicyResponse)
async def get_fx_policy_endpoint(company_id: UUID, purpose: FXPolicyPurpose, tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)], session: Annotated[AsyncSession, Depends(get_db_session)]) -> FXPolicyResponse:
    try:
        policy = await get_fx_policy(session=session, tenant=tenant, company_id=company_id, purpose=purpose)
    except FXPolicyInputError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if policy is None:
        raise HTTPException(status_code=404, detail="FX Policy not found")
    return FXPolicyResponse.model_validate(policy)


@router.put("/{purpose}", response_model=FXPolicyResponse)
async def put_fx_policy_endpoint(company_id: UUID, purpose: FXPolicyPurpose, policy_data: FXPolicyPut, tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)], session: Annotated[AsyncSession, Depends(get_db_session)]) -> FXPolicyResponse:
    try:
        policy = await put_fx_policy(session=session, tenant=tenant, company_id=company_id, purpose=purpose, policy_data=policy_data)
    except FXPolicyInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return FXPolicyResponse.model_validate(policy)
