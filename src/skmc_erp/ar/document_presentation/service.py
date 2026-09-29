from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.ar.document_presentation.model import (
    CompanyDocumentBranding,
    CompanyDocumentTemplate,
    DocumentPresentationStatus,
)
from skmc_erp.ar.document_presentation.registry import (
    is_supported_billing_template,
)
from skmc_erp.ar.document_presentation.schema import (
    CompanyDocumentBrandingCreate,
    CompanyDocumentTemplateSelection,
)
from skmc_erp.core.company.model import Company, CompanyStatus
from skmc_erp.core.file_storage.model import StoredFile
from skmc_erp.core.tenant.model import Tenant


class DocumentPresentationNotFoundError(Exception):
    """The Company or requested current configuration is not visible."""


class DocumentPresentationInputError(Exception):
    """A supplied template or branding reference is invalid."""


class DocumentPresentationStateConflictError(Exception):
    """The requested presentation change conflicts with current state."""


async def _get_company(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    for_update: bool = False,
) -> Company | None:
    query = select(Company).where(
        Company.id == company_id,
        Company.tenant_id == tenant.id,
    )
    if for_update:
        query = query.with_for_update()
    return await session.scalar(query)


async def _get_current_selection(
    session: AsyncSession,
    company_id: UUID,
) -> CompanyDocumentTemplate | None:
    return await session.scalar(
        select(CompanyDocumentTemplate).where(
            CompanyDocumentTemplate.company_id == company_id,
            CompanyDocumentTemplate.status
            == DocumentPresentationStatus.ACTIVE,
        )
    )


async def _get_current_branding(
    session: AsyncSession,
    company_id: UUID,
) -> CompanyDocumentBranding | None:
    return await session.scalar(
        select(CompanyDocumentBranding).where(
            CompanyDocumentBranding.company_id == company_id,
            CompanyDocumentBranding.status
            == DocumentPresentationStatus.ACTIVE,
        )
    )


async def _next_selection_version(
    session: AsyncSession,
    company_id: UUID,
) -> int:
    latest = await session.scalar(
        select(func.max(CompanyDocumentTemplate.version_no)).where(
            CompanyDocumentTemplate.company_id == company_id
        )
    )
    return (latest or 0) + 1


async def _commit(session: AsyncSession, message: str) -> None:
    try:
        await session.flush()
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise DocumentPresentationStateConflictError(message) from exc


async def list_document_templates(
    *, session: AsyncSession, tenant: Tenant, company_id: UUID
) -> Sequence[CompanyDocumentTemplate]:
    company = await _get_company(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    if company is None:
        return []
    result = await session.scalars(
        select(CompanyDocumentTemplate)
        .where(CompanyDocumentTemplate.company_id == company_id)
        .order_by(
            CompanyDocumentTemplate.version_no,
            CompanyDocumentTemplate.id,
        )
    )
    return result.all()


async def get_current_document_presentation(
    *, session: AsyncSession, tenant: Tenant, company_id: UUID
) -> tuple[CompanyDocumentTemplate, CompanyDocumentBranding | None] | None:
    company = await _get_company(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    if company is None:
        return None
    selection = await _get_current_selection(session, company_id)
    if selection is None:
        return None
    branding = None
    if selection.branding_id is not None:
        branding = await session.scalar(
            select(CompanyDocumentBranding).where(
                CompanyDocumentBranding.id == selection.branding_id,
                CompanyDocumentBranding.company_id == company_id,
            )
        )
    return selection, branding


async def select_company_billing_template(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    selection_data: CompanyDocumentTemplateSelection,
) -> tuple[CompanyDocumentTemplate, CompanyDocumentBranding | None]:
    company = await _get_company(
        session=session,
        tenant=tenant,
        company_id=company_id,
        for_update=True,
    )
    if company is None:
        raise DocumentPresentationNotFoundError("Company not found")
    if company.status is CompanyStatus.INACTIVE:
        raise DocumentPresentationStateConflictError("Company is inactive")
    if not is_supported_billing_template(selection_data.template_key):
        raise DocumentPresentationInputError(
            "Unsupported billing document template_key"
        )

    current = await _get_current_selection(session, company_id)
    branding = await _get_current_branding(session, company_id)
    branding_id = branding.id if branding is not None else None
    if (
        current is not None
        and current.template_key == selection_data.template_key
        and current.branding_id == branding_id
    ):
        return current, branding

    now = datetime.now(UTC)
    if current is not None:
        current.status = DocumentPresentationStatus.INACTIVE
        current.updated_at = now
    selection = CompanyDocumentTemplate(
        company_id=company_id,
        document_type=None,
        branding_id=branding_id,
        template_key=selection_data.template_key,
        version_no=await _next_selection_version(session, company_id),
        show_logo=None,
        show_bank_details=None,
        show_signature=None,
        show_hsn_sac=None,
        show_customer_reference=None,
        status=DocumentPresentationStatus.ACTIVE,
    )
    session.add(selection)
    await _commit(
        session,
        "Billing document template selection could not be saved",
    )
    await session.refresh(selection)
    if branding is not None:
        await session.refresh(branding)
    return selection, branding


async def list_company_document_branding(
    *, session: AsyncSession, tenant: Tenant, company_id: UUID
) -> Sequence[CompanyDocumentBranding]:
    company = await _get_company(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    if company is None:
        return []
    result = await session.scalars(
        select(CompanyDocumentBranding)
        .where(CompanyDocumentBranding.company_id == company_id)
        .order_by(
            CompanyDocumentBranding.created_at,
            CompanyDocumentBranding.id,
        )
    )
    return result.all()


async def get_current_company_document_branding(
    *, session: AsyncSession, tenant: Tenant, company_id: UUID
) -> CompanyDocumentBranding | None:
    company = await _get_company(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    if company is None:
        return None
    return await _get_current_branding(session, company_id)


async def _validate_stored_file_ownership(
    *,
    session: AsyncSession,
    company_id: UUID,
    branding_data: CompanyDocumentBrandingCreate,
) -> None:
    file_ids = {
        file_id
        for file_id in (
            branding_data.logo_file_id,
            branding_data.signature_file_id,
            branding_data.stamp_file_id,
        )
        if file_id is not None
    }
    if not file_ids:
        return
    owned_ids = set(
        (
            await session.scalars(
                select(StoredFile.id).where(
                    StoredFile.company_id == company_id,
                    StoredFile.id.in_(file_ids),
                )
            )
        ).all()
    )
    if owned_ids != file_ids:
        raise DocumentPresentationInputError(
            "Branding files must exist and belong to the Company"
        )


async def create_company_document_branding(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    branding_data: CompanyDocumentBrandingCreate,
) -> CompanyDocumentBranding:
    company = await _get_company(
        session=session,
        tenant=tenant,
        company_id=company_id,
        for_update=True,
    )
    if company is None:
        raise DocumentPresentationNotFoundError("Company not found")
    if company.status is CompanyStatus.INACTIVE:
        raise DocumentPresentationStateConflictError("Company is inactive")
    await _validate_stored_file_ownership(
        session=session,
        company_id=company_id,
        branding_data=branding_data,
    )

    current_branding = await _get_current_branding(session, company_id)
    values = branding_data.model_dump()
    if current_branding is not None and all(
        getattr(current_branding, field) == value
        for field, value in values.items()
    ):
        return current_branding

    now = datetime.now(UTC)
    if current_branding is not None:
        current_branding.status = DocumentPresentationStatus.INACTIVE
        current_branding.updated_at = now
    branding = CompanyDocumentBranding(
        company_id=company_id,
        **values,
        status=DocumentPresentationStatus.ACTIVE,
    )
    session.add(branding)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise DocumentPresentationStateConflictError(
            "Company document branding could not be saved"
        ) from exc

    current_selection = await _get_current_selection(session, company_id)
    if current_selection is not None:
        current_selection.status = DocumentPresentationStatus.INACTIVE
        current_selection.updated_at = now
        session.add(
            CompanyDocumentTemplate(
                company_id=company_id,
                document_type=None,
                branding_id=branding.id,
                template_key=current_selection.template_key,
                version_no=await _next_selection_version(session, company_id),
                show_logo=None,
                show_bank_details=None,
                show_signature=None,
                show_hsn_sac=None,
                show_customer_reference=None,
                status=DocumentPresentationStatus.ACTIVE,
            )
        )

    await _commit(session, "Company document branding could not be saved")
    await session.refresh(branding)
    return branding
