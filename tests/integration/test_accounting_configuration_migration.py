from datetime import date

from tests.integration.company_configuration_migration_support import execute, rejected, run_migration_case, scalar, seed_company


async def _exercise(url: str) -> None:
    _, company = await seed_company(url)
    gl_account = await scalar(url, "INSERT INTO core.gl_accounts (company_id, account_name, valid_from, status) VALUES (:company, 'Receivable', '2026-01-01', 'ACTIVE') RETURNING id", {"company": company})
    await execute(url, "INSERT INTO core.countries (code, name, status) VALUES ('IN', 'India', 'ACTIVE')")
    tax_type = await scalar(url, "INSERT INTO core.tax_types (code, name, country_code, status) VALUES ('GST', 'GST', 'IN', 'ACTIVE') RETURNING id")
    statutory = await scalar(url, "INSERT INTO core.tax_statutory_codes (tax_type_id, code, name, code_kind, country_code, status) VALUES (:tax, 'CGST', 'Central GST', 'COMPONENT', 'IN', 'ACTIVE') RETURNING id", {"tax": tax_type})
    await execute(url, "INSERT INTO core.company_accounting_settings (company_id, default_receivable_gl_account_id) VALUES (:company, :gl)", {"company": company, "gl": gl_account})
    await execute(url, "INSERT INTO ar.revenue_gl_mappings (company_id, supply_type_code, gl_account_id, valid_from, status) VALUES (:company, 'GOODS', :gl, '2026-01-01', 'ACTIVE')", {"company": company, "gl": gl_account})
    mapping_sql = "INSERT INTO ar.tax_gl_account_mappings (company_id, tax_statutory_code_id, gl_account_id, valid_from, valid_to, status) VALUES (:company, :code, :gl, :start, :end, :status)"
    values = {"company": company, "code": statutory, "gl": gl_account, "start": date(2026, 1, 1), "end": date(2026, 12, 31), "status": "ACTIVE"}
    await execute(url, mapping_sql, values)
    await rejected(url, mapping_sql, {**values, "start": date(2026, 6, 1), "end": date(2027, 1, 1)})
    await rejected(url, mapping_sql, {**values, "status": "DRAFT", "start": date(2028, 1, 1), "end": date(2028, 12, 31)})
    await rejected(url, "DELETE FROM core.gl_accounts WHERE id = :id", {"id": gl_account})


def test_accounting_configuration_migration_contract() -> None:
    run_migration_case("0020_accounting_configuration", "0019_tax_statutory_codes_rates", ("ar.revenue_gl_mappings", "ar.tax_gl_account_mappings", "core.company_accounting_settings"), _exercise)
