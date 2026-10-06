# Company Configuration Data Model and Persistence Design

## 1. Status, authority, and scope

**Document status:** `CURRENT WORKING DESIGN / PROPOSED FOR FREEZE` — documentation and design only.

This is the canonical Company Configuration database-design review artifact. Read it with the [Company Configuration Overview](README.md), [Requirements](requirements.md), [Workflows](workflows.md), [Business Rules](business_rules.md), and [Open Decisions](open_decisions.md). It follows the shared [Module Boundaries](../../architecture/module_boundaries.md) and shared-table contracts in [database.md](../../requirements/database.md).

It does not authorize SQL, migrations, ORM models, APIs, services, routes, frontend work, or tests.

## 2. Table Inventory by Domain

The Company Configuration design encompasses 54 Core/Shared and Company Configuration entities grouped into 11 domains:

### 2.1 Tenant & Organisation Domain
1. `tenants` — Top-level SaaS account owner & isolation boundary (`KEEP`).
2. `organisations` — Optional non-legal grouping of Companies within a Tenant (`KEEP`).

### 2.2 Geography & Legal Identity Domain
3. `countries` — Shared ISO 3166-1 alpha-2 Country reference master (`KEEP`).
4. `country_subdivisions` — Shared first-level State/UT/Province reference master (`KEEP`).
5. `entity_types` — Shared jurisdiction-scoped legal forms (e.g., Private Limited, LLP) (`KEEP`).
6. `company_identifier_types` — Shared jurisdiction-scoped legal identifier types (PAN, CIN, LLPIN) (`KEEP`).
7. `entity_type_identifier_rules` — Applicability rules (REQUIRED / OPTIONAL) per Entity Type (`KEEP`).
8. `company_identifiers` — Company legal identifier values (`KEEP`).

### 2.3 Company Root & Identity History Domain
9. `companies` — Stable current legal/business identity and seller defaults (`KEEP`).
10. `company_legal_name_versions` — Effective-dated legal name history for stable Company identity (`KEEP`).

### 2.4 GST & Location Domain
11. `gst_registration_types` — Controlled GST registration types (`KEEP`).
12. `company_gst_registrations` — Company State-scoped GST registrations (`KEEP`).
13. `company_gst_registration_versions` — Legal name versioning per GST Registration (`REVIEW`).
14. `company_locations` — Stable Company Location identity with fixed-purpose flags (`KEEP`).
15. `company_location_versions` — Effective-dated Location address and jurisdiction history (`KEEP`).

### 2.5 Fiscal & Compliance Domain
16. `company_fiscal_settings` — Recurring fiscal start pattern (`APR_MAR`, `JAN_DEC`, `CUSTOM`) (`KEEP`).
17. `financial_years` — Non-overlapping dated Financial Years (`DRAFT`, `OPEN`, `CLOSED`) (`KEEP`).
18. `company_luts` — Active LUT reference per GSTIN and Fiscal Year (`KEEP`).

### 2.6 Currency, FX & Banking Domain
19. `currencies` — Shared ISO currency reference master (`KEEP`).
20. `company_reporting_currencies` — Company additional reporting currencies (`KEEP`).
21. `company_ar_currencies` — Company AR currencies with Billing & Receipt permissions (`KEEP`).
22. `company_bank_accounts` — Company Bank Accounts with currency, type, optional Bank GL FK, default (`KEEP`).
23. `exchange_rates` — Shared exchange rate facts by currency pair and rate type (`KEEP`).
24. `fx_policies` — Process-specific FX rate selection rules (`KEEP`).

### 2.7 Tax & Statutory References Domain
25. `tax_types` — Controlled tax families (GST, TDS, TCS, VAT, CESS) (`KEEP`).
26. `company_hsn_sac_codes` — Company-configured HSN/SAC codes (`KEEP`).
27. `tax_rates` — Controlled numeric tax rates per tax type (`KEEP`).
28. `company_hsn_sac_tax_rates` — Effective eligible tax rates per Company HSN/SAC (`KEEP`).
29. `tax_treatments` — Controlled GST treatments (TAXABLE, NIL_RATED, EXEMPT, NON_GST) (`KEEP`).
30. `tax_statutory_codes` — Controlled COMPONENT / SECTION statutory identities (`KEEP`).
31. `tax_statutory_code_rates` — Statutory section rates (`KEEP`).
32. `supply_types` — Controlled supply types (B2B, B2C, EXPWOP, EXPWP, SEZWOP, SEZWP) (`KEEP`).

### 2.8 Catalogue & Products Domain
33. `service_categories` — Company service categories (`KEEP`).
34. `service_types` — Billable service items with SAC, Base GST Nature, rate, Business Segment (`KEEP`).
35. `product_categories` — Company product categories (`KEEP`).
36. `products` — Company product groupings (`KEEP`).
37. `skus` — Sellable goods SKUs with HSN, UOM, Base GST Nature, rate, Business Segment (`KEEP`).

### 2.9 Cost Centers & Teams Domain
38. `cost_center_locations` — Location Cost Center reporting buckets (`KEEP`).
39. `cost_center_business_segments` — Business Segment reporting buckets (`KEEP`).
40. `cost_center_teams` — Cost Center Team reporting buckets (`KEEP`).
41. `teams` — Actual operational Company Teams (`KEEP`).
42. `team_memberships` — Effective-dated user memberships in actual Teams (`KEEP`).
43. `company_cost_center_settings` — Enablement flags for Business Segment, Team, Location (`KEEP`).

### 2.10 Numbering & Commercial Defaults Domain
44. `document_sequences` — Document numbering series format and atomic counter per FY (`KEEP`).
45. `document_sequence_conditions` — Controlled applicability conditions per sequence (`KEEP`).
46. `payment_terms` — Reusable `IMMEDIATE` and `NET_DAYS` Payment Terms with Company default (`KEEP`).

### 2.11 Output, Delivery, Reminders & Administration Domain
47. `stored_files` — Provider-neutral binary asset metadata (logo, signature, stamp) (`KEEP`).
48. `company_document_branding` — Company branding assets referencing `stored_files` (`KEEP`).
49. `company_document_templates` — Versioned server-side document template selections (`KEEP`).
50. `email_provider_configs` — Tenant/Company email provider configuration (`KEEP`).
51. `company_invoice_delivery_settings` — Invoice delivery preferences and provider association (`KEEP`).
52. `reminder_policies` — Company reminder enablement policy (`KEEP`).
53. `reminder_schedule_rules` — Reminder offset days and schedule rules (`KEEP`).
54. `company_approval_settings` — Approver roles per document type (`REVIEW`).
55. `company_user_memberships` — Explicit user access memberships per Company (`KEEP`).

## 3. Entity-Relationship Diagram

~~~mermaid
erDiagram
    tenants ||--o{ organisations : "tenant_id"
    tenants ||--o{ companies : "tenant_id"
    organisations |o--o{ companies : "organisation_id"
    entity_types |o--o{ companies : "entity_type_id"
    currencies |o--o{ companies : "base_currency_code"
    countries ||--o{ company_identifier_types : "country_code"
    countries ||--o{ country_subdivisions : "country_code"
    companies ||--o{ company_identifiers : "company_id"
    company_identifier_types ||--o{ company_identifiers : "identifier_type_id"
    entity_types ||--o{ entity_type_identifier_rules : "entity_type_id"
    company_identifier_types ||--o{ entity_type_identifier_rules : "identifier_type_id"
    companies ||--o{ company_legal_name_versions : "company_id"
    companies ||--o{ company_gst_registrations : "company_id"
    gst_registration_types |o--o{ company_gst_registrations : "gst_registration_type_id"
    country_subdivisions ||--o{ company_gst_registrations : "subdivision_code"
    company_gst_registrations ||..o{ company_gst_registration_versions : "REVIEW gst_registration_id"
    companies ||--o{ company_locations : "company_id"
    company_gst_registrations |o--o{ company_locations : "gst_registration_id"
    cost_center_locations |o--o{ company_locations : "cost_center_location_id"
    countries ||--o{ company_locations : "country_code"
    country_subdivisions |o--o{ company_locations : "subdivision_code"
    company_locations ||--o{ company_location_versions : "company_location_id"
    countries ||--o{ company_location_versions : "country_code"
    country_subdivisions |o--o{ company_location_versions : "subdivision_code"
    companies ||--|| company_fiscal_settings : "company_id"
    companies ||--o{ financial_years : "company_id"
    companies ||--o{ company_luts : "company_id"
    company_gst_registrations ||--o{ company_luts : "gst_registration_id"
    financial_years ||--o{ company_luts : "financial_year_id"
    companies ||--o{ company_reporting_currencies : "company_id"
    currencies ||--o{ company_reporting_currencies : "currency_code"
    companies ||--o{ company_ar_currencies : "company_id"
    currencies ||--o{ company_ar_currencies : "currency_code"
    companies ||--o{ company_bank_accounts : "company_id"
    currencies ||--o{ company_bank_accounts : "currency_code"
    gl_accounts |o--o{ company_bank_accounts : "gl_account_id"
    companies ||--o{ exchange_rates : "company_id"
    currencies ||--o{ exchange_rates : "from_currency_code"
    currencies ||--o{ exchange_rates : "to_currency_code"
    companies ||--o{ fx_policies : "company_id"
    companies ||--o{ company_hsn_sac_codes : "company_id"
    tax_types ||--o{ tax_rates : "tax_type_id"
    tax_types ||--o{ tax_treatments : "tax_type_id"
    tax_types ||--o{ tax_statutory_codes : "tax_type_id"
    tax_statutory_codes ||--o{ tax_statutory_code_rates : "tax_statutory_code_id"
    company_hsn_sac_codes ||--o{ company_hsn_sac_tax_rates : "company_hsn_sac_code_id"
    tax_rates ||--o{ company_hsn_sac_tax_rates : "tax_rate_id"
    companies ||--o{ service_categories : "company_id"
    companies ||--o{ service_types : "company_id"
    service_categories ||--o{ service_types : "service_category_id"
    company_hsn_sac_codes ||--o{ service_types : "company_hsn_sac_code_id"
    tax_treatments ||--o{ service_types : "base_tax_treatment_id"
    tax_rates |o--o{ service_types : "selected_tax_rate_id"
    cost_center_business_segments |o--o{ service_types : "business_segment_id"
    company_hsn_sac_codes ||--o{ skus : "company_hsn_sac_code_id"
    tax_treatments ||--o{ skus : "base_tax_treatment_id"
    tax_rates |o--o{ skus : "selected_tax_rate_id"
    cost_center_business_segments |o--o{ skus : "business_segment_id"
    companies ||--o{ product_categories : "company_id"
    companies ||--o{ products : "company_id"
    product_categories ||--o{ products : "product_category_id"
    companies ||--o{ skus : "company_id"
    products ||--o{ skus : "product_id"
    companies ||--o{ cost_center_locations : "company_id"
    companies ||--o{ cost_center_business_segments : "company_id"
    companies ||--o{ cost_center_teams : "company_id"
    companies ||--o{ payment_terms : "company_id"
    companies ||--o{ company_document_branding : "company_id"
    companies ||--|| reminder_policies : "company_id"
    companies ||--o{ company_user_memberships : "company_id"
    companies ||--o{ stored_files : "company_id"
    companies ||--o{ document_sequences : "company_id"
    companies ||--o{ teams : "company_id"
    cost_center_teams |o--o{ teams : "cost_center_team_id"
    teams ||--o{ team_memberships : "team_id"
    companies ||--|| company_cost_center_settings : "company_id"
    financial_years ||--o{ document_sequences : "financial_year_id"
    document_sequences ||--o{ document_sequence_conditions : "document_sequence_id"
    companies ||--o{ company_document_templates : "company_id"
    company_document_branding |o--o{ company_document_templates : "branding_id"
    stored_files |o--o{ company_document_branding : "logo_file_id"
    stored_files |o--o{ company_document_branding : "signature_file_id"
    stored_files |o--o{ company_document_branding : "stamp_file_id"
    tenants ||--o{ email_provider_configs : "tenant_id"
    companies |o--o{ email_provider_configs : "company_id"
    companies ||--|| company_invoice_delivery_settings : "company_id"
    email_provider_configs |o--o{ company_invoice_delivery_settings : "email_provider_config_id"
    reminder_policies ||--o{ reminder_schedule_rules : "reminder_policy_id"
    companies ||..o{ company_approval_settings : "REVIEW company_id"
~~~

The editable Mermaid source is [data_model.mmd](data_model.mmd).
