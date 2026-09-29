from tests.integration.company_configuration_migration_support import execute, rejected, run_migration_case, scalar, seed_company


async def _exercise(url: str) -> None:
    _, company = await seed_company(url)
    file_id = await scalar(url, "INSERT INTO core.stored_files (company_id, object_key, content_hash, content_type, size_bytes) VALUES (:company, 'logos/logo.png', 'abc', 'image/png', 10) RETURNING id", {"company": company})
    branding = await scalar(url, "INSERT INTO ar.company_document_branding (company_id, logo_file_id, status) VALUES (:company, :file, 'ACTIVE') RETURNING id", {"company": company, "file": file_id})
    sql = "INSERT INTO ar.company_document_templates (company_id, document_type, branding_id, template_key, version_no, show_logo, show_bank_details, show_signature, show_hsn_sac, show_customer_reference, status) VALUES (:company, :type, :branding, 'standard', 1, true, true, true, true, true, 'ACTIVE')"
    await execute(url, sql, {"company": company, "type": "TI", "branding": branding})
    await rejected(url, sql, {"company": company, "type": "OTHER", "branding": branding})
    await rejected(url, "INSERT INTO core.stored_files (company_id, object_key, content_hash, content_type, size_bytes) VALUES (:company, 'bad', 'x', 'text/plain', -1)", {"company": company})
    await rejected(url, "DELETE FROM core.stored_files WHERE id = :id", {"id": file_id})


def test_file_document_presentation_migration_contract() -> None:
    run_migration_case("0022_file_document_presentation", "0021_company_luts", ("core.stored_files", "ar.company_document_branding", "ar.company_document_templates"), _exercise)
