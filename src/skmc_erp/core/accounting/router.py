from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.core.accounting.schema import (
    GlAccountCreate,
    GlAccountResponse,
    GlAccountUpdate,
)
from skmc_erp.core.accounting.service import (
    GlAccountInputError,
    GlAccountStateConflictError,
    create_gl_account,
    get_gl_account,
    inactivate_gl_account,
    list_gl_accounts,
    update_gl_account,
)
from skmc_erp.core.tenant.dependencies import get_temporary_tenant_context
from skmc_erp.core.tenant.model import Tenant
from skmc_erp.database import get_db_session

from datetime import date
from skmc_erp.core.accounting.schema import (
    AccountGroupCreate,
    AccountGroupRelationshipResponse,
    AccountGroupResponse,
    AccountGroupUpdate,
    AccountHierarchyCreate,
    AccountHierarchyResponse,
    CompanyAccountingSettingsResponse,
    CompanyAccountingSettingsUpdate,
    GlAccountEndAssignmentRequest,
    GlAccountGroupAssignmentRequest,
    GlAccountGroupMappingResponse,
    GlAccountRootAssignmentRequest,
    MoveGroupToRootRequest,
    ReparentGroupRequest,
)
from skmc_erp.core.accounting.service import (
    AccountingStructureError,
    assign_gl_account,
    create_account_group,
    create_primary_hierarchy,
    end_gl_account_assignment,
    get_account_group,
    get_accounting_settings,
    get_primary_hierarchy,
    inactivate_account_group,
    move_account_group_to_root,
    reparent_account_group,
    update_account_group,
    upsert_accounting_settings,
)

router = APIRouter(prefix="/companies/{company_id}/gl-accounts", tags=["gl_accounts"])


@router.post("", response_model=GlAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_gl_account_endpoint(
    company_id: UUID,
    gl_account_data: GlAccountCreate,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GlAccountResponse:
    try:
        gl_account = await create_gl_account(
            session=session,
            tenant=tenant,
            company_id=company_id,
            gl_account_data=gl_account_data,
        )
    except GlAccountInputError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except GlAccountStateConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return GlAccountResponse.model_validate(gl_account)


@router.get("", response_model=list[GlAccountResponse])
async def list_gl_accounts_endpoint(
    company_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[GlAccountResponse]:
    gl_accounts = await list_gl_accounts(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    # Following the pattern of hiding cross-tenant companies via returning empty list or letting get_gl_account return 404
    if not gl_accounts:
        return []

    return [GlAccountResponse.model_validate(acc) for acc in gl_accounts]


@router.get("/{gl_account_id}", response_model=GlAccountResponse)
async def get_gl_account_endpoint(
    company_id: UUID,
    gl_account_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GlAccountResponse:
    gl_account = await get_gl_account(
        session=session,
        tenant=tenant,
        company_id=company_id,
        gl_account_id=gl_account_id,
    )
    if gl_account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GL Account not found",
        )
    return GlAccountResponse.model_validate(gl_account)


@router.patch("/{gl_account_id}", response_model=GlAccountResponse)
async def update_gl_account_endpoint(
    company_id: UUID,
    gl_account_id: UUID,
    update_data: GlAccountUpdate,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GlAccountResponse:
    try:
        gl_account = await update_gl_account(
            session=session,
            tenant=tenant,
            company_id=company_id,
            gl_account_id=gl_account_id,
            update_data=update_data,
        )
    except GlAccountInputError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except GlAccountStateConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    if gl_account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GL Account not found",
        )
    return GlAccountResponse.model_validate(gl_account)


@router.post("/{gl_account_id}/inactivate", response_model=GlAccountResponse)
async def inactivate_gl_account_endpoint(
    company_id: UUID,
    gl_account_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GlAccountResponse:
    try:
        gl_account = await inactivate_gl_account(
            session=session,
            tenant=tenant,
            company_id=company_id,
            gl_account_id=gl_account_id,
        )
    except GlAccountStateConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    if gl_account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GL Account not found",
        )
    return GlAccountResponse.model_validate(gl_account)


structure_router = APIRouter(prefix="/companies/{company_id}", tags=["accounting_structure"])


@structure_router.post("/accounting/hierarchy", response_model=AccountHierarchyResponse, status_code=status.HTTP_201_CREATED)
async def create_primary_hierarchy_endpoint(
    company_id: UUID,
    hierarchy_data: AccountHierarchyCreate,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AccountHierarchyResponse:
    try:
        hierarchy = await create_primary_hierarchy(
            session=session,
            tenant=tenant,
            company_id=company_id,
            hierarchy_data=hierarchy_data,
        )
    except AccountingStructureError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return AccountHierarchyResponse.model_validate(hierarchy)


@structure_router.get("/accounting/hierarchy", response_model=AccountHierarchyResponse)
async def get_primary_hierarchy_endpoint(
    company_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AccountHierarchyResponse:
    hierarchy = await get_primary_hierarchy(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    if hierarchy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Primary ACCOUNTING hierarchy not found",
        )
    return AccountHierarchyResponse.model_validate(hierarchy)


@structure_router.post("/accounting/hierarchy/{hierarchy_id}/account-groups", response_model=AccountGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_account_group_endpoint(
    company_id: UUID,
    hierarchy_id: UUID,
    group_data: AccountGroupCreate,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AccountGroupResponse:
    try:
        group = await create_account_group(
            session=session,
            tenant=tenant,
            company_id=company_id,
            hierarchy_id=hierarchy_id,
            group_data=group_data,
        )
    except AccountingStructureError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return AccountGroupResponse.model_validate(group)


@structure_router.get("/account-groups/{group_id}", response_model=AccountGroupResponse)
async def get_account_group_endpoint(
    company_id: UUID,
    group_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AccountGroupResponse:
    group = await get_account_group(
        session=session,
        tenant=tenant,
        company_id=company_id,
        group_id=group_id,
    )
    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account group not found",
        )
    return AccountGroupResponse.model_validate(group)


@structure_router.patch("/account-groups/{group_id}", response_model=AccountGroupResponse)
async def update_account_group_endpoint(
    company_id: UUID,
    group_id: UUID,
    update_data: AccountGroupUpdate,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AccountGroupResponse:
    try:
        group = await update_account_group(
            session=session,
            tenant=tenant,
            company_id=company_id,
            group_id=group_id,
            update_data=update_data,
        )
    except AccountingStructureError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account group not found",
        )
    return AccountGroupResponse.model_validate(group)


@structure_router.post("/account-groups/{group_id}/inactivate", response_model=AccountGroupResponse)
async def inactivate_account_group_endpoint(
    company_id: UUID,
    group_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AccountGroupResponse:
    try:
        group = await inactivate_account_group(
            session=session,
            tenant=tenant,
            company_id=company_id,
            group_id=group_id,
        )
    except AccountingStructureError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account group not found",
        )
    return AccountGroupResponse.model_validate(group)


@structure_router.post("/account-groups/{group_id}/reparent", response_model=AccountGroupRelationshipResponse)
async def reparent_account_group_endpoint(
    company_id: UUID,
    group_id: UUID,
    request: ReparentGroupRequest,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AccountGroupRelationshipResponse:
    try:
        rel = await reparent_account_group(
            session=session,
            tenant=tenant,
            company_id=company_id,
            group_id=group_id,
            new_parent_group_id=request.new_parent_group_id,
            effective_date=request.effective_date,
        )
    except AccountingStructureError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return AccountGroupRelationshipResponse.model_validate(rel)


@structure_router.post("/account-groups/{group_id}/move-to-root")
async def move_account_group_to_root_endpoint(
    company_id: UUID,
    group_id: UUID,
    request: MoveGroupToRootRequest,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    try:
        await move_account_group_to_root(
            session=session,
            tenant=tenant,
            company_id=company_id,
            group_id=group_id,
            effective_date=request.effective_date,
        )
    except AccountingStructureError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return {"detail": "Moved to root"}


@structure_router.post("/gl-accounts/{gl_account_id}/group-assignment", response_model=GlAccountGroupMappingResponse)
async def assign_gl_account_to_group_endpoint(
    company_id: UUID,
    gl_account_id: UUID,
    hierarchy_id: UUID,
    request: GlAccountGroupAssignmentRequest,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GlAccountGroupMappingResponse:
    try:
        mapping = await assign_gl_account(
            session=session,
            tenant=tenant,
            company_id=company_id,
            gl_account_id=gl_account_id,
            hierarchy_id=hierarchy_id,
            account_group_id=request.account_group_id,
            effective_date=request.effective_date,
        )
    except AccountingStructureError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return GlAccountGroupMappingResponse.model_validate(mapping)


@structure_router.post("/gl-accounts/{gl_account_id}/root-assignment", response_model=GlAccountGroupMappingResponse)
async def assign_gl_account_to_root_endpoint(
    company_id: UUID,
    gl_account_id: UUID,
    hierarchy_id: UUID,
    request: GlAccountRootAssignmentRequest,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GlAccountGroupMappingResponse:
    try:
        mapping = await assign_gl_account(
            session=session,
            tenant=tenant,
            company_id=company_id,
            gl_account_id=gl_account_id,
            hierarchy_id=hierarchy_id,
            account_group_id=None,
            effective_date=request.effective_date,
        )
    except AccountingStructureError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return GlAccountGroupMappingResponse.model_validate(mapping)


@structure_router.post("/gl-accounts/{gl_account_id}/end-assignment")
async def end_gl_account_assignment_endpoint(
    company_id: UUID,
    gl_account_id: UUID,
    request: GlAccountEndAssignmentRequest,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    try:
        await end_gl_account_assignment(
            session=session,
            tenant=tenant,
            company_id=company_id,
            gl_account_id=gl_account_id,
            effective_date=request.effective_date,
        )
    except AccountingStructureError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return {"detail": "Assignment ended"}


@structure_router.get("/accounting/settings", response_model=CompanyAccountingSettingsResponse)
async def get_accounting_settings_endpoint(
    company_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyAccountingSettingsResponse:
    settings = await get_accounting_settings(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    if settings is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Accounting settings not found",
        )
    return CompanyAccountingSettingsResponse.model_validate(settings)


@structure_router.patch("/accounting/settings", response_model=CompanyAccountingSettingsResponse)
async def upsert_accounting_settings_endpoint(
    company_id: UUID,
    settings_data: CompanyAccountingSettingsUpdate,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyAccountingSettingsResponse:
    try:
        settings = await upsert_accounting_settings(
            session=session,
            tenant=tenant,
            company_id=company_id,
            settings_data=settings_data,
        )
    except AccountingStructureError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return CompanyAccountingSettingsResponse.model_validate(settings)
