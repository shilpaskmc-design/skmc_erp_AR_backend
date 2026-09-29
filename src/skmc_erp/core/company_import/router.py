from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.config import (
    DEFAULT_COMPANY_IMPORT_SIGNING_KEY,
    Settings,
    get_settings,
)
from skmc_erp.core.company.service import (
    CompanyInputError,
    CompanyStateConflictError,
    get_company,
)
from skmc_erp.core.company_import.schema import (
    CompanyImportApplyRequest,
    CompanyImportApplyResponse,
    CompanyImportIssue,
    CompanyImportPreviewResponse,
)
from skmc_erp.core.company_import.service import (
    CompanyImportValidationError,
    apply_company_import,
    preview_company_import,
)
from skmc_erp.core.company_import.token import PreviewTokenError
from skmc_erp.core.company_import.workbook import (
    MAX_FILE_BYTES,
    CompanyWorkbookError,
)
from skmc_erp.core.company_gst_registration.service import (
    CompanyGSTRegistrationInputError,
    CompanyGSTRegistrationNotFoundError,
    CompanyGSTRegistrationStateConflictError,
)
from skmc_erp.core.company_location.service import (
    CompanyLocationInputError,
    CompanyLocationNotFoundError,
    CompanyLocationStateConflictError,
)
from skmc_erp.core.financial_year.service import (
    FinancialYearInputError,
    FinancialYearNotFoundError,
    FinancialYearStateConflictError,
)
from skmc_erp.core.tenant.dependencies import get_temporary_tenant_context
from skmc_erp.core.tenant.model import Tenant
from skmc_erp.database import get_db_session


router = APIRouter(prefix="/companies", tags=["company-configuration-import"])
ALLOWED_CONTENT_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/octet-stream",
}


def _signing_key(settings: Settings) -> str:
    key = settings.company_import_signing_key.get_secret_value()
    if len(key.encode("utf-8")) < 32:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Company import signing key is not configured securely",
        )
    if (
        settings.environment.strip().casefold() == "production"
        and key == DEFAULT_COMPANY_IMPORT_SIGNING_KEY
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Company import signing key is not configured securely",
        )
    return key


def _issues_detail(issues: list[CompanyImportIssue]) -> list[dict[str, object]]:
    return [issue.model_dump() for issue in issues]


@router.post(
    "/{company_id}/configuration-import/preview",
    response_model=CompanyImportPreviewResponse,
)
async def preview_company_import_endpoint(
    company_id: UUID,
    workbook: Annotated[
        UploadFile, File(description="Company Configuration XLSX")
    ],
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CompanyImportPreviewResponse:
    company = await get_company(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    filename = workbook.filename or ""
    if Path(filename).suffix.casefold() != ".xlsx":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=_issues_detail(
                [
                    CompanyImportIssue(
                        sheet=None,
                        message="Only .xlsx workbooks are supported",
                    )
                ]
            ),
        )
    if workbook.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=_issues_detail(
                [
                    CompanyImportIssue(
                        sheet=None,
                        message="Unsupported workbook media type",
                    )
                ]
            ),
        )

    try:
        contents = await workbook.read(MAX_FILE_BYTES + 1)
    finally:
        await workbook.close()

    try:
        return await preview_company_import(
            session=session,
            company=company,
            tenant=tenant,
            contents=contents,
            signing_key=_signing_key(settings),
        )
    except CompanyWorkbookError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=_issues_detail(exc.issues),
        ) from exc
    except CompanyImportValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=_issues_detail(exc.issues),
        ) from exc


@router.post(
    "/{company_id}/configuration-import/apply",
    response_model=CompanyImportApplyResponse,
)
async def apply_company_import_endpoint(
    company_id: UUID,
    request: CompanyImportApplyRequest,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CompanyImportApplyResponse:
    try:
        response = await apply_company_import(
            session=session,
            tenant=tenant,
            company_id=company_id,
            preview_token=request.preview_token,
            signing_key=_signing_key(settings),
        )
    except PreviewTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except CompanyInputError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except (
        CompanyStateConflictError,
        CompanyLocationStateConflictError,
        CompanyGSTRegistrationStateConflictError,
        FinancialYearStateConflictError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except (
        CompanyLocationInputError,
        CompanyGSTRegistrationInputError,
        FinancialYearInputError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except (
        CompanyLocationNotFoundError,
        CompanyGSTRegistrationNotFoundError,
        FinancialYearNotFoundError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    if response is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )
    return response
