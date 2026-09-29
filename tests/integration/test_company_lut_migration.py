from tests.integration.company_configuration_migration_support import execute, rejected, run_migration_case, scalar, seed_company


async def _exercise(url: str) -> None:
    _, company = await seed_company(url)
    await execute(url, "INSERT INTO core.countries (code, name, status) VALUES ('IN', 'India', 'ACTIVE')")
    await execute(url, "INSERT INTO core.country_subdivisions (country_code, code, name, subdivision_type, gst_state_code, status) VALUES ('IN', 'IN-UP', 'Uttar Pradesh', 'STATE', '09', 'ACTIVE')")
    registration = await scalar(url, "INSERT INTO core.company_gst_registrations (company_id, gstin, subdivision_code, status) VALUES (:company, '09ABCDE1234F1Z5', 'IN-UP', 'ACTIVE') RETURNING id", {"company": company})
    year = await scalar(url, "INSERT INTO core.financial_years (company_id, start_date, end_date, display_code, is_transition, status) VALUES (:company, '2026-04-01', '2027-03-31', 'FY2026-27', false, 'OPEN') RETURNING id", {"company": company})
    sql = "INSERT INTO ar.company_luts (company_id, gst_registration_id, financial_year_id, lut_reference, valid_from, status) VALUES (:company, :gst, :year, 'LUT-1', '2026-04-01', :status)"
    values = {"company": company, "gst": registration, "year": year, "status": "ACTIVE"}
    await execute(url, sql, values)
    await rejected(url, sql, values)
    await rejected(url, sql, {**values, "status": "DRAFT"})
    await rejected(url, "DELETE FROM core.financial_years WHERE id = :id", {"id": year})


def test_company_lut_migration_contract() -> None:
    run_migration_case("0021_company_luts", "0020_accounting_configuration", ("ar.company_luts",), _exercise)
