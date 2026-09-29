from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.ar.numbering.model import (
    DocumentSequence,
    DocumentSequenceStatus,
)
from skmc_erp.ar.numbering.schema import DocumentSequenceCreate
from skmc_erp.core.company.model import Company, CompanyStatus
from skmc_erp.core.financial_year.model import FinancialYear
from skmc_erp.core.tenant.model import Tenant


class DocumentNumberingNotFoundError(Exception):
    """The requested Company is not visible within the Tenant."""


class DocumentNumberingInputError(Exception):
    """A supplied numbering relationship is invalid."""


class DocumentNumberingStateConflictError(Exception):
    """The requested numbering mutation conflicts with current state."""


async def _company(
    *, session: AsyncSession, tenant: Tenant, company_id: UUID, mutable: bool
) -> Company:
    company = await session.scalar(
        select(Company).where(
            Company.id == company_id,
            Company.tenant_id == tenant.id,
        )
    )
    if company is None:
        raise DocumentNumberingNotFoundError("Company not found")
    if mutable and company.status is CompanyStatus.INACTIVE:
        raise DocumentNumberingStateConflictError("Company is inactive")
    return company


async def create_document_sequence(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    sequence_data: DocumentSequenceCreate,
) -> DocumentSequence:
    company = await _company(
        session=session,
        tenant=tenant,
        company_id=company_id,
        mutable=True,
    )
    financial_year = await session.scalar(
        select(FinancialYear).where(
            FinancialYear.id == sequence_data.financial_year_id,
            FinancialYear.company_id == company.id,
        )
    )
    if financial_year is None:
        raise DocumentNumberingInputError(
            "Financial Year does not belong to the Company"
        )
    if sequence_data.next_number < sequence_data.start_number:
        raise DocumentNumberingInputError(
            "next_number must be greater than or equal to start_number"
        )

    now = datetime.now(UTC)
    sequence = DocumentSequence(
        id=uuid4(),
        company_id=company.id,
        financial_year_id=financial_year.id,
        document_type=sequence_data.document_type,
        series_name=sequence_data.series_name,
        format=sequence_data.format,
        prefix=sequence_data.prefix,
        start_number=sequence_data.start_number,
        next_number=sequence_data.next_number,
        padding=sequence_data.padding,
        priority=sequence_data.priority,
        status=DocumentSequenceStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    session.add(sequence)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise DocumentNumberingStateConflictError(
            "Document Sequence conflicts with existing configuration"
        ) from exc
    await session.refresh(sequence)
    return sequence


async def list_document_sequences(
    *, session: AsyncSession, tenant: Tenant, company_id: UUID
) -> Sequence[DocumentSequence]:
    await _company(
        session=session,
        tenant=tenant,
        company_id=company_id,
        mutable=False,
    )
    rows = await session.scalars(
        select(DocumentSequence)
        .where(DocumentSequence.company_id == company_id)
        .order_by(
            DocumentSequence.financial_year_id,
            DocumentSequence.document_type,
            DocumentSequence.series_name,
        )
    )
    return rows.all()


async def get_document_sequence(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    sequence_id: UUID,
) -> DocumentSequence | None:
    return await session.scalar(
        select(DocumentSequence)
        .join(Company, DocumentSequence.company_id == Company.id)
        .where(
            DocumentSequence.id == sequence_id,
            DocumentSequence.company_id == company_id,
            Company.tenant_id == tenant.id,
        )
    )


async def inactivate_document_sequence(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    sequence_id: UUID,
) -> DocumentSequence | None:
    await _company(
        session=session,
        tenant=tenant,
        company_id=company_id,
        mutable=True,
    )
    sequence = await get_document_sequence(
        session=session,
        tenant=tenant,
        company_id=company_id,
        sequence_id=sequence_id,
    )
    if sequence is None:
        return None
    if sequence.status is DocumentSequenceStatus.INACTIVE:
        return sequence
    sequence.status = DocumentSequenceStatus.INACTIVE
    sequence.updated_at = datetime.now(UTC)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise DocumentNumberingStateConflictError(
            "Document Sequence could not be inactivated"
        ) from exc
    await session.refresh(sequence)
    return sequence
