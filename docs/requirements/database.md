# SKMC ERP AR — Company Configuration Database Design

**Status:** Working design / review draft — not a migration specification  
**Scope:** Company Configuration + directly related AR configuration only  
**Goal:** Keep one visible record of the current table plan, the data each table stores, why it exists, and what changed from the earlier database plan.

---

## 1. Design Rules We Are Following

1. Keep **Core/Shared** company masters separate from **AR-specific** configuration, even if they live in one PostgreSQL database initially.
2. Do not create a table for a fixed product rule unless the value genuinely varies by Company, document, date, or process.
3. Prefer a direct FK for a true **1:N** relationship; use a mapping table only for real **M:N** membership or independent membership history.
4. Final invoices/financial documents will snapshot the actual legal, tax, currency and presentation values used. A mutable master must never rewrite an old finalized document.
5. Deactivate historically used masters instead of physically deleting them.
6. Keep current MVP simple, but preserve known extension points such as conditional numbering, multi-currency receipts and future approval stages.
7. Do not duplicate a concept in Company Configuration and another downstream module. Shared masters are referenced by Customer/SO/Billing/Receipt flows.
8. Company GL Accounts and mappings use stable IDs, while accounting classifications remain deferred. Example account names are never product constants.
9. Binary files belong in object storage. PostgreSQL stores provider-neutral file identity, immutable object key, content hash and useful metadata; domain tables use typed file FKs rather than raw binary data, provider URLs or duplicated storage metadata.

---

## 2. Status Legend

- **KEEP** — part of the current Company Configuration database plan.
- **KEEP / POLICY TBD** — table is needed, but some business rules/columns are not frozen yet.
- **REVIEW** — useful only if the stated business requirement is confirmed.
- **DEFER** — not required for current Company Configuration MVP.
- **REMOVE / MERGED / REPLACED** — earlier table/concept retired, combined, or superseded by the current design.

---

## 3. Change Log — What Changed From the Earlier Plan

| Area / Table | Earlier Plan | Current Decision | Reason |
|---|---|---|---|
| Shared file/object metadata | Domain-specific raw storage keys/references without one approved shared identity | **ADD/KEEP `stored_files`** | Company-owned assets and immutable artifacts need one provider-neutral metadata identity; binary bytes remain in Cloudflare R2 behind `ObjectStorage`, and domain relationships remain explicit typed FKs |
| `tenants` | `tenant_id` appeared as a platform concept rather than a proper master | **KEEP `tenants`** | SaaS isolation needs a stable root entity; IDs alone should point to an authoritative Tenant record |
| Company identity foundation | Organisation code, Company-code scope, Draft nullability, and exact Company foundation constraints were unresolved | **CONFIRM/IMPLEMENT `currencies`, `organisations`, and `companies`** | The approved slice uses a global Currency master, code-free Tenant-owned Organisation grouping with same-Tenant Company enforcement, and Draft-capable Company identity with globally generated `COM` codes |
| Geographic reference masters | Country and State candidates were deferred application-controlled codes | **KEEP `countries` and `country_subdivisions`** | Platform-managed ISO-compatible Country and first-level subdivision references provide stable shared identities without introducing City, District, postal-code, or address-hierarchy masters |
| Company locations | Separate Location + address + purpose mapping | **Keep address + fixed-purpose flags on `company_locations` for MVP** | Current purposes are fixed and a separate mapping adds joins without current value |
| GST Registration ↔ Location | GST/location mapping table | **`company_locations.gst_registration_id` nullable FK plus `is_default_for_gstin`** | One GST Registration has many Locations, one Location has zero/one Registration, and exactly one active mapped default exists where applicable; no M:N bridge is required |
| Location address history | Separate version table | **KEEP `company_location_versions` for effective-dated address/jurisdiction history** | A stable Location may move while preserving immediately effective address history independently of finalized invoice snapshots; the table does not version all Location configuration, and future/backdated workflows are outside MVP |
| Location cost center membership | Cost-center location + membership table | **Store `cost_center_location_id` directly on `company_locations`** | One physical Location belongs to max one current location cost-center group; direct FK is sufficient |
| Generic `cost_centers` / `cost_center_types` | Generic cost-center engine | **REMOVE** | Current model uses Business Segment and Location Group as reporting identities plus an explicit Cost Center Team bucket over separate actual Teams |
| `cost_center_business_segments` | Normal `business_segments` / generic mapping | **KEEP renamed master** | Name makes clear these Business Segments are being used as cost-center/reporting buckets |
| `cost_center_teams` | Actual Team combined with reporting identity | **KEEP as reporting bucket** | One Company-owned Cost Center Team may group multiple actual Teams; it does not own user memberships directly |
| `teams` | No separate operational Team identity | **ADD / KEEP actual Team master** | Actual Teams are Company-owned identities, may optionally reference one Cost Center Team, and own effective-dated user memberships |
| Cost-center policy | `cost_center_policies` | **Rename to `company_cost_center_settings`** | It is simple feature enablement, not a generic policy/rule engine |
| Base currency | Separate Company base-currency table | **Store `companies.base_currency_code`** | Exactly one base currency per Company; child table adds no value |
| Billing/payment currencies | Separate billing and payment currency tables | **Use `company_ar_currencies`** | Same currency can be enabled for Billing, Receipt, or both; later payment-only currency is one new row/flag change |
| EEFC handling | No explicit design | **Use `company_bank_accounts.currency_code` + bank-account type** | USD/EUR receipt can remain in same currency and knock off same-currency receivable |
| Exchange rates | Billing-owned `exchange_rate` | **Move to Core/Company Configuration `exchange_rates`** | FX reference is reused by Billing, Receipt, Reporting and future Accounting |
| FX policy | Considered defer/remove | **KEEP `fx_policies`** | Rate facts and rate-selection rules are different concepts; process-specific behavior should not be hardcoded |
| Tax family | Tax-family strings embedded in rate/section tables | **Add controlled `tax_types`** | GST, TDS, TCS, VAT and CESS are tax families, not HSN/SAC codes, percentages or statutory sections |
| HSN/SAC | Separate global masters or ambiguous `tax_classifications` | **Use Company-owned `company_hsn_sac_codes`** | A Company configures only relevant HSN/SAC codes; the name cannot be confused with GST/TDS/TCS classification |
| Numeric tax rate | GST-only rate master with embedded `tax_type` text | **Use `tax_rates.tax_type_id`** | Controlled numeric rates belong to a tax family without hardcoded family strings |
| HSN/SAC ↔ rate | `tax_classification_rates` | **Replace with `company_hsn_sac_tax_rates`** | One Company HSN/SAC code can have multiple effective eligible rates and only those rates should be selectable |
| Tax treatment | Code repeated on catalogue items without a controlled master | **Add `tax_treatments`** | TAXABLE, NIL_RATED, EXEMPT and NON_GST are controlled treatments distinct from a numeric 0% rate |
| Service/SKU tax mapping tables | Separate effective-dated assignment tables | **Store current Company HSN/SAC, Base GST Nature, and conditional selected eligible rate on `service_types` / `skus`** | Company HSN/SAC-to-rate mapping validates rate selection where required; finalized lines snapshot base nature/final outcome/rate/components and items do not hold uncontrolled percentage text |
| Tax statutory identities | TDS/TCS-only `statutory_sections` plus free-text GST component codes | **Use `tax_statutory_codes` + `tax_statutory_code_rates`** | COMPONENT and SECTION identities share one controlled layer while ordinary GST item rates remain separate |
| Supply/GST reference types | `type_of_supply`, `gst_registration_type`, `tax_component` in Billing | **Move `supply_types` / `gst_registration_types` to Company/Core reference only if configurable data is needed; do not create `tax_components` table now** | Supply/registration types are shared reference vocabulary; CGST/SGST/IGST are derived components and can remain controlled codes |
| Numbering applicability | Many nullable columns on `document_sequences` | **Use `document_sequence_conditions`** | New supported series parameters should not require adding a DB column each time |
| `document_sequences` | Existing | **KEEP** | One table owns format + counter; conditions remain separate |
| `ar_billing_defaults` | Separate defaults row | **REMOVE** | Defaults should live with the owning master (`payment_terms.is_default`, bank default, currency default) instead of another mini-settings table |
| Recurring settings | Company-level recurring configuration | **REMOVE from Company Configuration** | Advance/Milestone/Periodic/Recurring behavior belongs to Sales Order/contract/Billing Schedule |
| `company_user_access` | Proposed duplicate access table | **KEEP `company_user_memberships`** | Explicit Company membership is required; tenant membership alone cannot express Company-specific authorization |
| LUT | Blanket all-four Export/SEZ requirement | **Require valid LUT for current without-payment routes EXPWOP and SEZWOP; do not require it merely for EXPWP or SEZWP** | Current approved product rule distinguishes without-payment routes; management/legal policy can revise this later |
| Approval settings | Generic workflow direction | **Keep only a small `company_approval_settings` table if behavior varies by Company/document type** | Fixed rules should stay in code; configurable values belong in DB |
| Customer-only billing | Every document assumed to be an external Customer receivable | **Classify `CUSTOMER_SALE` / `INTER_UNIT` and capture same-Company source/destination GST/Location context** | Inter-Unit may have statutory document behavior but never models the destination as Customer or creates normal AR outstanding |
| Ship-To | Customer Location only | **Discriminate `CUSTOMER_LOCATION` / `COMPANY_LOCATION`** | A shipment may go to a Customer site or the seller Company's own Location; final documents snapshot the address |
| GSTR-1 edit lock | Generic invoice filing flag | **Batch by GST Registration + Return Period + Return Type; lock only FILED membership** | Draft batch membership remains editable with audit; filed batch/membership retains exact statutory evidence |
| E-invoice edit lock | No explicit IRN evidence guard | **Record successful e-invoice/IRN evidence on the AR Document** | Successful IRN generation independently blocks in-place invoice editing |
| CoA and AR account resolution | Typed/hierarchical GL rows and three-table Revenue Mapping | **Stable GL identities + effective hierarchy/mappings + Company default receivable + direct Bank GL FK** | Reorganization preserves history; Supply Type/optional HSN-SAC and statutory codes resolve accounts without hardcoded names; Inter-Unit clearing remains open |
| AR Delivery / Reminders | Initial design | **KEEP with exact physical definitions** | Automatic sending defaults OFF, manual send allowed, reminder precedence: Company -> Customer -> Invoice |

---

# 4. Core / Shared Company Configuration Tables

## 1. `tenants` — KEEP

**What data is stored**
- The top-level SaaS customer/account identity and authoritative data-isolation boundary.
- A Tenant is not a legal Company, GST entity, Company registration, or accounting entity. One Tenant may own several legal Companies, and an optional Organisation may group Companies inside that Tenant.

Example:

```text
Tenant: SKMC Global Account
├── Company: SKMC Global Pvt Ltd
├── Company: SKMC Singapore Pte Ltd
└── Company: another legal Company
```

Another SaaS customer belongs to a different Tenant even if a Company name happens to be similar.

**Columns**
- `id` UUID PRIMARY KEY DEFAULT `gen_random_uuid()`
- `name` VARCHAR(200) NOT NULL
- `code` VARCHAR(50) NOT NULL UNIQUE DEFAULT `core.next_tenant_code()`
- `status` VARCHAR(20) NOT NULL
- `created_at` TIMESTAMPTZ NOT NULL DEFAULT `CURRENT_TIMESTAMP`
- `updated_at` TIMESTAMPTZ NOT NULL DEFAULT `CURRENT_TIMESTAMP`

**Column meanings and reasons**

- `id` is the stable internal database identity. Tenant names can change, and the business/support-facing code must not become relational identity. Foreign keys reference this UUID, which also remains safe across SaaS environments and future controlled import or distributed scenarios. PostgreSQL generates it with `gen_random_uuid()` unless a legitimate explicit UUID is supplied.
- `name` is the human-readable SaaS customer/account name, such as `SKMC Global`, `ABC Group`, or `XYZ Enterprises`. It need not equal any Company's legal name and is intentionally not globally unique. It cannot be null or blank.
- `code` is the stable human-friendly Tenant reference used by support, administration UI, operational logs, exports, integrations, and migration/reference work. It is not the primary key. PostgreSQL generates `TEN` plus a zero-padded concurrency-safe sequence value, starting with `TEN000001`; gaps are accepted, consumed values are never reused, and numbering continues beyond six digits within `VARCHAR(50)`. Ordinary onboarding does not accept a user-invented code, while controlled operations may supply an explicit value when legitimately required.
- `status` controls the Tenant-level operational lifecycle and access state. It is stored as `VARCHAR(20)` with a CHECK allowing only `ACTIVE` (normal operation), `SUSPENDED` (temporarily restricted at platform/account level), and `INACTIVE` (not operational for normal use while historical data remains preserved). `DELETED` is not a normal business state. There is no database default; creation explicitly chooses a state.
- `created_at` records when the Tenant record was created for operational history, support, and platform administration. PostgreSQL supplies `CURRENT_TIMESTAMP`; it does not replace generic audit history.
- `updated_at` records only when the current Tenant record was last changed. PostgreSQL supplies `CURRENT_TIMESTAMP` on insert. No update trigger is part of the first migration; the application update path will manage later changes. It does not identify the actor, changed field, old/new values, or reason; those belong to the future generic Audit architecture.

`created_by` and `updated_by` are not part of the approved Tenant design. Attribution remains dependent on the future generic Audit design rather than introducing inconsistent per-table audit columns now.

**Relationships**
- Tenant 1:N Companies. Every Company has exactly one authoritative Tenant owner through `companies.tenant_id` NOT NULL FK → `tenants.id`.
- Tenant 1:N Organisations. Organisation is an optional grouping layer inside a Tenant.
- Company ownership is never inferred only through Company → Organisation → Tenant. A Company retains its direct authoritative Tenant relationship even when it belongs to an Organisation.
- Tenant and User are conceptually N:M through Tenant/User membership or access relationships: Tenant 1:N memberships and User 1:N memberships. Do not model this as a simple Tenant 1:N Users ownership rule. The exact membership persistence and multi-Tenant User policy remain open under IAM/access architecture.

**Tenant isolation rule**

The main value of `tenants` is the isolation rule established by the master. Every Company-scoped business record must be safely resolvable to exactly one Tenant through authoritative ownership relationships, including Companies, Customers, Sales Orders, invoices, Receipts, imports/exports, permissions, and configuration.

This requirement does not mean adding `tenant_id` blindly to every table. Direct versus derived Tenant keys must be decided table by table, while Tenant ownership remains unambiguous and enforceable.

**Why this table exists**
1. It is the authoritative top-level SaaS owner of business data and the primary isolation boundary between SaaS customers.
2. It prevents Companies from different customers being mixed even when names/codes are similar.
3. It allows one SaaS customer to own multiple legal Companies.
4. It supplies a common ownership scope for Companies, Organisations, access memberships, permissions, exports, and future platform features without inferring ownership indirectly through Company or User relationships.
5. It provides a clear future operational scope from Tenant → all owned Companies → all business data for account export, support/administration, backup/restore strategy, and SaaS account administration without placing those features in this table.
6. It lets shared platform modules rely on the same Tenant isolation model.
7. Removing it would force SaaS ownership to be inferred indirectly and make cross-customer isolation harder to enforce.

**Constraints and indexing**

- PRIMARY KEY: `id`.
- UNIQUE: `code`; do not add `UNIQUE (name)`.
- NOT NULL: `id`, `name`, `code`, `status`, `created_at`, and `updated_at`.
- CHECK `ck_tenants_status`: `status IN ('ACTIVE', 'SUSPENDED', 'INACTIVE')`.
- CHECK `ck_tenants_name_not_blank`: `btrim(name) <> ''`.
- CHECK `ck_tenants_code_not_blank`: `btrim(code) <> ''`.
- The primary-key index covers `id`; `UNIQUE (code)` supplies the unique code index.
- Do not add speculative status or administration indexes without a demonstrated query/workload requirement.
- No normal Tenant hard-delete workflow, delete trigger, or cascade is part of this slice. Future Tenant-owned FKs are restrictive unless a later approved requirement says otherwise. Lifecycle status/inactivation preserves historical ERP data; exact exceptional deletion and retention rules may later be strengthened by approved Audit/retention architecture.
- PostgreSQL RLS and request/session Tenant-context machinery are not part of the first Tenant migration. Downstream ownership constraints remain table-specific, while authentication and authorization are separate approved concerns.

**What does not belong in `tenants`**

The Tenant master intentionally remains small and stable. Do not store PAN, GSTIN, CIN, LLPIN, legal address, Registered Office, Base Currency, Company Financial Year, Company Bank Accounts, GST registrations, Company tax configuration, Company logo/legal branding, accounting configuration, Company-specific time zone, `owner_user_id`, `organisation_id`, `company_id`, or a generic settings JSON object here. These values belong to Company/legal/business configuration or separately owned platform capabilities.

SaaS subscription and plan details also do not belong directly in this table. A future platform model may relate Tenant → Subscription → Plan, but no subscription or plan columns are approved here.

**Open boundaries**

- The exact Tenant/User membership table and whether one User may access several Tenants remain open under IAM/access architecture.
- Actor attribution and detailed change history remain open pending the generic Audit design.
- Tenant-scoped export, support/admin, backup/restore, subscription, and plan capabilities are future platform behavior; this table provides ownership scope but does not implement those features.

---

## 2. `organisations` — KEEP

**What data is stored**
- An optional logical, non-legal grouping of Companies within one Tenant.
- Its current purpose is grouping only. A Company may exist directly under a Tenant without belonging to an Organisation.

Example:

```text
Tenant: ABC Customer Account
├── Organisation: ABC Manufacturing Group
│   ├── Company: ABC Manufacturing Pvt Ltd
│   └── Company: ABC Components Pvt Ltd
├── Organisation: ABC Services Group
│   ├── Company: ABC Consulting Pvt Ltd
│   └── Company: ABC Advisory LLP
└── Company: an ungrouped Company
```

**Columns**
- `id` UUID PRIMARY KEY DEFAULT `gen_random_uuid()`
- `tenant_id` UUID NOT NULL FK → `tenants.id` ON DELETE NO ACTION
- `name` VARCHAR(200) NOT NULL
- `status` VARCHAR(20) NOT NULL
- `created_at` TIMESTAMPTZ NOT NULL DEFAULT `CURRENT_TIMESTAMP`
- `updated_at` TIMESTAMPTZ NOT NULL DEFAULT `CURRENT_TIMESTAMP`

**Column meanings and reasons**

- `id` is the stable internal Organisation identity. Names may change, while relationships keep referencing the same Organisation through its UUID. PostgreSQL generates it unless a legitimate explicit UUID is supplied.
- `tenant_id` identifies the authoritative Tenant owner. Every Organisation belongs to exactly one Tenant and cannot exist without it. Organisation ownership must not be inferred indirectly, and an Organisation cannot contain a Company owned by another Tenant.
- `name` is the human-readable group name, such as `ABC Manufacturing Group`, `International Operations`, or `Advisory Companies`. It is required, cannot be blank, and is unique only within its Tenant. Different Tenants may use the same Organisation name.
- No Organisation code is part of the approved MVP contract. UUID plus Tenant-scoped name are sufficient; another generated identifier system is not introduced without a demonstrated requirement.
- `status` controls grouping availability. It is stored as `VARCHAR(20)` with a CHECK allowing only `ACTIVE` (available for normal grouping/use) and `INACTIVE` (unavailable for new normal assignments while historical relationships remain preserved). It has no database default.
- `created_at` records when the Organisation row was created; PostgreSQL supplies `CURRENT_TIMESTAMP`.
- `updated_at` records when the current row was last modified. PostgreSQL supplies the insert value, while application update paths own later changes; there is no update trigger.

`created_by` and `updated_by` are not part of the approved Organisation design at this stage.

**Relationships**
- Tenant 1:N Organisations.
- Organisation 1:N Companies, with optional membership from the Company side.
- `companies.tenant_id` remains NOT NULL and is the authoritative Tenant ownership FK to `tenants.id`.
- `companies.organisation_id` is nullable and, when populated, references `organisations.id` only for grouping.

Both structures are valid:

```text
Tenant → Company
Tenant → Organisation → Company
```

Organisation never replaces the Company's direct Tenant ownership.

**Cross-Tenant consistency rule**

If Organisation `O1` belongs to Tenant `T1`, every Company referencing `O1` must also have `company.tenant_id = T1`. A Company owned by `T2` cannot reference `O1`. This invariant must be enforced by the database/backend design and cannot rely only on frontend validation.

The database enforces this invariant through `companies (tenant_id, organisation_id)` → `organisations (tenant_id, id)`, supported by `UNIQUE (tenant_id, id)`. The direct authoritative `companies.tenant_id` → `tenants.id` FK remains in place.

**Why this table exists**
1. A Tenant may own multiple Companies that management wants grouped together.
2. It avoids repeating group metadata on each Company.
3. It provides a structured reference for future group-level views or reporting without requiring schema redesign.
4. It remains separate from Company because Company is the actual legal, billing, tax, and accounting entity.
5. It is optional, so a simple Tenant structure does not need a meaningless extra grouping layer.
6. Removing it would force future grouping needs into ad-hoc tags, repeated text, or later schema redesign.

**No configuration inheritance**

Organisation provides grouping only. Companies do not automatically inherit Base Currency, time zone, Financial Year, GST registrations, PAN/CIN/LLPIN, legal address, Bank Accounts, Chart of Accounts, tax configuration, HSN/SAC setup, document numbering, invoice templates, invoice delivery/email settings, or other Company-level legal/accounting configuration from it.

Company remains the legal, billing, tax, and accounting boundary. Future consolidated or group reporting may use Organisation as a grouping reference, but no Organisation-level configuration inheritance is approved.

**Constraints and indexing**

- PRIMARY KEY: `id`.
- FOREIGN KEY: `tenant_id` → `tenants.id` with restrictive/no-action deletion.
- NOT NULL: `id`, `tenant_id`, `name`, `status`, `created_at`, and `updated_at`.
- UNIQUE: (`tenant_id`, `name`); do not make `name` globally unique.
- UNIQUE: (`tenant_id`, `id`) solely to support the same-Tenant Company/Organisation composite FK.
- CHECK `btrim(name) <> ''`.
- CHECK `status IN ('ACTIVE', 'INACTIVE')`; there is no status default.
- The primary-key and unique constraints provide their corresponding indexes. Do not add speculative indexes without demonstrated query requirements.
- An Organisation must not be hard-deleted once referenced by Company or historical data. Use `INACTIVE` for lifecycle retirement; exact long-term deletion/retention rules remain dependent on future generic Audit/retention architecture.

**What does not belong in `organisations`**

Do not store PAN, GSTIN, CIN, LLPIN, Registered Office/legal address, Company Base Currency, Company time zone, Financial Year, Bank Account, GST Registration, LUT, Chart of Accounts, GL configuration, tax configuration, document sequences, invoice seller configuration, Company-level email configuration, or a generic settings JSON object here. These remain Company/domain-specific unless a later approved requirement changes the boundary.

---

## 2A. `countries` — KEEP

**What data is stored**
- Global, platform-managed Country reference data using ISO 3166-1 alpha-2 identity.
- The table is not Tenant-owned or Company-owned and is not maintained by normal ERP users.

**Columns**
- `code` VARCHAR(2) PRIMARY KEY
- `name` VARCHAR(100) NOT NULL
- `status` VARCHAR(20) NOT NULL
- `created_at` TIMESTAMPTZ NOT NULL DEFAULT `CURRENT_TIMESTAMP`
- `updated_at` TIMESTAMPTZ NOT NULL DEFAULT `CURRENT_TIMESTAMP`

**Constraints and lifecycle**
- CHECK `code ~ '^[A-Z]{2}$'`.
- CHECK `btrim(name) <> ''`; Country name is not unique.
- CHECK `status IN ('ACTIVE', 'INACTIVE')`; there is no status default.
- Only the primary-key index is required; do not add speculative name or status indexes.
- Alpha-3 and numeric ISO columns are not part of the approved minimum contract.
- Referenced Countries are normally inactivated rather than deleted. Dependent FKs use restrictive/no-action deletion.
- PostgreSQL supplies timestamp insert defaults; application update paths own later `updated_at` changes and no update trigger is used.

**Provisioning and integration boundary**
- Migration 004 creates no Country seed rows. A separate version-controlled reference-data loader will provision the catalogue.
- Migration 004 does not retrofit `entity_types.country_code` or `companies.country_code` FKs. Those constraints require catalogue coverage and an audit of existing values first.

---

## 2B. `country_subdivisions` — KEEP

**What data is stored**
- Global, platform-managed first-level jurisdictions such as State, Union Territory, Province, Region, or equivalent.
- Codes use the complete ISO-compatible identifier, such as `IN-UP`, `IN-MH`, `IN-DL`, or `US-CA`.

**Columns**
- `id` UUID PRIMARY KEY DEFAULT `gen_random_uuid()`
- `country_code` VARCHAR(2) NOT NULL FK → `countries.code` ON DELETE NO ACTION
- `code` VARCHAR(10) NOT NULL UNIQUE
- `name` VARCHAR(150) NOT NULL
- `subdivision_type` VARCHAR(50) NOT NULL
- `gst_state_code` VARCHAR(2) nullable
- `status` VARCHAR(20) NOT NULL
- `created_at` TIMESTAMPTZ NOT NULL DEFAULT `CURRENT_TIMESTAMP`
- `updated_at` TIMESTAMPTZ NOT NULL DEFAULT `CURRENT_TIMESTAMP`

**Constraints and indexing**
- CHECK `code ~ '^[A-Z]{2}-[A-Z0-9]{1,3}$'`.
- CHECK `left(code, 2) = country_code`.
- CHECK `btrim(name) <> ''`; subdivision name is not unique.
- CHECK `subdivision_type ~ '^[A-Z]+(_[A-Z]+)*$'`. Values are canonical uppercase identifiers, but the database is not restricted to only State, Union Territory, Province, and Region.
- CHECK `gst_state_code IS NULL OR gst_state_code ~ '^[0-9]{2}$'`.
- Partial UNIQUE (`country_code`, `gst_state_code`) WHERE `gst_state_code IS NOT NULL`; GST State codes are country-scoped and the nullable field does not impose GST semantics on non-Indian subdivisions.
- CHECK `status IN ('ACTIVE', 'INACTIVE')`; there is no status default.
- INDEX (`country_code`) supports Country-based selection and FK operations. No other speculative indexes are approved.
- UUID is relational identity; `code` is the unique external identifier.
- Referenced subdivisions are normally inactivated rather than deleted.

**Scope boundary**
- Migration 004 contains no seed data or loader.
- Migration 007 adds nullable GST State-code support but does not fabricate or seed statutory mappings. The version-controlled reference-data process owns those values.
- Company has no direct Country Subdivision relationship. A later approved Company Location design may consume this master.
- City remains Location address text. City, District, postal-code, and generic address-hierarchy masters are excluded.

---

## 3. `entity_types` — KEEP

**What data is stored**
- Shared, platform-managed canonical reference data for a Company's primary legal form within an applicable jurisdiction.
- Examples include Private Limited Company, Public Limited Company, One Person Company, Limited Liability Partnership, and Partnership Firm. The complete India legal-form matrix is not frozen here; Section 8 and Foreign Company classification remain open for separate legal/company-identity review.

**Columns**
- `id` UUID PRIMARY KEY DEFAULT `gen_random_uuid()`
- `country_code` VARCHAR(2) NOT NULL
- `code` VARCHAR(50) NOT NULL
- `name` VARCHAR(150) NOT NULL
- `status` VARCHAR(20) NOT NULL

The Country master is now approved and implemented separately. Migration 004 deliberately does not retrofit this existing column with a Country FK; the reference catalogue must first cover and audit all existing values.

**Column meanings and reasons**

- `id` is the stable relational identity of the legal form. Display names may change, but Company and future rule relationships continue to reference the same UUID rather than using code or name as a primary key. PostgreSQL generates it with `gen_random_uuid()` unless a legitimate explicit UUID is supplied.
- `country_code` identifies the country/legal jurisdiction in which the form applies. It is exactly two uppercase ASCII letters. Legal-form identity and code uniqueness are jurisdiction-scoped; the later Country FK retrofit remains pending reference-data provisioning and value audit.
- `code` is the stable, platform-controlled machine identity, such as `PRIVATE_LIMITED`, `PUBLIC_LIMITED`, `OPC`, `LLP`, or `PARTNERSHIP`. It is not entered by normal Company users and should remain stable after use; changing the display name does not require changing the code.
- `name` is the human-readable UI label, such as `Private Limited Company`. It is display text rather than relational or machine identity, is required, and cannot be blank. It is not unique; display-name curation remains a platform-administration responsibility.
- `status` controls reference availability. It is stored as `VARCHAR(20)` with a CHECK allowing only `ACTIVE` (normally selectable for new/current Company configuration) and `INACTIVE` (retained historically but not normally selectable for new setup). `SUSPENDED` and `DELETED` are not normal states. There is no database default.

**Canonical identity and code rules**

```text
id   = stable UUID database identity
code = stable platform-controlled machine code
name = human-readable display label
```

Codes use uppercase letters, numbers, and underscores only, with no spaces and underscores between words. For example, `PRIVATE_LIMITED`, `PUBLIC_LIMITED`, and `LLP` are structurally valid; `private_limited`, `Private Limited`, and `Pvt Ltd` are invalid. The database enforces the approved canonical format through the named PostgreSQL regular-expression CHECK below.

Companies store `companies.entity_type_id` → `entity_types.id`; they do not store uncontrolled legal-form text such as `Pvt Ltd` as identity.

**Relationships**
- Entity Type 1:N Companies through `companies.entity_type_id` FK → `entity_types.id`.
- The selected Entity Type jurisdiction must be compatible with the Company's applicable country/jurisdiction. Exact Company/Country enforcement mechanics remain for the separate `companies` and Country-master reviews.

**Why this table exists**
1. Legal entity type is reusable reference data rather than free text on every Company.
2. It prevents spelling and capitalization variants from creating different legal-form meanings.
3. It supplies stable identity for Company legal-form selection and supports filtering/reporting by legal form.
4. It allows platform administrators to add supported legal forms as jurisdictions expand without changing the `companies` schema.
5. It can later drive applicable legal-identifier rules and UI behavior without hardcoding every form in frontend/backend code.
6. Removing it would allow uncontrolled Company text or force legal forms into application constants.

**Platform ownership and UI behavior**

`entity_types` is shared platform-managed reference data, not Tenant-owned. It has no `tenant_id`. Normal Company/Tenant users may select an allowed active Entity Type through a controlled dropdown/search selector but may not create arbitrary legal forms. Search text such as `pvt ltd`, `Pvt Ltd`, or `private limited` never becomes a new master row; the saved value is `entity_type_id`.

When another jurisdiction is supported, platform reference-data administration may add its approved legal forms without adding columns to `companies`.

**Legal-identifier and import boundaries**

Entity Type determines applicable Company legal-identifier inputs through `entity_type_identifier_rules`. Do not add country-specific flags such as `requires_pan`, `requires_cin`, `requires_llpin`, `requires_uen`, or `requires_ein` to `entity_types`. The generic rule architecture is approved below; the full statutory matrix and identifier-specific format/normalization rules remain open for dedicated legal validation.

Import text variants such as `Pvt Ltd`, `PVT. LTD.`, `Private Ltd`, and `Private Limited` should eventually resolve to the canonical `PRIVATE_LIMITED` identity rather than create duplicates. Alias/normalization support belongs to the future Import framework; no `entity_type_aliases` table is approved now.

**Constraints and indexing**

- PRIMARY KEY: `id`.
- NOT NULL: `id`, `country_code`, `code`, `name`, and `status`.
- UNIQUE `uq_entity_types_country_code_code`: (`country_code`, `code`); code is not globally unique.
- CHECK `ck_entity_types_country_code_format`: `country_code ~ '^[A-Z]{2}$'`.
- CHECK `ck_entity_types_code_not_blank`: `btrim(code) <> ''`.
- CHECK `ck_entity_types_code_format`: `code ~ '^[A-Z0-9]+(?:_[A-Z0-9]+)*$'`.
- CHECK `ck_entity_types_name_not_blank`: `btrim(name) <> ''`.
- CHECK `ck_entity_types_status`: `status IN ('ACTIVE', 'INACTIVE')`.
- The primary-key and unique constraints provide their corresponding indexes. Do not add speculative indexes without a demonstrated query requirement.
- Do not add a name index, status index, RLS, delete trigger, or cascade behavior. Once referenced by Companies, an Entity Type is inactivated rather than normally hard-deleted; future Company FKs are restrictive/no-action unless later requirements change this rule. Its UUID and canonical code remain stable, while its display name may be legitimately corrected without changing identity.
- No `created_at` or `updated_at` columns are part of this table.

**What does not belong in `entity_types`**

Do not store `tenant_id`, `company_id`, PAN, CIN, LLPIN, GSTIN, legal address, tax configuration, accounting configuration, bank configuration, country-specific identifier booleans, or arbitrary JSON rule data here. Keep this as a small stable reference master.

---

## 3A. `company_identifier_types` — KEEP

**What data is stored**
- Shared, platform-managed reference identities for jurisdiction-specific Company legal identifier types, such as PAN, CIN, LLPIN, and future UEN-like identifiers.

**Columns**
- `id` UUID PRIMARY KEY DEFAULT `gen_random_uuid()`
- mandatory jurisdiction reference — exact physical representation remains OPEN for this table
- `code` VARCHAR(50) NOT NULL
- `name` VARCHAR(150) NOT NULL
- `status` controlled value NOT NULL

**Column meanings and reasons**

- `id` is the stable identity referenced by Company values and Entity-Type applicability rules. Code and name are not relational primary keys.
- The mandatory jurisdiction reference identifies where the identifier type applies. The approved business rule is mandatory jurisdiction; physical `country_id` versus `country_code` remains open for this table. The direct `country_code` approved for `entity_types` does not silently resolve this separate contract.
- `code` is the stable, platform-controlled machine identity, such as `PAN`, `CIN`, `LLPIN`, or `UEN`. It uses uppercase letters, numbers, and underscores only, cannot be blank, and remains stable after use.
- `name` is the human-readable label, such as `Permanent Account Number` or `Unique Entity Number`. It may be corrected without changing UUID or code and cannot be blank.
- `status` is `ACTIVE` when normally available for applicable Company configuration and `INACTIVE` when retained historically but not normally offered for new use.

**Relationships and constraints**

- Identifier Type 1:N Company Identifiers.
- Identifier Type 1:N Entity Type Identifier Rules.
- PRIMARY KEY: `id`.
- NOT NULL: `id`, mandatory jurisdiction reference, `code`, `name`, and `status`.
- UNIQUE: (jurisdiction reference, `code`).
- Controlled `status`: `ACTIVE` or `INACTIVE`.
- Blank code/name is rejected; canonical code-format validation belongs in database/backend implementation.
- Used Identifier Types are inactivated rather than normally hard-deleted.

**Why this table exists**

It separates what a legal identifier type is from the value a Company has and from the Entity Types to which it applies. This prevents application constants and avoids adding a new Company column for every jurisdiction-specific identifier.

**Platform boundary**

This is shared reference data and has no `tenant_id`. Normal Tenant/Company users cannot create or change identifier types. Do not add speculative format columns such as regex, length, validation script, or JSON rules; identifier-specific formatting and normalization remain open.

---

## 3B. `company_identifiers` — KEEP

**What data is stored**
- The actual jurisdiction-specific legal identifier values belonging to a Company.

**Columns**
- `id` UUID PRIMARY KEY DEFAULT `gen_random_uuid()`
- `company_id` UUID NOT NULL FK → `companies.id` with restrictive/no-action deletion
- `identifier_type_id` UUID NOT NULL FK → `company_identifier_types.id`
- `identifier_value` VARCHAR(255) NOT NULL
- `status` controlled value NOT NULL
- `created_at` TIMESTAMPTZ NOT NULL DEFAULT `CURRENT_TIMESTAMP`
- `updated_at` TIMESTAMPTZ NOT NULL DEFAULT `CURRENT_TIMESTAMP`

**Column meanings and reasons**

- `id` is the stable identity of the Company-Identifier record.
- `company_id` identifies the Company that owns the value and establishes Company 1:N Company Identifiers.
- `identifier_type_id` identifies what the value means; meaning is never inferred from identifier text.
- `identifier_value` stores the actual Company value in a jurisdiction-neutral field. PAN/CIN/LLPIN-specific physical columns and universal format logic do not belong here.
- `status` is `ACTIVE` for the current usable value and `INACTIVE` when retained rather than silently deleted.
- `created_at` and `updated_at` record current-row timestamps only; they do not provide actor attribution, reason, or full version history.

**Relationships and constraints**

- Company 1:N Company Identifiers.
- Identifier Type 1:N Company Identifiers.
- PRIMARY KEY: `id`.
- FOREIGN KEY: `company_id` → `companies.id`.
- FOREIGN KEY: `identifier_type_id` → `company_identifier_types.id`.
- NOT NULL: `id`, `company_id`, `identifier_type_id`, `identifier_value`, `status`, `created_at`, and `updated_at`.
- UNIQUE: (`company_id`, `identifier_type_id`) under the approved current assumption of one current value of a given type per Company.
- Controlled `status`: `ACTIVE` or `INACTIVE`.
- Do not impose universal uniqueness on `identifier_value` or (`identifier_type_id`, `identifier_value`); statutory scope and normalization remain identifier-specific open decisions.

**Why this table exists**

It keeps stable Company identity separate from a variable set of legal identifiers and avoids a wide sparse `companies` table with PAN, CIN, LLPIN, UEN, EIN, ABN, CRN, and future jurisdiction-specific columns.

Company legal-identifier changes must eventually participate in Company profile/version history where appropriate. Exact versioning remains open; actor/change/reason evidence belongs to generic Audit architecture. No `company_identifier_logs` table is approved here.

GSTIN remains in GST Registration architecture and is not moved into this generic Company legal-identifier structure.

---

## 3C. `entity_type_identifier_rules` — KEEP

**What data is stored**
- Platform-controlled applicability rules describing which legal Identifier Types are REQUIRED or OPTIONAL for an Entity Type.

**Columns**
- `id` UUID PRIMARY KEY
- `entity_type_id` UUID NOT NULL FK → `entity_types.id`
- `identifier_type_id` UUID NOT NULL FK → `company_identifier_types.id`
- `requirement_level` controlled value NOT NULL
- `created_at` TIMESTAMPTZ NOT NULL DEFAULT `CURRENT_TIMESTAMP`
- `updated_at` TIMESTAMPTZ NOT NULL DEFAULT `CURRENT_TIMESTAMP`

**Column meanings and reasons**

- `id` is the stable rule-row identity.
- `entity_type_id` identifies the legal form whose Company setup is being governed.
- `identifier_type_id` identifies the legal identifier input to show and validate.
- `requirement_level` is `REQUIRED` or `OPTIONAL`. No row means the identifier is not part of the normal Company Identity UI for that Entity Type; no `NOT_APPLICABLE` rows are stored.
- `created_at` and `updated_at` are current-row timestamps, not complete audit history.

**Relationships and constraints**

- Entity Type 1:N Identifier Rules.
- Identifier Type 1:N Entity Type Rules.
- PRIMARY KEY: `id`.
- FOREIGN KEY: `entity_type_id` → `entity_types.id`.
- FOREIGN KEY: `identifier_type_id` → `company_identifier_types.id`.
- NOT NULL: `id`, `entity_type_id`, `identifier_type_id`, `requirement_level`, `created_at`, and `updated_at`.
- UNIQUE: (`entity_type_id`, `identifier_type_id`).
- Controlled `requirement_level`: `REQUIRED` or `OPTIONAL`.
- Entity Type and Identifier Type must have compatible jurisdictions. Database/backend enforcement is required eventually; exact enforcement remains open until the Country/jurisdiction representation is frozen.

**Why this table exists**

It separates legal-form applicability from Identifier Type identity and Company-entered values. The UI and backend can consume one canonical rule source instead of maintaining conflicting hardcoded matrices.

**Company setup use**

```text
Company country
→ Entity Type
→ resolve Entity Type Identifier Rules
→ show applicable identifier inputs
→ require REQUIRED values and allow OPTIONAL values
→ store Company-entered values in company_identifiers
```

Platform/system administration owns these applicability rules. Normal Tenant/Company users provide their Company's values but cannot change the statutory rule definitions. Illustrative PAN/CIN/LLPIN examples do not freeze the complete India statutory matrix.

---

## 4. `companies` — KEEP

**What data is stored**
- Stable current legal/business identity and single-value Company-wide defaults shared across AR and future AP/Accounting. Company is the legal, seller/billing, tax-registration-owner, and accounting boundary; it is neither the SaaS Tenant nor an Organisation grouping.

**Columns**
- `id` UUID PRIMARY KEY DEFAULT `gen_random_uuid()`
- `tenant_id` UUID NOT NULL FK → `tenants.id` ON DELETE NO ACTION
- `organisation_id` UUID NULL
- `legal_name` VARCHAR(255) NOT NULL
- `display_name` VARCHAR(200) NULL
- `company_code` VARCHAR(50) NOT NULL UNIQUE DEFAULT `core.next_company_code()`
- `entity_type_id` UUID NULL FK → `entity_types.id` ON DELETE NO ACTION
- `country_code` VARCHAR(2) NULL
- `email` VARCHAR(320) NULL
- `phone` VARCHAR(32) NULL
- `website` VARCHAR(2048) NULL
- `base_timezone` VARCHAR(64) NULL
- `base_currency_code` VARCHAR(3) NULL FK → `currencies.code` ON DELETE NO ACTION
- `business_nature` VARCHAR(20) NULL
- `status` VARCHAR(20) NOT NULL
- `created_at` TIMESTAMPTZ NOT NULL DEFAULT `CURRENT_TIMESTAMP`
- `updated_at` TIMESTAMPTZ NOT NULL DEFAULT `CURRENT_TIMESTAMP`

**Column meanings and reasons**

- `id` is the stable Company identity reused by all modules. Name/code changes never change relational identity.
- `tenant_id` is the mandatory authoritative SaaS owner. Ownership is direct and is not inferred through Organisation.
- `organisation_id` is optional grouping only. A Company may exist without it; a composite FK with `tenant_id` ensures any referenced Organisation belongs to the same Tenant.
- `legal_name` is the current official Company-level legal name. It cannot be blank and is distinct from the legal name currently recorded against a specific GSTIN. Historical legal-name states are preserved through Company profile versions.
- `display_name` is an optional short/UI-facing name and is never statutory legal identity.
- `company_code` is the immutable normal-operation reference for search, reports, integrations, and operations. PostgreSQL generates globally unique `COM` plus a sequence number padded to at least six digits, starting with `COM000001`; gaps are accepted and values are never intentionally reused. It is not the primary key and normal onboarding does not accept a manually invented value.
- `entity_type_id` selects controlled legal-form reference data. It may be null while the Company is `DRAFT`, but activation requires a jurisdiction-compatible value. The ordinary FK protects identity; compatibility with `country_code` is enforced transactionally by future Company business logic rather than a composite FK.
- `country_code` stores an uppercase two-letter Company jurisdiction. It may be null while `DRAFT` and becomes logically mandatory before activation. Migration 004 does not add its Country FK; catalogue provisioning and an audit of existing values must precede that retrofit.
- `email`, `phone`, and `website` are optional primary Company contact values. A separate contact model is not introduced without a multi-contact requirement.
- `base_timezone` supplies Company-local operational, scheduling, and reporting context; Tenant time zone is not a substitute.
- `base_currency_code` identifies the Company's base currency through the shared Currency master. Reporting and AR permissions remain separate Company configurations.
- `business_nature` is functional configuration: `SERVICES` enables the Service catalogue path, `GOODS` enables Product/SKU setup, and `BOTH` enables both.
- `status` is `DRAFT`, `ACTIVE`, or `INACTIVE`, stored as `VARCHAR(20)` with no database default. Incomplete configuration may persist in `DRAFT`; future activation business logic owns the evolving completeness rules.
- `created_at` and `updated_at` are current-row timestamps only. PostgreSQL supplies insert defaults, the application owns later `updated_at` changes, and no update trigger is used.

**Relationships**
- Tenant 1:N Companies
- Organisation 1:N Companies (optional)
- Company 1:N Company Identifiers through `company_identifiers`
- Company 1:N GST Registrations, Locations, Bank Accounts, FYs, catalogues and AR configuration

**Legal identifier direction**

The earlier direct `pan`, `cin`, and `llpin` Company columns are REPLACED in the current design by `company_identifiers`. `companies.entity_type_id` remains. Entity Type/country compatibility is an application transaction invariant for the future activation service and does not add a redundant composite Entity Type key.

**Constraints and exclusions**

- PRIMARY KEY: `id`.
- FOREIGN KEY: direct `tenant_id` → `tenants.id`, optional `entity_type_id` → `entity_types.id`, and optional `base_currency_code` → `currencies.code`, all restrictive/no-action.
- COMPOSITE FOREIGN KEY: (`tenant_id`, `organisation_id`) → `organisations (tenant_id, id)`; a null Organisation remains valid.
- NOT NULL even in `DRAFT`: `id`, `tenant_id`, `legal_name`, generated `company_code`, `status`, `created_at`, and `updated_at`.
- NULL permitted while `DRAFT`: `organisation_id`, `entity_type_id`, `country_code`, `display_name`, contact fields, `base_timezone`, `base_currency_code`, and `business_nature`.
- UNIQUE: global `company_code`; `legal_name` and `display_name` are not unique.
- CHECK non-blank `legal_name`; each optional text value rejects blank/whitespace-only text when present.
- CHECK `company_code ~ '^COM[0-9]{6,}$'` and optional `country_code ~ '^[A-Z]{2}$'`.
- CHECK optional `business_nature IN ('SERVICES', 'GOODS', 'BOTH')`.
- CHECK `status IN ('DRAFT', 'ACTIVE', 'INACTIVE')`; there is no status default.
- INDEX (`tenant_id`, `organisation_id`) supports normal grouping lookup and the approved Tenant/Organisation relationship. Do not add status, legal-name, contact, or other speculative indexes.
- The database does not encode the full activation-readiness workflow. Before activation, Company business logic must require at least country, compatible Entity Type, valid IANA time zone, valid Base Currency, Business Nature, Registered Office, and other configuration owned elsewhere.
- Do not store PAN, CIN, LLPIN, GSTIN, Registered Office/other addresses, Bank Accounts, Financial Year instances, LUTs, HSN/SAC, CoA hierarchy, GL balances, numbering sequences, GST-registration State, or GST-registration-specific registered legal name directly on Company.
- Company branding remains Company configuration, but no blob/path column is invented without the approved file-storage pattern.

---

## 4A. `company_legal_name_versions` — KEEP

**What data is stored**
- Effective-dated legal names for one stable Company identity. `companies.legal_name` remains the current operational projection; this table is deliberately not a generic Company profile-version structure.

**Columns**
- `id` UUID PRIMARY KEY DEFAULT `gen_random_uuid()`
- `company_id` UUID NOT NULL FK → `companies.id`
- `legal_name` VARCHAR(255) NOT NULL
- `valid_from` DATE NOT NULL
- `valid_to` DATE NULL
- `created_at` TIMESTAMPTZ NOT NULL DEFAULT `CURRENT_TIMESTAMP`

**Physical constraints and lifecycle**
- CHECK non-blank `legal_name`.
- CHECK (`valid_to IS NULL OR valid_to >= valid_from`).
- Inclusive effective periods for one Company must not overlap; enforce Company plus `daterange(valid_from, valid_to, '[]')` with a GiST exclusion constraint.
- Partial UNIQUE (`company_id`) WHERE `valid_to IS NULL` permits at most one current/open version per Company.
- INDEX (`company_id`, `valid_from`) supports chronological and as-of reads.
- The Company FK uses restrictive/no-action deletion. History is not deleted or closed when a Company becomes inactive.
- Company creation atomically creates the initial open version. Migration backfill uses the existing Company's `legal_name`, `created_at::date` as the technical history start, and existing `created_at` as the version creation timestamp.
- A legal-name change atomically closes the current version on the day before the new immediate effective date, inserts the new open version, and updates `companies.legal_name`. A second transition on the same date is rejected because inclusive DATE periods cannot preserve both states safely. Future-dated scheduling is not part of MVP.
- Generic Audit separately answers who changed what, when, from/to, and why. Finalized invoices remain independently protected by their seller snapshots.

---

## 5. `gst_registration_types` — KEEP

**Purpose and scope**
- Shared GST-specific reference data used by Company GST Registrations. It is not the generic Tax Type/family master.

**Columns**
- `id` UUID PRIMARY KEY DEFAULT `gen_random_uuid()`
- `code` VARCHAR(50) NOT NULL
- `name` VARCHAR(100) NOT NULL
- `description` VARCHAR(500) NULL
- `status` VARCHAR(20) NOT NULL
- `created_at` TIMESTAMPTZ NOT NULL DEFAULT `CURRENT_TIMESTAMP`
- `updated_at` TIMESTAMPTZ NOT NULL DEFAULT `CURRENT_TIMESTAMP`

**Constraints, lifecycle, and relationships**
- UNIQUE (`code`).
- `status` is controlled as `ACTIVE` or `INACTIVE`.
- `code` is the stable, canonical system-facing identity; `name` is the required display label and `description` is optional explanatory metadata.
- No business defaults are defined. PostgreSQL supplies only the UUID and timestamp infrastructure defaults.
- Registration Type 1:N Company GST Registrations through `company_gst_registrations.gst_registration_type_id`.
- Referenced types are retired/inactivated rather than deleted.
- Exact supported GST Registration Type values remain subject to statutory reference-data review; no list is invented here.
- Do not store generic tax-family, rate, HSN/SAC, treatment, statutory-section, or transaction data here.

**Why this table exists**
1. It gives the retained GST Registration Type FK a stable identity rather than free text.
2. It separates GST-registration classification from generic Tax Types.
3. It supports controlled display and validation without changing registration schema for each category.

**Decision status:** KEEP — approved GST-specific reference table.

---

## 6. `company_gst_registrations` — KEEP

**What data is stored**
- Seller Company's GST registration identities and their current validity/status.

**Columns**
- `id` UUID PRIMARY KEY DEFAULT `gen_random_uuid()`
- `company_id` UUID NOT NULL FK → `companies.id` ON DELETE NO ACTION
- `gstin` VARCHAR(15) NOT NULL
- `registered_legal_name` VARCHAR(255) nullable
- `gst_registration_type_id` UUID nullable FK → `gst_registration_types.id` ON DELETE NO ACTION
- `subdivision_code` VARCHAR(10) NOT NULL FK → `country_subdivisions.code` ON DELETE NO ACTION
- `valid_from` DATE nullable
- `valid_to` DATE nullable
- `status` VARCHAR(20) NOT NULL with no database default (`DRAFT`, `ACTIVE`, `INACTIVE`)
- `created_at` TIMESTAMPTZ NOT NULL DEFAULT `CURRENT_TIMESTAMP`
- `updated_at` TIMESTAMPTZ NOT NULL DEFAULT `CURRENT_TIMESTAMP`

**Column meanings and reasons**

- `id` is the stable registration identity referenced by Locations, LUTs, and other relationships rather than GSTIN text.
- `company_id` identifies the owning legal Company; no GST Registration exists without a Company.
- `gstin` is the statutory number. Store trimmed canonical uppercase text, require the structural pattern `^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$`, and enforce `UNIQUE (gstin)` across the ERP because one GSTIN cannot belong simultaneously to two Company masters. Checksum validation is deferred.
- `registered_legal_name` is the current legal name recorded against this specific GSTIN. It is distinct from the current Company-master legal name and may temporarily differ during statutory amendment.
- `gst_registration_type_id` retains the controlled GST Registration Type reference and may be null while `DRAFT`. Activation readiness will later require an applicable active type.
- `subdivision_code` records the mandatory shared Indian State/UT jurisdiction. Creation requires an active `IN` Subdivision with a provisioned `gst_state_code`, and the first two GSTIN digits must match that code.
- `valid_from` is the optional known applicable start date; earlier transactions cannot use the registration.
- `valid_to` is the optional end date. When both dates exist, `valid_to >= valid_from`.
- `status` is required and follows the current configuration lifecycle `DRAFT` → `ACTIVE` → `INACTIVE`. New registrations are created as `DRAFT`; transition endpoints are outside this foundation.
- `created_at` and `updated_at` are current-row timestamps only, not statutory history or Audit attribution.

**Relationships**
- Company 1:N GST Registrations
- GST Registration 1:N Company Locations under the current MVP relationship
- GST Registration 1:N LUTs over time/FYs

`companies.legal_name` is the current Company-level legal name. `company_gst_registrations.registered_legal_name` is the current legal name recorded against one GSTIN. They normally match but may differ during amendment; a Company-name change must not automatically overwrite every GST Registration name.

**Constraints and lifecycle**

- PRIMARY KEY: `id`.
- FOREIGN KEY: `company_id` → `companies.id`.
- FOREIGN KEY: nullable `gst_registration_type_id` → `gst_registration_types.id` and `subdivision_code` → `country_subdivisions.code`.
- NOT NULL: `id`, `company_id`, `gstin`, `subdivision_code`, `status`, `created_at`, and `updated_at`.
- UNIQUE: `gstin`; do not weaken this to only (`company_id`, `gstin`).
- Partial UNIQUE (`company_id`, `subdivision_code`) WHERE `status = 'ACTIVE'` prevents concurrent creation or activation of two active registrations for one Company and State/UT while allowing drafts and retained inactive history.
- CHECK the approved GSTIN structural pattern, optional non-blank registered legal name, date ordering, and exact lifecycle values.
- `valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from`.
- Service creation requires Tenant-safe Company resolution, `companies.country_code = 'IN'`, an active/provisioned Indian Subdivision, GSTIN-prefix compatibility, and an active Registration Type when one is supplied.
- Used registrations are not casually hard-deleted; validity, status, and version history preserve statutory references.
- Do not add a global GST Registration `is_default`. Seller GSTIN follows seller Location and transaction context.
- Do not store Company/Location address, PAN, Bank Account, LUT details, tax rates, numbering, invoice templates, or ad-hoc attachment paths here.

**Approved Excel-import behavior**

- GSTIN is the business-facing import identity. The `GST Registrations` sheet creates new `DRAFT` rows or recognizes an equivalent existing row as unchanged; it never updates an existing registration. Duplicate normalized GSTIN rows are invalid.
- Registered Legal Name remains registration-specific and is not defaulted from Company Legal Name.
- Registration Type is supplied by stable active `gst_registration_types.code`, not UUID. Subdivision uses the controlled code and existing India/GST-prefix validation.
- `GST Location Mappings` resolves GSTIN plus Company-scoped immutable Location Code and persists through `company_locations.gst_registration_id`; no mapping table is added.
- Mapping import is additive-only: omission does not unmap, and an existing different association is not reassigned. `DRAFT` or `ACTIVE` registrations may receive a new assignment; `INACTIVE` registrations may retain an existing association but cannot receive a new/change assignment.
- Same-workbook Location mapping requires an explicitly supplied Location Code; generated Location Codes are not predicted during preview.

**Why this table exists**
1. A Company can have multiple GST registrations across states.
2. GST identity is statutory and should not be duplicated on every Location row as text.
3. Billing must explicitly select/resolve the seller GSTIN where applicable.
4. LUT validation is GSTIN-specific, so a stable GST Registration ID is required.
5. Registration status/validity can change while historical invoices retain the old GSTIN snapshot.
6. Removing it would mix statutory registration identity with physical Location data and create duplication.

---

## 6A. `company_gst_registration_versions` — REVIEW

**What data would be stored**
- Historically applicable states of one stable GST Registration when registered legal name, registration type, jurisdiction, validity/status-relevant metadata, or other approved registration details change.

**Minimum conceptual fields**
- stable GST Registration FK → `company_gst_registrations.id`
- historical `registered_legal_name`
- effective/version validity dates
- version creation timestamp

**Current decision**

Keep the history concept under REVIEW until the complete versioned-field set and constraints are approved. Company profile history is not a substitute for GST Registration history. Generic Audit remains separate from effective-state versioning.

Finalized invoices preserve the actual seller legal name, GSTIN, seller address, and GST-registration context used at finalization. Later Company or GST Registration changes never dynamically rewrite those snapshots.

---

## 7. `company_locations` — KEEP

**What data is stored**
- One stable physical/business Location belonging to a Company, including its current usable address/configuration state and fixed Location purposes. The nullable GST Registration relationship is active from Migration 007 and the nullable Location Cost Center relationship is active from Migration 0010; default-GSTIN behavior remains a future extension.

**Columns**
- `id` UUID PRIMARY KEY
- `company_id` UUID NOT NULL FK → `companies.id`
- `location_code` VARCHAR(50) NOT NULL
- `location_name` VARCHAR(150) NOT NULL
- `address_line_1` VARCHAR(255) NOT NULL
- `address_line_2` VARCHAR(255) nullable
- `city` VARCHAR(100) NOT NULL
- `district` VARCHAR(100) nullable
- `subdivision_code` VARCHAR(10) nullable; composite FK with `country_code` → `country_subdivisions(country_code, code)`
- `country_code` VARCHAR(2) NOT NULL FK → `countries.code`
- `gst_registration_id` UUID nullable; composite FK with `company_id` and `subdivision_code` → `company_gst_registrations(company_id, id, subdivision_code)`
- `cost_center_location_id` UUID nullable; composite FK with `company_id` → `cost_center_locations(company_id, id)`
- `postal_code` VARCHAR(20) nullable
- `is_registered_office` BOOLEAN NOT NULL DEFAULT false
- `is_corporate_office` BOOLEAN NOT NULL DEFAULT false
- `is_branch` BOOLEAN NOT NULL DEFAULT false
- `is_billing_office` BOOLEAN NOT NULL DEFAULT false
- `is_warehouse` BOOLEAN NOT NULL DEFAULT false
- `other_purpose` VARCHAR(150) nullable
- `status` VARCHAR(20) NOT NULL with no database default (`ACTIVE`, `INACTIVE` for the current lifecycle)
- `created_at` TIMESTAMPTZ NOT NULL DEFAULT `CURRENT_TIMESTAMP`
- `updated_at` TIMESTAMPTZ NOT NULL DEFAULT `CURRENT_TIMESTAMP`

Migration 005 initially omitted `gst_registration_id`, `is_default_for_gstin`, and `cost_center_location_id`. Migration 007 adds the nullable `gst_registration_id` with complete same-Company and jurisdiction protection. Migration 0010 adds the nullable `cost_center_location_id` with same-Company protection. Default-GSTIN/default-Location behavior and `is_default_for_gstin` remain deferred.

`location_code` is the stable Company-scoped business/reference identity approved for Excel re-import, integrations, and rename-safe lookup. It is normalized to uppercase, matches `^[A-Z0-9][A-Z0-9_-]{0,49}$`, and is protected by `UNIQUE (company_id, location_code)`. When omitted, a Company-scoped concurrency-safe counter generates `LOC-0001`, `LOC-0002`, and later values. It is immutable, remains assigned after inactivation, and is never used in place of the UUID for relational foreign keys.

**Column meanings and reasons**

- `id` is the stable identity. The same logical Location can retain its UUID when its physical address changes.
- `company_id` is the mandatory owner; a Location cannot exist without a Company.
- `location_code` is the immutable, Company-scoped business/reference identity. `location_name` remains the mutable human-readable label and need not be unique.
- `gst_registration_id` allows one GST Registration to serve many Locations while a Location may exist without GST registration; no M:N bridge is required.
- Future `is_default_for_gstin` behavior will mark the active mapped Location offered as the preselection for a GSTIN without removing explicit transaction-level Location selection.
- `cost_center_location_id` optionally rolls several physical Locations into one same-Company Location Cost Center/reporting bucket. A Location does not automatically become a Cost Center.
- `location_name` is the required, non-blank human-readable business identity, such as `Noida Registered Office` or `Mumbai Branch`.
- The address fields hold the current usable physical address. A usable Location must contain the components required by its jurisdiction; the design does not impose one worldwide address format.
- The fixed purpose flags allow one physical Location to serve several purposes simultaneously without duplicate Location rows or a generic purpose-mapping engine.
- `other_purpose`, when populated, records an uncommon additional purpose without a redundant `is_other` flag.
- `status` controls the current lifecycle. Historically used Locations are inactivated rather than normally hard-deleted; `SUSPENDED` is not introduced without a business requirement.
- `created_at` and `updated_at` describe the current row. They do not replace effective address history or generic Audit evidence.

**Relationships**
- Company 1:N Locations
- Country 1:N Locations
- Country Subdivision 1:N Locations (nullable from Location side and compatible with the selected Country)
- GST Registration 1:N Locations (nullable from Location side)
- Future Location Cost Center 1:N Locations (nullable from Location side)

**Why this table exists**
1. A Company can operate from multiple physical/business places.
2. One Location can serve several fixed purposes without duplicating the same address.
3. Seller Location must be explicitly available to Billing, Place-of-Supply and document output.
4. Direct GST Registration FK implements the current 1:N model without an unnecessary M:N mapping table.
5. `is_default_for_gstin` supports one preselected active Location for a GSTIN while retaining explicit transaction selection.
6. Direct Location Cost Center FK supports grouping several Locations into one reporting bucket; removing this table would break multi-location behavior.

**Important current rules**
- At most one active Location per Company may have `is_registered_office = true`, using an appropriate partial uniqueness constraint/index. A completed/usable Company must have exactly one active Registered Office; the at-least-one rule belongs to setup/activation validation so incomplete drafts are not prematurely blocked.
- Every Location must have at least one fixed purpose or a non-blank `other_purpose`; this is enforced in request validation and by a database CHECK.
- `country_code` is mandatory. `subdivision_code` is optional, but when supplied the composite FK `(country_code, subdivision_code)` guarantees that the Subdivision belongs to the selected Country. `country_subdivisions(country_code, code)` has the minimum supporting uniqueness constraint; the existing global uniqueness of complete Subdivision `code` remains unchanged.
- A linked GST Registration must belong to the same Company and use the same non-null `subdivision_code` as the Location. Migration 007 enforces both through one composite FK and a linked-Location subdivision CHECK. Future Location Cost Center ownership must likewise be database-protected when implemented.
- Default-GSTIN/default-Location behavior and `is_default_for_gstin` remain deferred; no Company-global default GSTIN is introduced.
- A mapped Location's State/UT jurisdiction must match its GST Registration. Frontend filtering may assist selection, but the composite PostgreSQL FK is authoritative protection.
- Historically used Locations are deactivated rather than deleted.
- Location Code cannot be changed or reused for another Location, including after inactivation. Its UUID remains the relational key.
- Do not store duplicated GSTIN text, LUT details, Company PAN/CIN/LLPIN, Bank Accounts, tax rates, document sequences, CoA, invoice templates, or ad-hoc attachment paths on this table.

---

## 8. `company_location_versions` — KEEP

**What data is stored**
- The complete effective-dated physical address/jurisdiction timeline for one stable Company Location, including the currently applicable open-ended version.

**Columns**
- `id` UUID PRIMARY KEY DEFAULT `gen_random_uuid()`
- `company_location_id` UUID NOT NULL FK → `company_locations.id` ON DELETE NO ACTION
- `address_line_1` VARCHAR(255) NOT NULL
- `address_line_2` VARCHAR(255) nullable
- `city` VARCHAR(100) NOT NULL
- `district` VARCHAR(100) nullable
- `subdivision_code` VARCHAR(10) nullable; composite FK with `country_code` → `country_subdivisions(country_code, code)` ON DELETE NO ACTION
- `country_code` VARCHAR(2) NOT NULL FK → `countries.code` ON DELETE NO ACTION
- `postal_code` VARCHAR(20) nullable
- `valid_from` DATE NOT NULL
- `valid_to` DATE nullable
- `created_at` TIMESTAMPTZ NOT NULL DEFAULT `CURRENT_TIMESTAMP`

**Relationships**
- Company Location 1:N Location Versions

**Why this table exists**
1. A legal/business Location can move while remaining the same logical Location.
2. Address history is retained when the current operational address changes.
3. Historical processes can resolve the address/jurisdiction effective on a date.
4. Regulatory/master-data history can be useful independently of finalized invoices.
5. Finalized invoices still preserve their own exact transaction-time seller/location snapshots.

**Scope and constraints**

- Version only physical address/jurisdiction state. Do not automatically version `location_name`, `gst_registration_id`, `cost_center_location_id`, `is_default_for_gstin`, the five fixed purpose flags, `other_purpose`, or `status`.
- This table does not answer which GST Registration, Cost Center, or purpose mapping applied on a historical date. Any future effective-dated GST mapping requirement needs a separate approved design.
- `company_locations` stores the fast/current operational address; this table stores the complete effective timeline, including at most one open-ended current version. A later implementation must update the applicable master state and timeline consistently/atomically.
- `valid_to` is null or greater than or equal to `valid_from`.
- Effective date ranges for the same `company_location_id` must not overlap. PostgreSQL enforces this with a GiST exclusion constraint over inclusive date ranges.
- A partial unique index permits at most one open-ended version per `company_location_id`.
- The Location FK and Country/Subdivision FKs are restrictive. Version ownership follows the stable Location and the composite geography FK preserves the existing Country/Subdivision representation.
- New Locations receive one open version whose `valid_from` is the application business date. Existing Locations are technically backfilled from `company_locations.created_at::date`; this is not evidence of an earlier legal/historical effective date.
- Normal address edits are immediately effective: atomically close the open version on the preceding date, create the new open version, and update the current Location projection. No-op or non-address changes create no version.
- Future-dated scheduling and backdated correction workflows are outside the MVP.
- Location lifecycle is terminal `ACTIVE` -> `INACTIVE`; inactive Locations remain readable but cannot be reactivated, edited, or reassigned.
- Finalized documents are never rebuilt from current Location or Location Version rows. Location history is master-data truth over time; the document snapshot is exact transaction-time truth.

---

## 9. `company_fiscal_settings` — KEEP

**What data is stored**
- The Company's one current recurring rule for the month/day on which its normal Financial Year begins. It is a pattern/template, not an actual Financial Year instance.

**Columns**
- `company_id` UUID PRIMARY KEY and FK → `companies.id`
- `fiscal_year_pattern` VARCHAR(20) NOT NULL (`APR_MAR`, `JAN_DEC`, `CUSTOM`)
- `start_month` SMALLINT NOT NULL
- `start_day` SMALLINT NOT NULL
- `created_at` TIMESTAMPTZ NOT NULL DEFAULT `CURRENT_TIMESTAMP`
- `updated_at` TIMESTAMPTZ NOT NULL DEFAULT `CURRENT_TIMESTAMP`

**Column meanings and constraints**

- `company_id` is both PK and FK because the approved relationship is Company 1:1 Fiscal Settings. A separate surrogate UUID adds no current value.
- `fiscal_year_pattern` retains the configured typed pattern. `APR_MAR` requires month/day `4/1`; `JAN_DEC` requires `1/1`; `CUSTOM` uses the stored configurable month/day.
- `start_month` is the normal fiscal-year starting month and must be between 1 and 12.
- `start_day` is the normal starting day. The month/day combination must exist in every non-leap calendar year: February 29 and impossible dates such as April 31 are rejected by database CHECK and request validation.
- `created_at` and `updated_at` record current-row timestamps.
- Do not store `end_month` or `end_day`. A normal period ends one day before the next normal start; actual exceptions belong in `financial_years`.
- Do not store `current_financial_year_id`, `is_current`, `is_closed`, `is_locked`, or `status`. This table does not represent actual FY instances, accounting close, period locks, or current-period state.

**Relationships**
- Company 1:1 Fiscal Settings
- Used to generate/propose 1:N `financial_years`

**Why this table exists**
1. Different Companies can follow Apr–Mar, Jan–Dec or another permitted fiscal cycle.
2. The recurring rule should not be repeated on every `financial_years` row.
3. It allows the next FY to be generated automatically from a stable pattern.
4. It provides a source for setup UI without deriving the pattern from old FY rows.
5. It separates recurring calendar policy from actual period records.
6. Removing it would make automatic future-year generation depend on guessing from previous periods.

**Automatic FY behavior**
- Fiscal settings usually stay unchanged year to year.
- Before the current FY ends, or when a transaction date has no FY, the system can calculate and propose/create the next FY.
- Changing fiscal settings affects only future FY generation/proposals and never rewrites existing `financial_years`; actual historical FY rows remain authoritative.
- Creating the next FY does **not** close or lock the previous FY, prevent transactions in it, or change accounting-period state. Multiple non-overlapping FY records may validly coexist.

---

## 10. `financial_years` — KEEP

**What data is stored**
- Actual dated Financial Year instances for each Company. Their stored dates are authoritative and are not later re-derived from current fiscal settings.

**Columns**
- `id` UUID PRIMARY KEY DEFAULT `gen_random_uuid()`
- `company_id` UUID NOT NULL FK → `companies.id`
- `start_date` DATE NOT NULL
- `end_date` DATE NOT NULL
- `display_code` VARCHAR(30) NOT NULL
- `is_transition` BOOLEAN NOT NULL DEFAULT false
- `status` VARCHAR(20) NOT NULL with no database default (`DRAFT`, `OPEN`, `CLOSED`)
- `created_at` TIMESTAMPTZ NOT NULL DEFAULT `CURRENT_TIMESTAMP`
- `updated_at` TIMESTAMPTZ NOT NULL DEFAULT `CURRENT_TIMESTAMP`

**Column meanings and constraints**

- `id` is the stable identity referenced by LUTs, document sequences, applicable financial documents, and future Accounting records. `display_code` is never used as a relational key.
- `company_id` is the mandatory owner; the relationship is Company 1:N Financial Years.
- `start_date` and `end_date` are the actual authoritative boundaries, with `end_date >= start_date`.
- For the same Company, Financial Year date ranges must not overlap. A PostgreSQL date-range/GiST exclusion constraint is an appropriate implementation direction.
- Gaps are not prohibited by an unconditional database constraint. A gap is a configuration/workflow issue: a transaction date must resolve to exactly one FY, otherwise the system may propose/create the expected FY or block until setup is completed according to later workflow rules.
- `display_code` is the required human-readable label and is unique per Company through `UNIQUE (company_id, display_code)`. Dates remain the source of truth, and different Companies may reuse the same label.
- `is_transition` explicitly preserves that an actual period is short/transitional. Do not infer this later by comparing historical dates with current fiscal settings.
- `status` uses the normal lifecycle `DRAFT` → `OPEN` → `CLOSED`. `FUTURE` is not stored; temporal position is derived from dates. Financial Year status remains separate from Accounting-period close/lock and from invoice/receivable settlement state.
- `created_at` and `updated_at` record current-row timestamps.
- Do not add `is_current`, `is_closed`, or `is_locked`. Applicable FY is resolved from the transaction date; close/lock belongs to future Accounting-period design.
- Same-Company overlap is protected race-safely by a PostgreSQL GiST exclusion constraint over inclusive date ranges, using the standard `btree_gist` extension for Company UUID equality.

**Relationships**
- Company 1:N Financial Years
- Financial Year 1:N Company LUTs where applicable
- Financial Year 1:N Document Sequences where configured
- Financial documents may later reference the resolved FY

**Why this table exists**
1. Fiscal settings tell the pattern; this table gives the real period identity (`FY 2026-27`).
2. Short/transition years cannot be represented by only `start_month/start_day`.
3. Document numbering/reset needs a stable actual FY ID.
4. LUT is GSTIN + FY specific, so it needs a concrete FY reference.
5. Old invoices must remain attached to the same FY even if future fiscal settings change.
6. Transition periods need explicit dated identity rather than inference from the current normal pattern.

**Next-FY and historical-stability rules**

- Fiscal settings may calculate/propose the next expected normal FY before the current FY ends, when future configuration needs it, or when a transaction date lacks an applicable FY. Exact timing/UI remains an implementation detail.
- Creating a next FY is calendar/master-data setup. It does not close or lock the prior FY, prevent prior-FY transactions, or change accounting-period state.
- Once referenced historically, an actual FY's dates are not silently changed because the recurring fiscal pattern changes. Historical documents retain the same stable FY identity.
- Financial Year, accounting close, and accounting lock are separate concepts. Future Accounting may introduce accounting periods, closing state, lock state, and posting restrictions through its own design.
- Do not store Company tax configuration, GST Registration, LUT data, numbering rules, accounting balances, close/lock detail, arbitrary JSON settings, or a current-FY boolean in these tables.

---

## 11. `currencies` — KEEP

**What data is stored**
- Shared, platform-managed Currency reference such as INR, USD, EUR, GBP, JPY, AED and SGD. Normal Company users select supported currencies rather than creating arbitrary global definitions.

**Columns**
- `code` VARCHAR(3) PRIMARY KEY
- `name` VARCHAR(100) NOT NULL
- `symbol` VARCHAR(16) NULL
- `minor_units` SMALLINT NOT NULL
- `status` VARCHAR(20) NOT NULL
- `created_at` TIMESTAMPTZ NOT NULL
- `updated_at` TIMESTAMPTZ NOT NULL

**Column meanings and constraints**

- `code` is the canonical relational identity. It must contain exactly three uppercase alphabetic characters; `VARCHAR(3)` avoids PostgreSQL `CHAR` padding semantics. Standardized Currency codes are appropriate keys.
- `name` is the required, non-blank human-readable Currency name and is not relational identity.
- `symbol` is optional and is not unique because multiple currencies can share a symbol and displays need not use one.
- `minor_units` explicitly records normal decimal precision and must be between 0 and 4. It has no default because reference data must not silently assume two decimal places.
- `status` is `ACTIVE` or `INACTIVE` with no database default. Active rows are available for new configuration; historically used inactive currencies are retained rather than casually deleted.
- `created_at` and `updated_at` use PostgreSQL insert defaults. Application update paths own later `updated_at` changes; no update trigger is used.
- Do not add `tenant_id` or `company_id`; this is shared/platform-managed reference data.

**Physical constraints**

- PRIMARY KEY (`code`).
- CHECK canonical three-character uppercase alphabetic `code` format.
- CHECK non-blank `name`; when `symbol` is present it must not be blank/whitespace-only.
- CHECK (`minor_units BETWEEN 0 AND 4`).
- Controlled `status` values: `ACTIVE`, `INACTIVE`.
- No name/symbol/status indexes or other speculative indexes; only the primary-key index is required initially.
- No seed catalogue or reference-data loader is included in this migration.

**Relationships**
- Referenced by Company base currency, reporting currencies, AR currencies, bank accounts and FX rates

**Why this table exists**
1. Currency is shared reference data used across multiple modules.
2. It avoids inconsistent free-text currency names/codes.
3. Symbols/minor units can be maintained once.
4. Company-specific allowed currency tables can point to a controlled master.
5. Future AP/Accounting can reuse the same codes.
6. Removing it would duplicate currency metadata throughout the database.

---

## 12. `company_reporting_currencies` — KEEP

**What data is stored**
- Additional currencies in which a Company allows management/MIS reporting views. The Company's Base Currency remains on `companies` and is not duplicated here.

**Columns**
- `company_id` UUID NOT NULL FK → `companies.id`
- `currency_code` VARCHAR(3) NOT NULL FK → `currencies.code`
- `status` VARCHAR(20) NOT NULL
- `created_at` TIMESTAMPTZ NOT NULL
- `updated_at` TIMESTAMPTZ NOT NULL

**Column meanings and constraints**

- `company_id` identifies the Company that permits the additional reporting choice.
- `currency_code` identifies the shared Currency. Together with `company_id`, it is the natural row identity, so no surrogate UUID is added.
- `status` is `ACTIVE` or `INACTIVE`. Inactive rows retain configuration/history but are not normally offered for new reporting selection.
- `created_at` and `updated_at` record current-row timestamps.
- PRIMARY KEY (`company_id`, `currency_code`).
- The Company's own `companies.base_currency_code` must not be redundantly inserted as an additional Reporting Currency. Cross-table enforcement may remain backend/domain validation; no trigger is invented here.
- Do not store conversion/exchange rates, a default-reporting flag, transaction amounts, FX policy, Billing permission, or Receipt permission. Reporting conversion uses the separate FX architecture and does not alter original transaction/book values.

**Relationships**
- Company N:M Currency through this controlled list

**Why this table exists**
1. Base Currency and Reporting Currency have different meanings.
2. A Company can allow several reporting currencies simultaneously.
3. Dashboard users should only see configured choices rather than every currency in the master.
4. Changing reporting currency changes presentation, not original transaction/book values.
5. It gives FX setup a bounded list of relevant currencies.
6. Removing it would require either showing all currencies or hardcoding report choices.

---

## 13. `company_ar_currencies` — KEEP

**What data is stored**
- Currencies allowed specifically for AR Billing and/or Receipt.

**Columns**
- `id` UUID PRIMARY KEY
- `company_id` UUID NOT NULL FK → `companies.id`
- `currency_code` VARCHAR(3) NOT NULL FK → `currencies.code`
- `billing_enabled` BOOLEAN NOT NULL DEFAULT false
- `receipt_enabled` BOOLEAN NOT NULL DEFAULT false
- `is_default_billing` BOOLEAN NOT NULL DEFAULT false
- `is_default_receipt` BOOLEAN NOT NULL DEFAULT false
- `status` VARCHAR(20) NOT NULL
- `created_at` TIMESTAMPTZ NOT NULL
- `updated_at` TIMESTAMPTZ NOT NULL

**Column meanings and constraints**

- `id` is the stable identity for this richer AR configuration object, which may be referenced by future AR configuration. It is retained even though Company/Currency is also unique.
- `company_id` identifies the owning Company.
- `currency_code` identifies the shared Currency; `UNIQUE (company_id, currency_code)` permits only one AR configuration row per Company/Currency.
- `billing_enabled` independently permits the Currency for AR Billing.
- `receipt_enabled` independently permits the Currency for AR Receipts. Billing-only, Receipt-only, and both are valid configurations.
- `is_default_billing` marks the preferred/preselected Billing Currency and requires `billing_enabled = true`.
- `is_default_receipt` marks the preferred/preselected Receipt Currency and requires `receipt_enabled = true`.
- `status` is `ACTIVE` or `INACTIVE`; `SUSPENDED` is not introduced. An active row must enable Billing, Receipt, or both.
- `created_at` and `updated_at` record current-row timestamps.

**Physical constraints**

- PRIMARY KEY (`id`).
- UNIQUE (`company_id`, `currency_code`).
- CHECK (`NOT is_default_billing OR billing_enabled`).
- CHECK (`NOT is_default_receipt OR receipt_enabled`).
- CHECK/business constraint: `status <> 'ACTIVE' OR billing_enabled OR receipt_enabled`.
- At most one active row per Company may have `billing_enabled = true` and `is_default_billing = true`, using an appropriate PostgreSQL partial unique index/constraint direction.
- At most one active row per Company may have `receipt_enabled = true` and `is_default_receipt = true`, using an appropriate PostgreSQL partial unique index/constraint direction.
- The Base Currency is not automatically permitted merely because it is `companies.base_currency_code`. When allowed for Billing or Receipt, it requires an explicit AR Currency row under this same permission model. Setup may propose/create that row, but exact UI automation is not designed here.
- Foreign-currency/EEFC Bank Account behavior remains owned by `company_bank_accounts`; it is not stored in this table.
- Reporting permission remains independent and is not inferred from this table.

**Relationships**
- Company 1:N configured AR currency rows

**Why this table exists**
1. Billing Currency, Receipt Currency and Reporting Currency are different business permissions.
2. The same currency can be allowed for Billing, Receipt, or both without duplicate tables.
3. A Company can later add EUR only for Receipt by adding/enabling one row.
4. It supports same-currency foreign receipts into EEFC accounts.
5. It restricts FX setup to currencies the Company actually uses.
6. Removing it would either require separate billing/payment tables or allow every global currency by default.

`company_reporting_currencies` and `company_ar_currencies` remain separate because management presentation and AR operational permission are different business controls. A Currency may be Reporting-only, Receipt-only, Billing-only, or configured independently for multiple purposes. Actual rate facts belong to `exchange_rates`; rate-selection behavior belongs to `fx_policies`.

---

## 14. `company_bank_accounts` — KEEP

**Owner:** Core / Shared Company Configuration

**Physical table:** `core.company_bank_accounts`

**What data is stored**
- Company's bank accounts, currency and account type, including EEFC/foreign-currency accounts.

**Columns**
- `id` UUID PRIMARY KEY
- `company_id` UUID NOT NULL FK → `companies.id`
- `account_holder_name` VARCHAR(200) NOT NULL
- `bank_name` VARCHAR(200) NOT NULL
- `account_number` VARCHAR(64) NOT NULL
- `branch_name` VARCHAR(200) NULL
- `ifsc` VARCHAR(11) NULL
- `swift` VARCHAR(11) NULL
- `iban` VARCHAR(34) NULL
- `currency_code` VARCHAR(3) NOT NULL FK → `currencies.code`
- `account_type` VARCHAR(30) NULL — examples include `CURRENT` and `EEFC`; the universal list remains OPEN
- `gl_account_id` UUID NULL FK → `gl_accounts.id`
- `is_default_for_billing` BOOLEAN NOT NULL DEFAULT false
- `status` VARCHAR(20) NOT NULL
- `created_at` TIMESTAMPTZ NOT NULL
- `updated_at` TIMESTAMPTZ NOT NULL

**Column meanings and constraints**

- `id` is the stable Bank Account identity.
- `company_id` is the mandatory owner.
- `account_holder_name` and `bank_name` are required, non-blank business labels.
- `account_number` remains text because leading zeroes may matter and no arithmetic is performed on it.
- `branch_name`, `ifsc`, `swift`, and `iban` are nullable because their applicability varies by country/account. Canonical trimming and uppercase validation applies where appropriate.
- `currency_code` identifies the account Currency and supports INR, foreign-currency, and EEFC accounts.
- `account_type` optionally records a jurisdiction-relevant type; no universal global list is frozen here.
- `gl_account_id` is the direct, nullable Bank-to-GL reference. No additional mapping table is introduced.
- `is_default_for_billing` controls preselection only. At most one active default may exist for each (`company_id`, `currency_code`) through an appropriate PostgreSQL partial unique index direction; another eligible account may still be selected explicitly.
- `status` is `ACTIVE` or `INACTIVE`; historically used accounts are normally inactivated rather than deleted and `SUSPENDED` is not introduced.
- `created_at` and `updated_at` record current-row timestamps.
- Do not add universal `UNIQUE (account_number)` or `UNIQUE (company_id, account_number)` without an approved Bank identity/context and duplicate-detection policy.

**Relationships**
- Company 1:N Bank Accounts
- Currency 1:N Bank Accounts
- GL Account 1:N Bank Accounts; both records must belong to the same Company

**Why this table exists**
1. A Company may own multiple settlement accounts.
2. Invoice output may need a selected/default bank account.
3. Bank account currency is required for foreign-currency/EEFC receipt handling.
4. USD received in a USD EEFC account can settle a USD receivable without forcing INR conversion first.
5. SWIFT/IBAN/IFSC applicability differs by bank/account and should not live on Company.
6. The direct GL reference connects the operational bank account to its stable accounting identity without another mapping table.

**Accounting rule**
- `gl_account_id` may remain null while the Bank Account or CoA is being prepared. A future accounting-integrated operation that requires a bank ledger must block until an active, date-valid, same-Company GL Account is assigned. The full bank-posting journal is DEFERRED.

---

## 15. `exchange_rates` — KEEP

**What data is stored**
- Actual Company-relevant FX rate facts for a direction, type and effective period/date.

**Columns**
- `id` UUID PRIMARY KEY
- `company_id` UUID NOT NULL FK → `companies.id`
- `from_currency_code` VARCHAR(3) NOT NULL FK → `currencies.code`
- `to_currency_code` VARCHAR(3) NOT NULL FK → `currencies.code`
- `rate` NUMERIC(28,12) NOT NULL
- `rate_type` VARCHAR(20) NOT NULL — `CORPORATE` / `SPOT`
- `effective_from` DATE NOT NULL
- `effective_to` DATE NULL
- `source` VARCHAR(100) NULL
- `status` VARCHAR(20) NOT NULL
- `created_at` TIMESTAMPTZ NOT NULL
- `updated_at` TIMESTAMPTZ NOT NULL

**Column meanings and constraints**

- `id` is the stable identity of one reusable rate fact.
- `company_id` identifies the Company for which the rate is maintained.
- `from_currency_code` and `to_currency_code` preserve explicit direction. Reverse direction is a distinct fact; reciprocal rows are not created automatically.
- `rate` uses exact `NUMERIC(28,12)`, never floating-point, and must be greater than zero.
- `rate_type` is the reusable Exchange Rate Type: `CORPORATE` or `SPOT`. These are not currencies. `USER_FIXED` is transaction-specific and is not reusable master data.
- `effective_from` and nullable `effective_to` define the daily/period-based applicability range; `effective_to` must be null or on/after `effective_from`.
- `source` optionally records a source/reference without introducing provider-specific architecture.
- `status` is `ACTIVE` or `INACTIVE`.
- `created_at` and `updated_at` record current-row timestamps.
- CHECK (`rate > 0`).
- CHECK (`from_currency_code <> to_currency_code`); same-Currency FX rows are prohibited.
- CHECK (`effective_to IS NULL OR effective_to >= effective_from`).
- Active effective periods must not overlap for the same (`company_id`, `from_currency_code`, `to_currency_code`, `rate_type`). PostgreSQL range/GiST exclusion is an appropriate implementation direction.

**Relationships**
- Company 1:N FX Rates
- Each row references two currencies

**Why this table exists**
1. Billing/Receipt/Reporting need a historical rate source independent of final transaction snapshots.
2. Rate direction matters (`USD → INR` is not stored as the same row as `INR → USD`).
3. Effective dates preserve the rate that was available for a transaction date.
4. We only maintain pairs relevant to Base/AR/Reporting currencies, not every global pair.
5. Corporate and Spot rate facts can coexist without hardcoding numeric rates into transactions.
6. Removing it would make every transaction manually enter rates or depend on an external provider with no internal history.

---

## 16. `fx_policies` — KEEP

**What data is stored**
- Company rules telling each process which Exchange Rate Type to preselect and whether an authorized transaction-specific User-Fixed override is allowed. Detailed Receipt and Reporting runtime behavior remains OPEN.

**Columns**
- `id` UUID PRIMARY KEY
- `company_id` UUID NOT NULL FK → `companies.id`
- `purpose` VARCHAR(20) NOT NULL — `BILLING` / `RECEIPT` / `REPORTING`
- `default_rate_type` VARCHAR(20) NOT NULL — `CORPORATE` / `SPOT`
- `allow_user_fixed_override` BOOLEAN NOT NULL DEFAULT false
- `reason_required_for_override` BOOLEAN NOT NULL DEFAULT false
- `status` VARCHAR(20) NOT NULL
- `created_at` TIMESTAMPTZ NOT NULL
- `updated_at` TIMESTAMPTZ NOT NULL

**Column meanings and constraints**

- `id` is the stable FX Policy identity.
- `company_id` identifies the owning Company.
- `purpose` identifies the business process and is limited to `BILLING`, `RECEIPT`, or `REPORTING`.
- `default_rate_type` is the default **Exchange Rate Type**, not a default Currency. It preselects `CORPORATE` or `SPOT`; it does not mean Corporate Currency, Billing Currency, or Base Currency.
- `allow_user_fixed_override` says whether the process supports an authorized transaction-specific manual rate.
- `reason_required_for_override` requires a reason when a User-Fixed override is used and may be true only when overrides are allowed.
- `status` is `ACTIVE` or `INACTIVE`.
- `created_at` and `updated_at` record current-row timestamps.
- UNIQUE (`company_id`, `purpose`).
- CHECK (`NOT reason_required_for_override OR allow_user_fixed_override`).
- The provisional `override_role` column is REMOVED/DEFERRED. FX Policy enables the capability; IAM/RBAC determines which user may exercise it. Exact permission names and role design remain outside this table.

**Billing selection rule**

When Billing requires FX, load the Company's `BILLING` policy and preselect `default_rate_type`. `CORPORATE` and `SPOT` remain selectable; selecting either resolves its applicable rate from `exchange_rates`. `USER_FIXED` appears only when policy permits it and the current user is authorized. A manually entered rate is stored with the transaction/document snapshot rather than inserted into `exchange_rates`; a reason is mandatory when the policy requires one.

Receipt and Reporting retain purpose-specific policies and default Exchange Rate Types, but this Billing selection behavior is not automatically imposed on them while their detailed runtime, rate-date, stale-rate, and conversion rules remain OPEN.

**Relationships**
- Company 1:N FX Policies (normally one row per purpose)
- Resolves rate types from `exchange_rates`

**Why this table exists**
1. `exchange_rates` answers **what rates exist**; `fx_policies` answers **which rate type a process should use**.
2. Billing, Receipt and Reporting may need different rate behavior.
3. It avoids hardcoding `if billing then CORPORATE` separately in multiple modules.
4. It provides one place to control authorized User-Fixed overrides and reason requirements.
5. Policy can evolve without changing historic transaction rates because transactions snapshot the actual applied rate.
6. Removing it would push policy into application code and make Company-specific FX behavior harder to support.

Regardless of policy default, finalized transactions/documents preserve the actual transaction Currency, Base Currency, applied Rate Type, applied FX rate, and applicable User-Fixed override context/reason. This principle does not redesign transaction schemas here.

---

## 17. `tax_types` — KEEP

**What data is stored**
- System/reference identities for broad tax families such as GST, TDS, TCS, VAT and CESS.

**Columns**
- `id` UUID PRIMARY KEY
- `code` VARCHAR(30) NOT NULL
- `name` VARCHAR(100) NOT NULL
- `country_code` VARCHAR(2) NOT NULL
- `status` VARCHAR(20) NOT NULL
- `created_at` TIMESTAMPTZ NOT NULL
- `updated_at` TIMESTAMPTZ NOT NULL

**Physical constraints and boundaries**
- UNIQUE (`country_code`, `code`).
- `status` is controlled as `ACTIVE` or `INACTIVE`; referenced rows are inactivated rather than deleted.
- `code` is trimmed/canonical controlled identity and `name` is a required non-blank display label.
- `country_code` is the current ISO-style two-character jurisdiction code. The approved target is `core.countries.code`; the future Tax Type implementation must sequence reference-data provisioning and FK enforcement safely rather than adding that table in Migration 004.
- No business defaults are defined for these columns.
- CGST, SGST, and IGST are not Tax Types; they are GST statutory COMPONENT codes.
- Do not store HSN/SAC, percentage rates, treatments, statutory sections/components, thresholds, or calculation rules here.

**Relationships**
- Tax Type 1:N Tax Rates
- Tax Type 1:N Tax Statutory Codes
- Tax Type 1:N Tax Treatments

**Why this table exists**
1. It answers which broad tax family a rate, treatment or section belongs to.
2. It removes repeated GST/TDS/TCS strings from unrelated reference tables.
3. It prevents HSN/SAC from being mistaken for a tax family.
4. It lets one controlled tax-family identity be reused across Company Configuration, Billing and Receipt.
5. It leaves VAT or CESS reference support possible without pretending their calculation rules are implemented.
6. It gives validation and administration a stable reference instead of application-specific text constants.

**What happens if removed/merged**
- Tax-family text would be duplicated in `tax_rates`, `tax_treatments`, and `tax_statutory_codes`, making family validation and naming inconsistent. It must not be merged with HSN/SAC, percentages, statutory components, or sections because those answer different business questions.

**Decision status:** KEEP — controlled system/reference master; it does not create a generic tax engine.

**Flow stage:** Tax reference maintenance → catalogue/receipt configuration → Billing or Receipt consumes the referenced family.

---

## 18. `company_hsn_sac_codes` — KEEP

**What data is stored**
- Only the HSN and SAC codes/descriptions configured by each Company for its own products and services.

**Columns**
- `id` UUID PRIMARY KEY
- `company_id` UUID NOT NULL FK → `companies.id`
- `classification_type` VARCHAR(10) NOT NULL
- `code` VARCHAR(20) NOT NULL
- `description` VARCHAR(500) NOT NULL
- `status` VARCHAR(20) NOT NULL
- `created_at` TIMESTAMPTZ NOT NULL
- `updated_at` TIMESTAMPTZ NOT NULL

**Physical constraints and boundaries**
- CHECK (`classification_type IN ('HSN', 'SAC')`).
- UNIQUE (`company_id`, `classification_type`, `code`).
- `status` is controlled as `ACTIVE` or `INACTIVE`; historically used classifications are normally inactivated rather than deleted.
- `code` is textual statutory identity and preserves leading zeroes.
- Backend validation, not only UI filtering, enforces SAC for Service Types and HSN for SKUs.
- No business defaults are defined for these columns.
- Do not store Tax Type, an uncontrolled percentage, Tax Treatment, statutory COMPONENT/SECTION, or transaction calculation rules here.

**India-first boundary — DEFERRED generalization**
- This is the current India-first Company classification model. A future foreign-seller rollout may generalize/replace it with a broader Company Tax Classification model, but no scheme tables, arbitrary rule JSON, country-specific child tables, or generic tax engine are added now. Historical India GST data must remain stable through any later extension.

**Relationships**
- Company 1:N Company HSN/SAC Codes
- Company HSN/SAC Code 1:N eligible-rate relationships
- Referenced by Service Types only when `classification_type = SAC`
- Referenced by SKUs only when `classification_type = HSN`
- Referenced optionally by Revenue Mapping HSN/SAC conditions

**Why this table exists**
1. Each Company needs only the statutory codes relevant to what it actually sells.
2. A single typed table avoids duplicate HSN and SAC schemas while keeping their kinds explicit.
3. Service Types and SKUs use controlled Company-owned references instead of free text.
4. Company ownership prevents a compulsory copy of thousands of global classifications.
5. Eligible-rate and revenue-account mappings need a stable HSN/SAC identity.
6. The explicit name prevents GST, TDS, TCS, VAT, or CESS families from being confused with item classification.

**What happens if removed/merged**
- Removing it would repeat free-text HSN/SAC across catalogue and transaction setup. Merging it into `tax_types`, `tax_rates`, `tax_treatments`, or GL Accounts would conflate statutory item classification with tax family, percentage, treatment, or accounting identity.

**Decision status:** KEEP — replaces the ambiguous `tax_classifications` name; no parallel legacy table remains.

**Flow stage:** Company Tax Setup → configure relevant HSN/SAC → Service Type/SKU selection → eligible-rate and Billing resolution.

---

## 19. `tax_rates` — KEEP

**What data is stored**
- Controlled numeric tax-rate values belonging to a broad Tax Type; GST rates are the current AR use.

**Columns**
- `id` UUID PRIMARY KEY
- `tax_type_id` UUID NOT NULL FK → `tax_types.id`
- `rate_percent` NUMERIC(9,6) NOT NULL
- `country_code` VARCHAR(2) NOT NULL
- `status` VARCHAR(20) NOT NULL
- `created_at` TIMESTAMPTZ NOT NULL
- `updated_at` TIMESTAMPTZ NOT NULL

**Physical constraints and boundaries**
- CHECK (`rate_percent >= 0 AND rate_percent <= 100`).
- UNIQUE (`tax_type_id`, `country_code`, `rate_percent`).
- `status` is controlled as `ACTIVE` or `INACTIVE`; historically referenced rates are not deleted.
- `country_code` references `core.countries.code` with restrictive/no-cascade behavior.
- No business defaults are defined, and financial rates never use floating-point types.
- Numeric `0%` does not imply `NIL_RATED`, `EXEMPT`, or `NON_GST`; treatment remains separate.
- This table stores reusable ordinary item/supply percentage-rate identities, currently primarily GST HSN/SAC rates. It does not store every percentage in the system, statutory SECTION/case rates, thresholds, or transaction results.

**Relationships**
- Tax Type 1:N Tax Rates
- Tax Rate 1:N Company HSN/SAC eligible-rate relationships

**Why this table exists**
1. Rate values must not be typed manually for every Service Type, SKU or invoice.
2. It provides a controlled numeric list such as GST 0%, 5%, 12%, 18% and 28% where configured and legally supported.
3. `tax_type_id` states the family without embedding uncontrolled GST/TDS/TCS text.
4. It supports validated dropdowns and effective HSN/SAC-rate relationships.
5. Final invoice lines snapshot the applied rate, so later reference changes do not rewrite history.
6. It keeps numeric percentages separate from treatments and TDS/TCS section-rate cases.

**What happens if removed/merged**
- Numeric values would be duplicated in Company mappings or catalogues. Merging them with `tax_treatments` would incorrectly make 0% equivalent to NIL_RATED, EXEMPT, or NON_GST; merging them with section rates would mix GST item taxation with TDS/TCS section semantics.

**Decision status:** KEEP — numeric reference master linked to `tax_types`; the rate list is not hardcoded in application logic.

**Flow stage:** Tax reference maintenance → Company HSN/SAC eligible-rate mapping → catalogue default selection → Billing snapshot.

---

## 20. `company_hsn_sac_tax_rates` — KEEP

**What data is stored**
- Which controlled Tax Rates are valid/configured for a Company's HSN/SAC code and during which effective period.

**Columns**
- `id` UUID PRIMARY KEY
- `company_hsn_sac_code_id` UUID NOT NULL FK → `company_hsn_sac_codes.id`
- `tax_rate_id` UUID NOT NULL FK → `tax_rates.id`
- `valid_from` DATE NOT NULL
- `valid_to` DATE NULL
- `status` VARCHAR(20) NOT NULL
- `created_at` TIMESTAMPTZ NOT NULL
- `updated_at` TIMESTAMPTZ NOT NULL

**Physical constraints and boundaries**
- CHECK (`valid_to IS NULL OR valid_to >= valid_from`).
- `status` is controlled as `ACTIVE` or `INACTIVE`; no business defaults are defined.
- Active effective ranges for the same (`company_hsn_sac_code_id`, `tax_rate_id`) must not overlap. PostgreSQL range/GiST exclusion is an appropriate implementation direction.
- Do not add global UNIQUE (`company_hsn_sac_code_id`, `tax_rate_id`), because separate historical effective periods are valid.
- For current AR, the referenced `tax_rate_id` must belong to the GST Tax Type.
- Do not store copied rate percentages, treatment, statutory SECTION rates, transaction tax amounts, or generic calculation rules here.

**Relationships**
- Company HSN/SAC Codes N:M Tax Rates through this table
- Validates the current `service_types.selected_tax_rate_id` and `skus.selected_tax_rate_id`
- For the current AR flow, the referenced Tax Rate must belong to the GST Tax Type

**Why this table exists**
1. One Company HSN/SAC code may allow multiple GST rates.
2. Catalogue and Billing should show only rates configured for the selected code.
3. Effective dates allow statutory/configuration changes without overwriting prior relationships.
4. It separates shared numeric rate facts from Company-owned item classifications.
5. It supplies a relational validation target for the current Service Type/SKU default rate.
6. It prevents application code from hardcoding HSN/SAC-to-rate lists.

**What happens if removed/merged**
- The UI would show every rate for every HSN/SAC, or catalogue rows would need duplicated percentages. Merging the relationship into the HSN/SAC row would allow only one rate and lose effective history.

**Decision status:** KEEP — replaces `tax_classification_rates`; only the new table is counted as current. Current AR HSN/SAC mappings accept GST Tax Rates and do not absorb TDS/TCS section rates.

**Flow stage:** Company Tax Setup → map HSN/SAC to eligible effective Tax Rates → catalogue selects one current default → Billing revalidates and snapshots the applied rate.

---

## 21. `tax_treatments` — KEEP

**What data is stored**
- Controlled Tax/GST nature and treatment references. For current Service Type/SKU catalogue use, the confirmed Base GST Nature values are `TAXABLE`, `NIL_RATED`, `EXEMPT`, and `NON_GST`.

**Columns**
- `id` UUID PRIMARY KEY
- `code` VARCHAR(30) NOT NULL
- `name` VARCHAR(100) NOT NULL
- `tax_type_id` UUID NOT NULL FK → `tax_types.id`
- `country_code` VARCHAR(2) NOT NULL
- `status` VARCHAR(20) NOT NULL
- `created_at` TIMESTAMPTZ NOT NULL
- `updated_at` TIMESTAMPTZ NOT NULL

**Physical constraints and boundaries**
- UNIQUE (`tax_type_id`, `country_code`, `code`).
- `status` is controlled as `ACTIVE` or `INACTIVE`; referenced treatments are inactivated rather than deleted.
- Current confirmed catalogue Base GST Nature codes are `TAXABLE`, `NIL_RATED`, `EXEMPT`, and `NON_GST`; `ZERO_RATED` is a possible transaction-level result and is not added as a catalogue choice.
- `country_code` references `core.countries.code` with restrictive/no-cascade behavior.
- No business defaults are defined.
- For Service Type/SKU use, the reference describes Base GST Nature, not a percentage or final transaction outcome. Do not infer it only from `rate_percent` or store rates/calculation logic here.

**Relationships**
- Tax Type 1:N Tax Treatments
- Referenced as the current Base GST Nature by Service Types and SKUs through `base_tax_treatment_id`
- Final invoice lines snapshot the Base GST Nature and separately preserve the transaction-level outcome and tax facts used

**Why this table exists**
1. For catalogue use, Base GST Nature states the item's inherent GST nature; it is not a percentage or the complete transaction result.
2. It prevents a numeric 0% rate from being used as a substitute for NIL_RATED, EXEMPT, or NON_GST.
3. It provides consistent controlled choices across Service and Goods catalogues.
4. It lets catalogue validation enforce the Base GST Nature/rate matrix and lets future Billing start from an explicit item fact.
5. It gives historical snapshots a stable source while preserving the actual issued value.
6. It prevents the term “Tax Rate Type” from being used for treatment semantics.

**What happens if removed/merged**
- Treatment codes would be repeated as uncontrolled fields or inferred incorrectly from the numeric rate. Merging treatments into `tax_rates` would erase the distinction between `0%` and the legal/product treatment of the supply.

**Decision status:** KEEP — confirmed controlled master; restrict current Service Type/SKU catalogue assignment to the four approved Base GST Nature codes and do not add `ZERO_RATED` as a catalogue value.

**Flow stage:** Tax reference maintenance → Service Type/SKU Base GST Nature → future Billing transaction-context resolution → immutable line snapshot.

---

## 22. `tax_statutory_codes` — KEEP

**What data is stored**
- Controlled statutory identities associated with a Tax Type. `code_kind = COMPONENT` identifies statutory components such as GST components; `code_kind = SECTION` identifies TDS/TCS statutory sections/categories. Examples that have not received current statutory review are not asserted as current legal truth.

**Columns**
- `id` UUID PRIMARY KEY DEFAULT `gen_random_uuid()`
- `tax_type_id` UUID NOT NULL FK → `tax_types.id`
- `code` VARCHAR(50) NOT NULL
- `name` VARCHAR(150) NOT NULL
- `description` VARCHAR(500) NULL
- `code_kind` VARCHAR(20) NOT NULL
- `country_code` VARCHAR(2) NOT NULL
- `status` VARCHAR(20) NOT NULL
- `created_at` TIMESTAMPTZ NOT NULL DEFAULT `CURRENT_TIMESTAMP`
- `updated_at` TIMESTAMPTZ NOT NULL DEFAULT `CURRENT_TIMESTAMP`

**Physical constraints and boundaries**
- CHECK (`btrim(code) <> ''`).
- CHECK (`btrim(name) <> ''`).
- CHECK (`code_kind IN ('COMPONENT', 'SECTION')`).
- CHECK (`country_code ~ '^[A-Z]{2}$'`).
- CHECK (`status IN ('ACTIVE', 'INACTIVE')`).
- UNIQUE (`tax_type_id`, `country_code`, `code_kind`, `code`).
- FOREIGN KEY `tax_type_id` → `core.tax_types.id` uses `ON DELETE NO ACTION`.
- `status` is controlled as `ACTIVE` or `INACTIVE`; referenced codes are inactivated rather than deleted.
- `country_code` is format-controlled as exactly two uppercase ASCII letters. It has no FK to `core.countries`; persistence does not validate Country-master membership.
- `code` comparison is case-sensitive, `name` is not unique, and persistence performs no trimming or upper/lower-case transformation.
- No business defaults are defined; in particular, `status` has no default. Only the established UUID and timestamp infrastructure defaults apply.
- COMPONENT identifies statutory components; SECTION identifies TDS/TCS statutory sections/categories.
- Do not merge or store HSN/SAC, ordinary item Tax Rates, Tax Treatment, thresholds, or transaction calculation results here.

**Relationships**
- Tax Type 1:N Tax Statutory Codes
- Tax Statutory Code 1:N effective Code Rates
- Tax Statutory Code 1:N Company Tax GL Account Mappings

**Why this table exists**
1. GST components and TDS/TCS sections need stable statutory identities for validation and GL mapping.
2. `code_kind` keeps components and sections distinct without calling CGST/SGST/IGST “sections.”
3. `tax_type_id` ties each code to GST, TDS, TCS or another controlled family without repeated free text.
4. Receipt can select an applicable TDS section from a valid controlled list.
5. Billing can map calculated GST component identities to Company GL Accounts without `tax_component_code` text.
6. It keeps statutory identity separate from ordinary GST item percentages in `tax_rates`.

**What happens if removed/merged**
- Component/section codes would be duplicated on mappings and transactions. Merging them with HSN/SAC or ordinary Tax Rates would confuse statutory identity with item classification or percentage.

**Decision status:** KEEP — generalized/renamed from `statutory_sections`. Initial kinds are COMPONENT and SECTION; this is a controlled identity layer, not a generic tax engine.

**Flow stage:** Statutory reference maintenance → GST component/TDS/TCS section resolution → Company GL mapping or transaction selection → snapshot.

---

## 23. `tax_statutory_code_rates` — KEEP

**What data is stored**
- Effective numeric rate cases belonging to a Tax Statutory Code, primarily TDS/TCS SECTION codes. Ordinary GST item rates remain in `tax_rates`.

**Columns**
- `id` UUID PRIMARY KEY DEFAULT `gen_random_uuid()`
- `tax_statutory_code_id` UUID NOT NULL FK → `tax_statutory_codes.id`
- `case_code` VARCHAR(50) NULL
- `rate_percent` NUMERIC(9,6) NOT NULL
- `valid_from` DATE NOT NULL
- `valid_to` DATE NULL
- `status` VARCHAR(20) NOT NULL
- `created_at` TIMESTAMPTZ NOT NULL DEFAULT `CURRENT_TIMESTAMP`
- `updated_at` TIMESTAMPTZ NOT NULL DEFAULT `CURRENT_TIMESTAMP`

**Physical constraints and boundaries**
- CHECK (`case_code IS NULL OR btrim(case_code) <> ''`). A null `case_code` is the default logical case; persistence performs no trimming or case transformation.
- CHECK (`rate_percent >= 0 AND rate_percent <= 100`).
- CHECK (`valid_to IS NULL OR valid_to >= valid_from`).
- CHECK (`status IN ('ACTIVE', 'INACTIVE')`).
- FOREIGN KEY `tax_statutory_code_id` → `core.tax_statutory_codes.id` uses `ON DELETE NO ACTION`.
- `status` is controlled as `ACTIVE` or `INACTIVE`; it has no default. Only the established UUID and timestamp infrastructure defaults apply.
- The child FK is only `tax_statutory_code_id` → `tax_statutory_codes.id`. Current use is primarily SECTION rates, but the database does not restrict the parent's `code_kind`; COMPONENT-linked rates are not prohibited by persistence. Do not add a trigger, duplicate `code_kind`, a SECTION-only check, or separate kind-specific rate tables.
- Active inclusive effective ranges for the same (`tax_statutory_code_id`, non-null `case_code`) must not overlap. Enforce this with a partial GiST exclusion constraint over (`tax_statutory_code_id` WITH `=`, `case_code` WITH `=`, `daterange(valid_from, valid_to, '[]')` WITH `&&`) where `status = 'ACTIVE' AND case_code IS NOT NULL`.
- Active inclusive effective ranges for the default logical case must not overlap. Enforce this with a separate partial GiST exclusion constraint over (`tax_statutory_code_id` WITH `=`, `daterange(valid_from, valid_to, '[]')` WITH `&&`) where `status = 'ACTIVE' AND case_code IS NULL`; do not use a sentinel value.
- Different non-null named cases may overlap, and INACTIVE rows do not participate in either exclusion constraint.
- `case_code` remains nullable because some sections have one ordinary/default case.
- Do not add `tax_rate_id`. Equal numeric percentages do not make statutory SECTION/case rates and ordinary item/supply rates the same business identity.
- Do not store thresholds, cumulative tracking, exemptions/certificates, or transaction amounts here.

**Relationships**
- Tax Statutory Code 1:N Rate Cases

**Why this table exists**
1. A statutory section's rate can change over time.
2. One section may have more than one configured rate case/context.
3. It keeps TDS/TCS section-rate semantics separate from ordinary GST `tax_rates`.
4. Receipt can derive the configured rate after the user selects the applicable section/code.
5. Later approved TCS logic can resolve a section rate without using HSN/SAC GST mapping.
6. Historical final transactions snapshot the actual section, case, rate, basis, and amount applied.

**What happens if removed/merged**
- Only one current rate could be stored on a section, losing effective history and rate cases. Merging it with `tax_rates` would mix section-based TDS/TCS behavior with ordinary item tax rates.

**Decision status:** KEEP — generalized/renamed from `statutory_section_rates`; advanced thresholds, cumulative behavior, exemptions and override logic remain later transaction-module decisions. GST COMPONENT codes do not replace ordinary GST rates in `tax_rates`.

**Flow stage:** Section configuration → applicable case/rate resolution → Receipt or Billing records the actual section/rate/amount.

**Ordinary-rate versus statutory-case distinction**

- `tax_rates` stores reusable ordinary item/supply percentage-rate identities, currently primarily GST rates eligible for Company HSN/SAC classifications.
- `tax_statutory_code_rates` stores effective statutory SECTION/case rates, primarily for TDS/TCS.
- Both use percentages, but they have different business identities. No mandatory FK connects them and `tax_statutory_code_rates` has no `tax_rate_id`.

**Jurisdiction boundary**

- Generic/country-scoped references: `tax_types`, `tax_rates`, `tax_treatments`, `tax_statutory_codes`, and `tax_statutory_code_rates`.
- Current India-specific design: `gst_registration_types`, `company_gst_registrations`, `company_hsn_sac_codes`, and `company_hsn_sac_tax_rates`.
- This design does not claim complete foreign-jurisdiction support. A broader tax-registration abstraction and generalized item-tax classification scheme remain DEFERRED for a future foreign-Company rollout and must preserve historical India GST data.
- Finalized transactions preserve applied tax values/snapshots according to their owning transaction design; historical output is never reconstructed from mutable current references.

---

## 24. `supply_types` — REVIEW / LIKELY KEEP AS REFERENCE

**What data would be stored**
- Controlled product vocabulary for B2B, B2C, EXPWOP, EXPWP, SEZWOP and SEZWP.

**Proposed physical columns — table-versus-enum decision remains REVIEW**

`id`
- Type: UUID; Nullability: NOT NULL; Default: none; Key: PRIMARY KEY.
- Why: stable internal Supply Type identity for future references if the table form is approved.

`code`
- Type: VARCHAR(30); Nullability: NOT NULL; Default: none; Constraint: UNIQUE.
- Why: stable controlled product code such as `B2B`, `EXPWOP`, or `SEZWP`.

`name`
- Type: VARCHAR(100); Nullability: NOT NULL; Default: none.
- Why: human-readable Supply Type label.

`category`
- Type: VARCHAR(30); Nullability: NOT NULL; Default: none; CHECK: `DOMESTIC`, `EXPORT`, or `SEZ_DEEMED`.
- Why: groups the controlled terminology without changing the individual Supply Type identity.

`with_payment`
- Type: BOOLEAN; Nullability: NULL; Default: none.
- Why: distinguishes with-payment/without-payment Export or SEZ-Deemed terminology where applicable; it is null for Domestic types when that distinction does not define the type.

`status`
- Type: VARCHAR(20); Nullability: NOT NULL; Default: none; Controlled values: `ACTIVE`, `INACTIVE`.
- Why: retires a controlled value without deleting historical references.

`created_at`
- Type: TIMESTAMPTZ; Nullability: NOT NULL; Default: none.
- Why: records when the current reference row was created.

`updated_at`
- Type: TIMESTAMPTZ; Nullability: NOT NULL; Default: none.
- Why: records when the current reference row was last updated.

No additional Supply Types or Supply Type calculation/resolution rules are introduced. The physical table remains **REVIEW / LIKELY KEEP AS REFERENCE** until table-versus-enum storage is approved.

**Relationships**
- Referenced later by SO/Billing and document-sequence conditions

**Why we may keep it**
1. Supply Type is reused in Sales Order, Billing, tax validation and numbering.
2. A controlled code list prevents spelling/meaning drift across modules.
3. Numbering conditions need a stable value to compare against.
4. Export/SEZ variants need clear product terminology independent of UI labels.
5. It can support enable/disable or metadata later without changing transaction schemas.
6. If the values are permanently hardcoded product enums, a table is optional; therefore final storage form is still reviewable.

---

# 5. AR Catalogue / Cost-Center Configuration

*Current-state table numbers follow the documented entity order. GST Registration Type is grouped with Company GST Registration, the tax-reference block remains together, and cost-center tables are grouped below the catalogues.*

## 25. `service_categories` — KEEP

**What data is stored**
- Company-defined grouping of services.

**Columns and purpose**

`id`
- Type: UUID; Nullability: NOT NULL; Default: none; Key: PRIMARY KEY.
- Why: stable Service Category identity used by Service Types.

`company_id`
- Type: UUID; Nullability: NOT NULL; Default: none; FK: `companies.id`.
- Why: identifies the Company that owns this private service grouping.

`name`
- Type: VARCHAR(150); Nullability: NOT NULL; Default: none; Constraint: UNIQUE with Company.
- Why: required business-facing category name.

`code`
- Type: VARCHAR(50); Nullability: NULL; Default: none; Constraint: partial UNIQUE with Company when non-null.
- Why: optional Company-specific operational/reference code.

`status`
- Type: VARCHAR(20); Nullability: NOT NULL; Default: none; Controlled values: `ACTIVE`, `INACTIVE`.
- Why: controls current catalogue availability while retaining historical identity.

`created_at`
- Type: TIMESTAMPTZ; Nullability: NOT NULL; Default: none.
- Why: records creation of the current category row.

`updated_at`
- Type: TIMESTAMPTZ; Nullability: NOT NULL; Default: none.
- Why: records the latest update to the current category row.

**Constraints and lifecycle**
- UNIQUE (`company_id`, `name`).
- Partial UNIQUE (`company_id`, `code`) WHERE `code IS NOT NULL`.
- Historically used categories are inactivated rather than deleted; inactive is terminal and inactive rows are read-only.
- Inactivation is rejected while any active Product references the category. Inactive Products do not block inactivation, and children are never moved or cascade-deleted.

**Relationships**
- Company 1:N Service Categories
- Service Category 1:N Service Types

**Why this table exists**
1. Companies define their own service taxonomy; there is no global commercial service catalogue.
2. It groups Service Types for setup/search/reporting.
3. It avoids repeating category text on every Service Type.
4. Different Companies can use different category names for similar work.
5. It supports future category-level UI convenience without owning final SAC.
6. Removing it would flatten services and lose useful hierarchy.

---

## 26. `service_types` — KEEP

**What data is stored**
- Lowest billable/selectable service item and its current statutory/reporting configuration.

**Columns and purpose — current MVP direction**

`id`
- Type: UUID; Nullability: NOT NULL; Default: none; Key: PRIMARY KEY.
- Why: stable lowest-level billable Service identity.

`company_id`
- Type: UUID; Nullability: NOT NULL; Default: none; FK: `companies.id`.
- Why: identifies the Company that owns the Service Type.

`service_category_id`
- Type: UUID; Nullability: NOT NULL; Default: none; FK: `service_categories.id`.
- Why: places the Service Type under its Company-owned Service Category.

`name`
- Type: VARCHAR(200); Nullability: NOT NULL; Default: none.
- Why: business-facing billable Service name.

`code`
- Type: VARCHAR(50); Nullability: NULL; Default: none; Constraint: partial Company-scoped uniqueness when non-null.
- Why: optional Company operational/reference code.

`description`
- Type: VARCHAR(500); Nullability: NULL; Default: none.
- Why: optional reusable Service description.

`uom`
- Type: VARCHAR(30); Nullability: NULL; Default: none.
- Why: optional Unit of Measure for the Service catalogue entry.

`company_hsn_sac_code_id`
- Type: UUID; Nullability: NOT NULL; Default: none; FK: `company_hsn_sac_codes.id`.
- Why: references the same-Company SAC statutory classification used for this Service.

`selected_tax_rate_id`
- Type: UUID; Nullability: NULL; Default: none; FK: `tax_rates.id`.
- Why: stores the current/default eligible GST rate when Base GST Nature requires one; `EXEMPT` and `NON_GST` deliberately have no selected rate.

`base_tax_treatment_id`
- Type: UUID; Nullability: NOT NULL; Default: none; FK: `tax_treatments.id`.
- Why: records the item's controlled Base GST Nature separately from the numeric rate and future transaction-level GST outcome.

`business_segment_id`
- Type: UUID; Nullability: NULL; Default: none; FK: `cost_center_business_segments.id`.
- Why: optionally assigns the Service Type to one same-Company Business Segment reporting bucket.

`tcs_check_required`
- Type: BOOLEAN; Nullability: NOT NULL; Default: `false`.
- Why: requires the applicable Billing TCS decision; it does not automatically charge TCS.

`status`
- Type: VARCHAR(20); Nullability: NOT NULL; Default: none; Controlled values: `ACTIVE`, `INACTIVE`.
- Why: controls current selection while preserving historically referenced Services.

`created_at`
- Type: TIMESTAMPTZ; Nullability: NOT NULL; Default: none.
- Why: records creation of the current Service Type row.

`updated_at`
- Type: TIMESTAMPTZ; Nullability: NOT NULL; Default: none.
- Why: records the latest update to the current Service Type row.

**Constraints and business validation**
- Partial UNIQUE (`company_id`, `code`) WHERE `code IS NOT NULL`.
- `service_category_id` and SAC must belong to the same Company; backend/database protection must prevent cross-Company references.
- `company_hsn_sac_code_id` must have `classification_type = SAC`.
- `base_tax_treatment_id` must identify an active GST treatment in the matching jurisdiction whose code is exactly `TAXABLE`, `NIL_RATED`, `EXEMPT`, or `NON_GST`; other codes, including `ZERO_RATED`, are invalid for catalogue use.
- `TAXABLE` requires `selected_tax_rate_id` to be an active GST Tax Rate currently eligible for the selected SAC through `company_hsn_sac_tax_rates`.
- `NIL_RATED` requires the same active eligible relationship and a numeric rate of exactly 0%; a 0% rate never changes the Base GST Nature by inference.
- `EXEMPT` and `NON_GST` require `selected_tax_rate_id` to be NULL; no artificial 0% rate is assigned.
- `business_segment_id`, when populated, must reference a Business Segment owned by the same Company; a direct nullable FK limits the Service Type to at most one current Segment.
- Pricing fields do not belong on this catalogue table.
- Historically used Service Types are normally inactivated rather than deleted.

**Relationships**
- Category 1:N Service Types
- Company SAC 1:N Service Types; the referenced row must have `classification_type = SAC`
- Tax Treatment master 1:N Service Types as Base GST Nature
- Business Segment 1:N Service Types (nullable from Service Type)

**Why this table exists**
1. Service Type is the lowest billable service identity used by SO/Billing.
2. Commercial name and selected SAC are Company-configured while the SAC retains its statutory meaning.
3. Nullable `selected_tax_rate_id` stores the current/default eligible rate only for Base GST Natures that require one; it must remain valid for `company_hsn_sac_code_id`.
4. The optional direct Business Segment relationship supports current management reporting without a mapping table.
5. TCS mandatory-check flag can force an applicability decision without automatically charging TCS.
6. Removing it would leave no stable service item for pricing, tax classification or reporting.

**Current tax rule**
- Base GST Nature is a catalogue classification, not a numeric Tax Rate Type or the final Billing outcome. Validate the final nature/rate combination before the item is billable; a later Billing resolver derives the transaction result from Supply Type and other transaction context.

---

## 27. `product_categories` — KEEP

**What data is stored**
- Company-defined grouping of products.

**Columns and purpose**

`id`
- Type: UUID; Nullability: NOT NULL; Default: none; Key: PRIMARY KEY.
- Why: stable Product Category identity.

`company_id`
- Type: UUID; Nullability: NOT NULL; Default: none; FK: `companies.id`.
- Why: identifies the Company that owns the goods grouping.

`name`
- Type: VARCHAR(150); Nullability: NOT NULL; Default: none; Constraint: UNIQUE with Company.
- Why: required business-facing category name.

`code`
- Type: VARCHAR(50); Nullability: NULL; Default: none; Constraint: partial UNIQUE with Company when non-null.
- Why: optional Company-specific operational/reference code.

`status`
- Type: VARCHAR(20); Nullability: NOT NULL; Default: none; Controlled values: `ACTIVE`, `INACTIVE`.
- Why: controls current catalogue use without erasing historical identity.

`created_at`
- Type: TIMESTAMPTZ; Nullability: NOT NULL; Default: none.
- Why: records creation of the current category row.

`updated_at`
- Type: TIMESTAMPTZ; Nullability: NOT NULL; Default: none.
- Why: records the latest update to the current category row.

**Constraints and lifecycle**
- UNIQUE (`company_id`, `name`).
- Partial UNIQUE (`company_id`, `code`) WHERE `code IS NOT NULL`.
- Historically used categories are normally inactivated rather than deleted.

**Relationships**
- Company 1:N Product Categories
- Product Category 1:N Products

**Why this table exists**
1. It gives goods catalogue a clear first-level hierarchy.
2. Categories are Company-defined, not global product semantics.
3. It simplifies UI filtering and catalogue maintenance.
4. It avoids repeating category text on every Product/SKU.
5. Category can later carry presentation/default metadata without becoming the final HSN owner.
6. Removing it would flatten product organisation and make catalogue management harder.

---

## 28. `products` — KEEP

**What data is stored**
- Commercial product family/model above SKU level.

**Columns and purpose**

`id`
- Type: UUID; Nullability: NOT NULL; Default: none; Key: PRIMARY KEY.
- Why: stable commercial Product-family identity.

`company_id`
- Type: UUID; Nullability: NOT NULL; Default: none; FK: `companies.id`.
- Why: identifies the Company that owns the Product.

`product_category_id`
- Type: UUID; Nullability: NOT NULL; Default: none; FK: `product_categories.id`.
- Why: places the Product under a same-Company first-level Product Category.

`name`
- Type: VARCHAR(200); Nullability: NOT NULL; Default: none.
- Why: business-facing Product family/model name.

`code`
- Type: VARCHAR(50); Nullability: NULL; Default: none; Constraint: partial Company-scoped uniqueness when non-null.
- Why: optional Company operational/reference code.

`description`
- Type: VARCHAR(500); Nullability: NULL; Default: none.
- Why: optional reusable description of the Product family/model.

`status`
- Type: VARCHAR(20); Nullability: NOT NULL; Default: none; Controlled values: `ACTIVE`, `INACTIVE`.
- Why: controls current catalogue availability while retaining historical identity.

`created_at`
- Type: TIMESTAMPTZ; Nullability: NOT NULL; Default: none.
- Why: records creation of the current Product row.

`updated_at`
- Type: TIMESTAMPTZ; Nullability: NOT NULL; Default: none.
- Why: records the latest update to the current Product row.

**Constraints and business validation**
- Partial UNIQUE (`company_id`, `code`) WHERE `code IS NOT NULL`.
- `product_category_id` must belong to the same Company; backend/database protection must prevent cross-Company references.
- Product remains commercial hierarchy only. Final HSN, UOM, conditional selected Tax Rate, and Base GST Nature remain on SKU.
- `product_category_id` is immutable after creation. A classification change inactivates the old Product and creates a replacement under the correct category.
- Historically used Products are inactivated rather than deleted; inactive is terminal and inactive rows are read-only.
- Inactivation is rejected while any active SKU references the Product. Inactive SKUs do not block inactivation, and children are never moved or cascade-deleted.

**Relationships**
- Product Category 1:N Products
- Product 1:N SKUs

**Why this table exists**
1. One Product may have several billable SKUs/variants.
2. It keeps common commercial identity separate from SKU-specific code/HSN/UOM.
3. It supports search/catalogue hierarchy.
4. It prevents duplicating Product name/category metadata on every SKU.
5. It leaves room for future SKU attributes without inventory design now.
6. Removing it would force every SKU to repeat full Product information.

---

## 29. `skus` — KEEP

**What data is stored**
- Lowest billable/selectable goods item and its current statutory/reporting configuration.

**Columns and purpose — current MVP direction**

`id`
- Type: UUID; Nullability: NOT NULL; Default: none; Key: PRIMARY KEY.
- Why: stable lowest-level billable Goods identity.

`company_id`
- Type: UUID; Nullability: NOT NULL; Default: none; FK: `companies.id`.
- Why: identifies the Company that owns the SKU.

`product_id`
- Type: UUID; Nullability: NOT NULL; Default: none; FK: `products.id`.
- Why: places the SKU under its same-Company Product family/model.

`sku_code`
- Type: VARCHAR(80); Nullability: NOT NULL; Default: none; Constraint: UNIQUE with Company.
- Why: required Company-specific operational identity for the sellable variation.

`name`
- Type: VARCHAR(200); Nullability: NOT NULL; Default: none.
- Why: business-facing SKU name.

`description`
- Type: VARCHAR(500); Nullability: NULL; Default: none.
- Why: optional reusable SKU description.

`uom`
- Type: VARCHAR(30); Nullability: NOT NULL; Default: none.
- Why: required Unit of Measure for the billable Goods item.

`company_hsn_sac_code_id`
- Type: UUID; Nullability: NOT NULL; Default: none; FK: `company_hsn_sac_codes.id`.
- Why: references the same-Company HSN statutory classification used for this SKU.

`selected_tax_rate_id`
- Type: UUID; Nullability: NULL; Default: none; FK: `tax_rates.id`.
- Why: stores the current/default eligible GST rate when Base GST Nature requires one; `EXEMPT` and `NON_GST` deliberately have no selected rate.

`base_tax_treatment_id`
- Type: UUID; Nullability: NOT NULL; Default: none; FK: `tax_treatments.id`.
- Why: records the item's controlled Base GST Nature separately from the numeric rate and future transaction-level GST outcome.

`business_segment_id`
- Type: UUID; Nullability: NULL; Default: none; FK: `cost_center_business_segments.id`.
- Why: optionally assigns the SKU to one same-Company Business Segment reporting bucket.

`tcs_check_required`
- Type: BOOLEAN; Nullability: NOT NULL; Default: `false`.
- Why: requires the applicable Billing TCS decision; it does not automatically levy TCS.

`status`
- Type: VARCHAR(20); Nullability: NOT NULL; Default: none; Controlled values: `ACTIVE`, `INACTIVE`.
- Why: controls current selection while preserving historically referenced SKUs.

`created_at`
- Type: TIMESTAMPTZ; Nullability: NOT NULL; Default: none.
- Why: records creation of the current SKU row.

`updated_at`
- Type: TIMESTAMPTZ; Nullability: NOT NULL; Default: none.
- Why: records the latest update to the current SKU row.

**Constraints and business validation**
- UNIQUE (`company_id`, `sku_code`).
- `product_id` and HSN must belong to the same Company; backend/database protection must prevent cross-Company references.
- `company_hsn_sac_code_id` must have `classification_type = HSN`.
- `base_tax_treatment_id` must identify an active GST treatment in the matching jurisdiction whose code is exactly `TAXABLE`, `NIL_RATED`, `EXEMPT`, or `NON_GST`; other codes, including `ZERO_RATED`, are invalid for catalogue use.
- `TAXABLE` requires `selected_tax_rate_id` to be an active GST Tax Rate currently eligible for the selected HSN through `company_hsn_sac_tax_rates`.
- `NIL_RATED` requires the same active eligible relationship and a numeric rate of exactly 0%; a 0% rate never changes the Base GST Nature by inference.
- `EXEMPT` and `NON_GST` require `selected_tax_rate_id` to be NULL; no artificial 0% rate is assigned.
- `business_segment_id`, when populated, must reference a Business Segment owned by the same Company; a direct nullable FK limits the SKU to at most one current Segment.
- `product_id` is immutable after creation. A parent/classification change inactivates the old SKU and creates a replacement under the correct Product.
- Historically used SKUs are inactivated rather than deleted; inactive is terminal, remains readable, and cannot be edited or reassigned.

**Relationships**
- Product 1:N SKUs
- Company HSN 1:N SKUs; the referenced row must have `classification_type = HSN`
- Tax Treatment master 1:N SKUs as Base GST Nature
- Business Segment 1:N SKUs (nullable from SKU)

**Why this table exists**
1. SKU is the actual billable goods identity.
2. It owns SKU code/UOM and final HSN selection rather than Product Category.
3. Nullable `selected_tax_rate_id` stores the current/default eligible rate only for Base GST Natures that require one; it must remain valid for `company_hsn_sac_code_id`.
4. The optional direct Business Segment relationship supports current management reporting without a mapping table.
5. TCS applicability-check behavior can be configured per SKU.
6. Removing it would make Product too coarse for variants, HSN/UOM or customer commercial lines.

**Current tax rule**
- Base GST Nature is a catalogue classification, not a numeric Tax Rate Type or the final Billing outcome. Validate the final nature/rate combination before the item is billable; a later Billing resolver derives the transaction result from Supply Type and other transaction context.

---

## 30. `cost_center_locations` — KEEP

**What data is stored**
- Named location-based reporting/cost-center groups such as `Noida Operations`.

**Columns and purpose**

`id`
- Type: UUID; Nullability: NOT NULL; Default: none; Key: PRIMARY KEY.
- Why: stable identity for a Location Cost Center independently of any one physical Company Location.

`company_id`
- Type: UUID; Nullability: NOT NULL; Default: none; FK: `companies.id`.
- Why: identifies the Company that owns the reporting group.

`name`
- Type: VARCHAR(150); Nullability: NOT NULL; Default: none; Constraint: UNIQUE with Company.
- Why: business-facing name for the location-based reporting group.

`code`
- Type: VARCHAR(50); Nullability: NULL; Default: none; Constraint: partial UNIQUE with Company when non-null.
- Why: optional Company-specific reporting/reference code.

`status`
- Type: VARCHAR(20); Nullability: NOT NULL; Default: none; Controlled values: `ACTIVE`, `INACTIVE`.
- Why: controls current availability without deleting historical identity.

`created_at`
- Type: TIMESTAMPTZ; Nullability: NOT NULL; Default: none.
- Why: records when the Location Cost Center row was created.

`updated_at`
- Type: TIMESTAMPTZ; Nullability: NOT NULL; Default: none.
- Why: records when the current row was last updated.

**Constraints and lifecycle**
- UNIQUE (`company_id`, `name`).
- Partial UNIQUE (`company_id`, `code`) WHERE `code IS NOT NULL`.
- CHECK (`status IN ('ACTIVE', 'INACTIVE')`).
- A referenced `company_locations.cost_center_location_id` must identify a Location Cost Center owned by the same Company. This ownership invariant requires backend/database enforcement and must not rely on frontend validation alone; the exact FK mechanism follows the repository's eventual same-Company enforcement convention.
- One physical Company Location has at most one current Location Cost Center because the nullable FK is stored directly on `company_locations`; one Location Cost Center may contain many Company Locations.
- This table stores the current stable master identity and is not effective-dated. Historically used Location Cost Centers are inactivated rather than deleted; finalized historical references remain unchanged. Adding a physical Location may assign it to an existing active reporting group.

**Relationships**
- Company 1:N Location Cost Centers
- Location Cost Center 1:N `company_locations` through `company_locations.cost_center_location_id`

**Why this table exists**
1. One reporting cost center can contain several physical Locations.
2. The reporting name (`Noida Operations`) is not necessarily identical to any one Location name.
3. It supports the agreed location-based cost-center reporting model without a generic cost-center engine.
4. A direct FK from Location makes membership simple because one Location belongs to max one current group.
5. It lets new Locations be assigned to an existing group without changing invoices/catalogues.
6. Removing it would force each physical Location to act as its own cost center and would not support grouping four Noida Locations into one reporting bucket.

---

## 31. `cost_center_business_segments` — KEEP

**What data is stored**
- Business Segments used directly as reporting/cost-center buckets.

**Columns and purpose**

`id`
- Type: UUID; Nullability: NOT NULL; Default: none; Key: PRIMARY KEY.
- Why: stable identity for the Company-owned Business Segment.

`company_id`
- Type: UUID; Nullability: NOT NULL; Default: none; FK: `companies.id`.
- Why: identifies the Company that owns the Segment.

`name`
- Type: VARCHAR(150); Nullability: NOT NULL; Default: none; Constraint: UNIQUE with Company.
- Why: required business-facing Segment name.

`code`
- Type: VARCHAR(50); Nullability: NULL; Default: none; Constraint: partial UNIQUE with Company when non-null.
- Why: optional Company-specific reporting/reference code.

`status`
- Type: VARCHAR(20); Nullability: NOT NULL; Default: none; Controlled values: `ACTIVE`, `INACTIVE`.
- Why: controls current Segment availability without deleting historical identity.

`created_at`
- Type: TIMESTAMPTZ; Nullability: NOT NULL; Default: none.
- Why: records when the Segment row was created.

`updated_at`
- Type: TIMESTAMPTZ; Nullability: NOT NULL; Default: none.
- Why: records when the current row was last updated.

**Constraints and lifecycle**
- UNIQUE (`company_id`, `name`).
- Partial UNIQUE (`company_id`, `code`) WHERE `code IS NOT NULL`.
- CHECK (`status IN ('ACTIVE', 'INACTIVE')`).
- Service Type and SKU each store a nullable direct `business_segment_id`; composite same-Company FKs prevent cross-Company references and each catalogue row can belong to at most one current Business Segment.
- This table stores the current stable master identity and is not effective-dated. Historically used Business Segments are inactivated rather than deleted; finalized historical references remain unchanged.

**Relationships**
- Company 1:N Business Segment Cost Centers
- Business Segment 1:N Service Types and 1:N SKUs through their nullable direct `business_segment_id` columns.

**Why this table exists**
1. Management wants Business Segment itself to function as one cost-center/reporting basis.
2. It avoids creating a second generic `cost_centers` row for the same business concept.
3. It lets services/goods be assigned to reporting segments.
4. It provides stable IDs/codes for filters and reports.
5. It remains distinct from Team and Location-based reporting.
6. Removing it would either lose segment reporting or recreate it as an unnecessary generic cost-center mapping.

---

## 32. `cost_center_teams` — KEEP

**What data is stored**
- Company-owned Team-based cost-center reporting buckets. A bucket may group multiple actual Company Teams but is not itself the operational Team master.

**Columns and purpose**

`id`
- Type: UUID; Nullability: NOT NULL; Default: none; Key: PRIMARY KEY.
- Why: stable identity for the Team-based reporting bucket independently of the actual Teams assigned to it.

`company_id`
- Type: UUID; Nullability: NOT NULL; Default: none; FK: `companies.id`.
- Why: identifies the Company that owns the reporting bucket and defines its Company scope.

`name`
- Type: VARCHAR(150); Nullability: NOT NULL; Default: none; Constraint: UNIQUE with Company.
- Why: required business-facing name for the reporting bucket, such as `Regulatory Operations`.

`code`
- Type: VARCHAR(50); Nullability: NULL; Default: none; Constraint: partial UNIQUE with Company when non-null.
- Why: optional Company-specific reporting/reference code.

`status`
- Type: VARCHAR(20); Nullability: NOT NULL; Default: none; Controlled values: `ACTIVE`, `INACTIVE`.
- Why: controls current reporting-bucket availability without deleting historical identity.

`created_at`
- Type: TIMESTAMPTZ; Nullability: NOT NULL; Default: none.
- Why: records when the reporting bucket was created.

`updated_at`
- Type: TIMESTAMPTZ; Nullability: NOT NULL; Default: none.
- Why: records when the reporting bucket was last updated.

**Constraints and lifecycle**
- UNIQUE (`company_id`, `name`).
- Partial UNIQUE (`company_id`, `code`) WHERE `code IS NOT NULL`.
- CHECK (`status IN ('ACTIVE', 'INACTIVE')`).
- This table is a reporting identity, not an IAM group and not the operational Team master.
- One Cost Center Team may group multiple actual Teams. An actual Team may reference zero or one Cost Center Team, so no Team-to-bucket mapping table is used.
- An assigned actual Team and its Cost Center Team must belong to the same Company. This invariant requires database/backend enforcement and must not rely on frontend validation alone; the exact FK mechanism follows the repository's same-Company enforcement convention.
- This table stores the current stable reporting-bucket identity and is not effective-dated. Historically used buckets are inactivated rather than deleted; finalized historical references remain unchanged.
- Mandatory assignment of every actual Team to a Cost Center Team is not required. Whether future Company activation/readiness requires complete coverage remains OPEN.

**Relationships**
- Company 1:N Cost-Center Teams
- Cost-Center Team 1:N actual `teams`

**Why this table exists**
1. Management reporting may need one bucket, such as `Regulatory Operations`, to combine several operational Teams.
2. It keeps the reporting grouping separate from actual Team identity and user membership history.
3. It supports stable Team-based invoice/SO/report filters without introducing a generic Cost Center master.
4. Actual Teams can move into or out of a reporting bucket without replacing either identity.
5. Removing it would prevent several operational Teams from reporting under one approved Cost Center Team bucket.

---

## 32A. `teams` — KEEP

**What data is stored**
- Actual Company-owned operational Teams, distinct from Cost Center Team reporting buckets and external IAM groups.

**Columns and purpose**

`id`
- Type: UUID; Nullability: NOT NULL; Default: none; Key: PRIMARY KEY.
- Why: stable identity for the actual Company Team while membership and reporting-bucket assignment change over time.

`company_id`
- Type: UUID; Nullability: NOT NULL; Default: none; FK: `companies.id`.
- Why: identifies the Company that owns the actual Team and defines its Company scope.

`cost_center_team_id`
- Type: UUID; Nullability: NULL; Default: none; FK: `cost_center_teams.id`.
- Why: optionally assigns the actual Team to one Team-based cost-center reporting bucket.

`name`
- Type: VARCHAR(150); Nullability: NOT NULL; Default: none; Constraint: UNIQUE with Company.
- Why: required business-facing operational Team name, such as `BIS Team`.

`status`
- Type: VARCHAR(20); Nullability: NOT NULL; Default: none; Controlled values: `ACTIVE`, `INACTIVE`.
- Why: controls current Team availability without deleting historical identity or membership history.

`created_at`
- Type: TIMESTAMPTZ; Nullability: NOT NULL; Default: none.
- Why: records when the actual Team was created.

`updated_at`
- Type: TIMESTAMPTZ; Nullability: NOT NULL; Default: none.
- Why: records when the actual Team was last updated.

**Constraints and lifecycle**
- UNIQUE (`company_id`, `name`).
- CHECK (`status IN ('ACTIVE', 'INACTIVE')`).
- `cost_center_team_id` is nullable: an actual Team may be unassigned or may belong to one Cost Center Team, but never more than one in the current scope.
- The referenced Cost Center Team must belong to the same Company as the actual Team. This invariant requires database/backend enforcement and must not rely on frontend validation alone; the exact FK mechanism follows the repository's same-Company enforcement convention.
- The direct nullable FK implements the approved 1:N relationship. No Team-to-Cost-Center-Team mapping table is introduced.
- An actual Team is an ERP Company business identity, not an IAM group. IAM/Keycloak authenticates users; ERP owns Team membership history.
- Historically used Teams are inactivated rather than deleted; membership and finalized transaction history remain unchanged.

**Relationships**
- Company 1:N actual Teams
- Cost-Center Team 1:N actual Teams
- Actual Team 1:N Team Memberships

**Why this table exists**
1. Operational Team identity and Team-based cost-center grouping are different business concepts.
2. One reporting bucket may group several actual Teams without collapsing them into one Team.
3. User membership history belongs to the actual Team rather than the reporting bucket.
4. The nullable direct relationship permits uncovered Teams without creating an M:N mapping structure.

---

## 33. `team_memberships` — KEEP

**What data is stored**
- Which user belongs to which actual Company Team and during what period.

**Columns and purpose**

`id`
- Type: UUID; Nullability: NOT NULL; Default: none; Key: PRIMARY KEY.
- Why: stable identity for one effective-dated user-to-Team membership period.

`team_id`
- Type: UUID; Nullability: NOT NULL; Default: none; FK: `teams.id`.
- Why: identifies the actual Company-owned Team to which the user belongs. Users do not belong directly to Cost Center Team reporting buckets.

`user_subject_id` — **physical field OPEN**
- Preferred candidate: VARCHAR(255); Nullability: NOT NULL; Default: none.
- Why: identifies the authenticated user/IAM subject whose business Team membership ERP records.
- The repository has no frozen internal User table or approved external-subject persistence convention. The final column name, datatype and FK/reference form remain OPEN so this table does not invent a second user identity model.

`valid_from`
- Type: DATE; Nullability: NOT NULL; Default: none.
- Why: first date on which the membership applies.

`valid_to`
- Type: DATE; Nullability: NULL; Default: none.
- Why: last date on which a closed historical membership applies; null means open-ended.

`status`
- Type: VARCHAR(20); Nullability: NOT NULL; Default: none; Controlled values: `ACTIVE`, `INACTIVE`.
- Why: records whether the membership row is currently operational while retaining its dated history.

`created_at`
- Type: TIMESTAMPTZ; Nullability: NOT NULL; Default: none.
- Why: records when the membership row was created.

`updated_at`
- Type: TIMESTAMPTZ; Nullability: NOT NULL; Default: none.
- Why: records when the membership row was last updated.

**Constraints and lifecycle**
- CHECK (`valid_to IS NULL OR valid_to >= valid_from`).
- CHECK (`status IN ('ACTIVE', 'INACTIVE')`).
- Business rule: one active actual-Team membership per user within the applicable Company scope. A user may belong to multiple Companies.
- Exact PostgreSQL overlap/exclusion or uniqueness enforcement remains OPEN until the physical user reference and Company/user membership scope are frozen; no speculative constraint is introduced.
- Team Company scope comes from `teams.company_id`; the membership applies within that actual Team's Company.
- When a user moves Teams, close the prior row with `valid_to` and create a new row. Do not overwrite or delete historical membership.

**Relationships**
- Actual Team 1:N Memberships
- IAM User 1:N Membership histories

**Why this table exists**
1. Actual Team identity and user membership are different concepts.
2. A Team can contain many users.
3. Membership changes over time while historical reporting may need old assignments.
4. Keycloak can authenticate the user, but Company business Team membership belongs to ERP domain data.
5. It supports the current rule of one active actual-Team membership at the agreed scope once that scope is frozen.
6. Removing it would force user IDs directly into Team columns or lose membership history.

---

## 34. `company_cost_center_settings` — KEEP

**What data is stored**
- Whether Company cost-center reporting is enabled and which current bases are used.

**Columns and purpose**

`company_id`
- Type: UUID; Nullability: NOT NULL; Default: none; Key: PRIMARY KEY; FK: `companies.id`.
- Why: creates the one authoritative Cost Center settings row for the Company.

`cost_center_reporting_enabled`
- Type: BOOLEAN; Nullability: NOT NULL; Default: false.
- Why: enables or disables Cost Center reporting as a whole.

`business_segment_enabled`
- Type: BOOLEAN; Nullability: NOT NULL; Default: false.
- Why: enables Business Segment setup and use for this Company.

`team_enabled`
- Type: BOOLEAN; Nullability: NOT NULL; Default: false.
- Why: enables Cost Center Team bucket setup, actual Team assignment, and Team-based reporting for this Company.

`location_enabled`
- Type: BOOLEAN; Nullability: NOT NULL; Default: false.
- Why: enables Location Cost Center setup and use for this Company.

`created_at`
- Type: TIMESTAMPTZ; Nullability: NOT NULL; Default: none.
- Why: records when the Company's settings row was created.

`updated_at`
- Type: TIMESTAMPTZ; Nullability: NOT NULL; Default: none.
- Why: records when the Company's settings row was last updated.

**Constraints and lifecycle**
- Company 1:1 settings through `company_id` as both PRIMARY KEY and FK.
- CHECK (`cost_center_reporting_enabled = true OR (business_segment_enabled = false AND team_enabled = false AND location_enabled = false)`).
- A completed, usable configuration with Cost Center reporting enabled must select at least one of Business Segment, Team, or Location. Whether an enabled but incomplete draft may be saved is not frozen, so no reverse database CHECK is added yet.
- Disabled or historical Segment, Team, or Location Cost Center master rows do not enable a basis. This settings row is authoritative.
- Different Companies may enable any combination of the three current bases, or disable Cost Center reporting completely.
- Disable reporting by setting the master flag and all basis flags to false rather than deleting the settings row.
- The row stores current Company enablement rather than an effective-dated history. Changes require normal configuration audit; master-row existence is not an enablement signal.

**Relationships**
- Company 1:1 Cost-Center Settings

**Why this table exists**
1. Existence of old master rows should not imply the feature is currently enabled.
2. It records the user's explicit Company Configuration choices.
3. UI can show only selected reporting setup sections.
4. Validation/reporting can distinguish disabled vs incomplete configuration.
5. It avoids a generic policy engine while giving one authoritative enablement row.
6. Removing it would force the system to infer intent from whether Segment/Team/Location rows happen to exist.

---

# 6. AR Compliance / Numbering / Output Configuration

## 35. `company_luts` — KEEP

**What data is stored**
- LUT reference and validity for a seller GST Registration and Financial Year.

**Columns and purpose**

`id`
- Type: UUID; Nullability: NOT NULL; Default: none; Key: PRIMARY KEY.
- Why: stable LUT configuration identity retained for historical transaction context.

`company_id`
- Type: UUID; Nullability: NOT NULL; Default: none; FK: `companies.id`.
- Why: identifies the Company that owns the LUT configuration.

`gst_registration_id`
- Type: UUID; Nullability: NOT NULL; Default: none; FK: `company_gst_registrations.id`.
- Why: identifies the exact seller GST Registration to which the LUT applies.

`financial_year_id`
- Type: UUID; Nullability: NOT NULL; Default: none; FK: `financial_years.id`.
- Why: identifies the exact Financial Year for which the LUT is configured.

`lut_reference`
- Type: VARCHAR(100); Nullability: NOT NULL; Default: none.
- Why: stores the business/statutory LUT ARN or reference; it is not globally unique under the current requirements.

`valid_from`
- Type: DATE; Nullability: NOT NULL; Default: none.
- Why: first date on which this LUT record is applicable.

`valid_to`
- Type: DATE; Nullability: NULL; Default: none.
- Why: optional last date of applicability within the associated Financial Year/context.

`status`
- Type: VARCHAR(20); Nullability: NOT NULL; Default: none; Controlled values: `ACTIVE`, `INACTIVE`.
- Why: controls current eligibility while preserving prior LUT identities.

`created_at`
- Type: TIMESTAMPTZ; Nullability: NOT NULL; Default: none.
- Why: records when the LUT row was created.

`updated_at`
- Type: TIMESTAMPTZ; Nullability: NOT NULL; Default: none.
- Why: records when the current LUT row was last updated.

**Constraints and lifecycle**
- CHECK (`valid_to IS NULL OR valid_to >= valid_from`).
- CHECK (`status IN ('ACTIVE', 'INACTIVE')`).
- Partial UNIQUE (`gst_registration_id`, `financial_year_id`) WHERE `status = 'ACTIVE'`.
- `gst_registration_id` and `financial_year_id` must each belong to `company_id`. Same-Company integrity requires backend/database enforcement and must not rely on frontend validation.
- `lut_reference` has no global uniqueness constraint.
- A new Financial Year or replacement LUT creates/retains a distinct row rather than overwriting referenced historical context. Historically used rows are inactivated, not hard-deleted.

**Relationships**
- Company 1:N LUTs
- GST Registration 1:N LUTs
- Financial Year 1:N LUTs

**Why this table exists**
1. LUT is GST Registration-specific, not just Company-wide.
2. LUT is Financial-Year/period specific and history must be retained.
3. Billing must validate the applicable LUT before finalization of relevant supply routes.
4. A new FY should create/use a new applicable LUT record rather than overwrite old history.
5. It gives invoices an auditable source/context even though final documents snapshot key values.
6. Removing it would force LUT into GST Registration or Company and lose FY-specific history.

**Current product rule**
- Valid applicable LUT is required for the current without-payment routes **EXPWOP** and **SEZWOP**.
- **EXPWP** and **SEZWP** do not require LUT merely because they are Export or SEZ routes.

**LUT document scope**
- LUT document upload is not required in the current MVP. No file FK, storage/object key, URL, PDF or attachment field is included. If upload is approved later, it uses `ObjectStorage` → `stored_files` → a typed LUT FK through a separate review.

---

## 36. `document_sequences` — KEEP

**What data is stored**
- Numbering-series identity, format and independent counter; not all applicability dimensions.

**Columns and purpose**

`id`
- Type: UUID; Nullability: NOT NULL; Default: none; Key: PRIMARY KEY.
- Why: stable identity for one numbering series and its independent counter.

`company_id`
- Type: UUID; Nullability: NOT NULL; Default: none; FK: `companies.id`.
- Why: identifies the Company that owns and consumes the series.

`financial_year_id`
- Type: UUID; Nullability: NOT NULL; Default: none; FK: `financial_years.id`.
- Why: identifies the exact Financial Year whose numbering configuration and counter apply.

`document_type`
- Type: VARCHAR(10); Nullability: NOT NULL; Default: none; Controlled values: `PI`, `TI`, `CN`, `DN`.
- Why: identifies the AR document family that consumes the series.

`series_name`
- Type: VARCHAR(100); Nullability: NOT NULL; Default: none.
- Why: business/admin-facing identity of the series within its Company, Financial Year and document type.

`format`
- Type: VARCHAR(255); Nullability: NOT NULL; Default: none.
- Why: validated numbering-format/token pattern. It is not a PDF template and is not executable code.

`prefix`
- Type: VARCHAR(50); Nullability: NULL; Default: none.
- Why: optional separately configured literal prefix when the selected format uses one.

`start_number`
- Type: BIGINT; Nullability: NOT NULL; Default: none.
- Why: first permitted numeric counter for the series.

`next_number`
- Type: BIGINT; Nullability: NOT NULL; Default: none.
- Why: next counter value to consume atomically at approved finalization.

`padding`
- Type: SMALLINT; Nullability: NOT NULL; Default: none.
- Why: numeric rendering width; for example, value `1` with padding `4` renders as `0001`.

`priority`
- Type: INTEGER; Nullability: NULL; Default: none.
- Why: reserved optional sequence-selection preference for the approved future priority-resolution direction; current priority semantics and positive-only validation remain OPEN.

`status`
- Type: VARCHAR(20); Nullability: NOT NULL; Default: none; Controlled values: `ACTIVE`, `INACTIVE`.
- Why: controls availability for future allocation without erasing used series history.

`created_at`
- Type: TIMESTAMPTZ; Nullability: NOT NULL; Default: none.
- Why: records when the sequence row was created.

`updated_at`
- Type: TIMESTAMPTZ; Nullability: NOT NULL; Default: none.
- Why: records when the sequence configuration/counter row was last updated.

**Constraints and lifecycle**
- UNIQUE (`company_id`, `financial_year_id`, `document_type`, `series_name`).
- CHECK (`document_type IN ('PI', 'TI', 'CN', 'DN')`).
- CHECK (`start_number >= 1`).
- CHECK (`next_number >= start_number`).
- CHECK (`padding >= 1`); no maximum padding is invented.
- CHECK (`status IN ('ACTIVE', 'INACTIVE')`).
- `financial_year_id` must belong to `company_id`; same-Company integrity must be enforced outside frontend-only validation.
- No `priority` CHECK is frozen because current selection semantics remain OPEN.
- Final number allocation occurs only at approved finalization and atomically consumes the selected row. An idempotent retry of an already-finalized operation must not consume another number.
- Parallel series keep independent counters. Cancellation never releases an issued number, and a used counter is never reset/reused.
- Prior-FY and used series remain retained/inactive as applicable. Later sequence changes never rewrite issued document numbers.
- After the first committed final number is issued from a series, its numbering identity/format basis (`financial_year_id`, `document_type`, `format`, `prefix`, `start_number`, `padding`) and material eligibility scope must not be edited in place in a way that reinterprets issued numbers. Retire the used series and create a new series for materially different future numbering configuration.

**Relationships**
- Company 1:N Document Sequences
- Financial Year 1:N Document Sequences
- Document Sequence 1:N Conditions

**Why this table exists**
1. Different PI/TI/CN/DN series can run in parallel with independent counters.
2. Number format/counter is a real persistent financial configuration, not a transient setting.
3. FY-specific rows allow yearly reset/change without rewriting prior series.
4. Finalization can atomically lock/increment the selected sequence.
5. Cancelled issued numbers remain consumed because the sequence owns the counter history.
6. Removing it would force numbering logic into document code and make parallel/configurable series impossible.

---

## 37. `document_sequence_conditions` — KEEP

**What data is stored**
- Controlled applicability conditions telling when a Document Sequence is eligible.

**Columns and purpose**

`id`
- Type: UUID; Nullability: NOT NULL; Default: none; Key: PRIMARY KEY.
- Why: stable identity for one controlled sequence-eligibility condition.

`document_sequence_id`
- Type: UUID; Nullability: NOT NULL; Default: none; FK: `document_sequences.id`.
- Why: identifies the numbering series whose eligibility this condition restricts.

`condition_type`
- Type: VARCHAR(40); Nullability: NOT NULL; Default: none.
- Why: identifies which supported transaction/configuration fact is tested. Current candidate vocabulary includes `SUPPLY_TYPE`, `GST_REGISTRATION`, `LOCATION`, `BUSINESS_SEGMENT`, `TEAM`, and `TRANSACTION_NATURE`, but the exact first-release allowed set remains OPEN and is not frozen as a database CHECK yet.

`operator`
- Type: VARCHAR(20); Nullability: NOT NULL; Default: none.
- Why: stores the controlled comparison operation. Exact allowed vocabulary remains OPEN; no regex, script, formula or numeric-comparison operator is approved.

`condition_value`
- Type: VARCHAR(255); Nullability: NOT NULL; Default: none.
- Why: stores the controlled value interpreted according to `condition_type`, such as a Supply Type code or applicable domain UUID text.

`created_at`
- Type: TIMESTAMPTZ; Nullability: NOT NULL; Default: none.
- Why: records when the condition was created.

`updated_at`
- Type: TIMESTAMPTZ; Nullability: NOT NULL; Default: none.
- Why: records when the current condition row was last updated.

**Constraints, validation and lifecycle**
- The exact first-release `condition_type` allow-list remains OPEN, so no database CHECK freezes the six candidate values yet. The application/backend must still use controlled vocabulary and reject unsupported types.
- No ordinary FK is added to `condition_value`, because its domain depends on `condition_type`.
- Backend/domain validation must validate the supported type, approved operator, value shape/existence, active/valid state where applicable, and same-Company ownership through the parent sequence.
- Exact operator vocabulary and whether multiple conditions use AND-only or another approved combination remain OPEN. No nested groups, OR trees, expressions, scripts, formulas, regex or JSON rules are introduced.
- Once the parent sequence has issued a committed final number, its eligibility scope/conditions are treated as historical configuration and are not edited or deleted in place to change future eligibility. Retain/retire the used series and create a new series/configuration for a materially different future scope.

**Controlled condition types may include**
- SUPPLY_TYPE
- GST_REGISTRATION
- LOCATION
- BUSINESS_SEGMENT
- TEAM
- TRANSACTION_NATURE

**Relationships**
- Document Sequence 1:N Conditions

**Why this table exists**
1. Numbering can depend on different parameters such as Export, GSTIN, Location, Segment or Team.
2. Putting every possible parameter as nullable columns would continuously alter `document_sequences` schema.
3. New supported condition types can be added through controlled backend vocabulary.
4. Priority/condition selection can evolve later without replacing the core counter table.
5. It supports current 0/1/many eligible-series resolution and future automatic priority selection.
6. Removing it would either hardcode sequence selection or create a wide, brittle nullable-column table.

**Important**
- This is a controlled numbering-condition model, **not** a generic executable rules engine.

---

## 38. `payment_terms` — KEEP

**What data is stored**
- Reusable Company AR payment terms such as Immediate, Net 30, Net 45.

**Columns and purpose**

`id`
- Type: UUID; Nullability: NOT NULL; Default: none; Key: PRIMARY KEY.
- Why: stable identity for a reusable Company payment term.

`company_id`
- Type: UUID; Nullability: NOT NULL; Default: none; FK: `companies.id`.
- Why: identifies the Company that owns the term.

`name`
- Type: VARCHAR(100); Nullability: NOT NULL; Default: none.
- Why: business-facing term name such as `Immediate` or `Net 30`; current requirements do not freeze name uniqueness.

`code`
- Type: VARCHAR(50); Nullability: NOT NULL; Default: none.
- Why: stable Company-specific operational/reference code.

`term_type`
- Type: VARCHAR(20); Nullability: NOT NULL; Default: none; Controlled values: `IMMEDIATE`, `NET_DAYS`.
- Why: selects immediate payment or a positive credit-day calculation.

`credit_days`
- Type: SMALLINT; Nullability: NOT NULL; Default: none.
- Why: number of days used to derive due date; it is zero only for `IMMEDIATE`.

`is_default`
- Type: BOOLEAN; Nullability: NOT NULL; Default: false.
- Why: marks the active term preselected for the Company without a separate billing-defaults table.

`status`
- Type: VARCHAR(20); Nullability: NOT NULL; Default: none; Controlled values: `ACTIVE`, `INACTIVE`.
- Why: controls current selection while retaining historically used terms.

`created_at`
- Type: TIMESTAMPTZ; Nullability: NOT NULL; Default: none.
- Why: records when the term was created.

`updated_at`
- Type: TIMESTAMPTZ; Nullability: NOT NULL; Default: none.
- Why: records when the current term row was last updated.

**Constraints and lifecycle**
- UNIQUE (`company_id`, `code`).
- CHECK (`term_type IN ('IMMEDIATE', 'NET_DAYS')`).
- CHECK (`(term_type = 'IMMEDIATE' AND credit_days = 0) OR (term_type = 'NET_DAYS' AND credit_days > 0)`).
- CHECK (`status IN ('ACTIVE', 'INACTIVE')`).
- CHECK (`NOT is_default OR status = 'ACTIVE'`); an inactive Payment Term cannot remain marked as the Company's default.
- Partial UNIQUE (`company_id`) WHERE `is_default = true AND status = 'ACTIVE'`.
- No arbitrary maximum credit-days limit or Company/name uniqueness constraint is added.
- Historically used terms are inactivated rather than hard-deleted. A Sales Order or finalized invoice preserves the selected term/credit-days/due-date truth; changing current configuration does not recalculate prior approved transactions.
- Installment schedules are outside this table and current task.

**Relationships**
- Company 1:N Payment Terms
- Sales Orders/Invoices later reference a selected term/snapshot

**Why this table exists**
1. Credit period is reused across clients/SOs/invoices rather than retyped each time.
2. One Company may maintain several named terms.
3. `is_default` removes the need for a separate `ar_billing_defaults` table.
4. Due-date derivation can use a controlled term definition.
5. Future installment schedules can extend the concept without changing current simple terms.
6. Removing it would duplicate `credit_days` throughout commercial/financial transactions.

---

## 39. `company_document_branding` — KEEP

**What data is stored**
- Reusable Company document branding assets/content independent of a specific PI/TI/CN/DN layout version.

**Columns and purpose**

`id`
- Type: UUID; Nullability: NOT NULL; Default: none; Key: PRIMARY KEY.
- Why: stable identity for one reusable Company branding configuration.

`company_id`
- Type: UUID; Nullability: NOT NULL; Default: none; FK: `companies.id`.
- Why: identifies the Company that owns the branding content and assets.

`logo_file_id`
- Type: UUID; Nullability: NULL; Default: none; FK: `stored_files.id`.
- Why: optional stable identity of the immutable stored logo object.

`signature_file_id`
- Type: UUID; Nullability: NULL; Default: none; FK: `stored_files.id`.
- Why: optional stable identity of the stored authorized-signature asset.

`stamp_file_id`
- Type: UUID; Nullability: NULL; Default: none; FK: `stored_files.id`.
- Why: optional stable identity of the stored Company stamp/seal asset.

`header_text`
- Type: TEXT; Nullability: NULL; Default: none.
- Why: optional reusable document-header wording.

`footer_text`
- Type: TEXT; Nullability: NULL; Default: none.
- Why: optional reusable document-footer wording.

`status`
- Type: VARCHAR(20); Nullability: NOT NULL; Default: none; Controlled values: `ACTIVE`, `INACTIVE`.
- Why: identifies the one current branding row while retaining retired history.

`created_at`
- Type: TIMESTAMPTZ; Nullability: NOT NULL; Default: `CURRENT_TIMESTAMP`.
- Why: records when the branding row was created.

`updated_at`
- Type: TIMESTAMPTZ; Nullability: NOT NULL; Default: `CURRENT_TIMESTAMP`.
- Why: records when the current branding row was last updated.

**Constraints and lifecycle**
- CHECK (`status IN ('ACTIVE', 'INACTIVE')`).
- Partial UNIQUE index on (`company_id`) where `status = 'ACTIVE'`; a Company has at most one current branding row.
- Every non-null file FK must reference a `stored_files` row owned by `company_id`; cross-Company asset references are invalid and require backend/database enforcement.
- Branding stores no binary bytes, object/storage key, hash, content type, size, URL or R2/provider field; `stored_files` owns that metadata.
- A branding change does not mutate the current row. It retires that row and creates a new `ACTIVE` row. If a current template selection exists, the same transaction retires it and creates a new selection version with the unchanged `template_key` and new branding identity.
- No separate generic branding-version table is introduced. Final issued PDFs remain immutable evidence outside this configuration row.

**Relationships**
- Company 1:N immutable Branding records/versions, with zero or one current row
- Document Templates reference the chosen branding content/assets

**Why this table exists**
1. Company identity assets and document layout are different responsibilities.
2. The same logo/signature/stamp can be reused across several document types.
3. It avoids duplicating binary/object references in every template row.
4. Branding can change for future documents without changing historical finalized output.
5. It supports controlled Company-specific presentation without a drag/drop designer.
6. Removing it would duplicate reusable branding data across PI/TI/CN/DN templates.

---

## 40. `company_document_templates` — KEEP

**What data is stored**
- Immutable versions of a Company's single billing-document template selection. One current selection applies to PI, TI, CN, and DN.

**Columns and purpose**

`id`
- Type: UUID; Nullability: NOT NULL; Default: none; Key: PRIMARY KEY.
- Why: stable identity for one Company document-template configuration version.

`company_id`
- Type: UUID; Nullability: NOT NULL; Default: none; FK: `companies.id`.
- Why: identifies the Company that owns the template version.

`document_type`
- Type: VARCHAR(10); Nullability: NULL; Default: none; legacy controlled values when non-null: `PI`, `TI`, `CN`, `DN`.
- Why: retained only to preserve pre-Migration-0027 historical rows. It is NULL for every current/`ACTIVE` Company-wide selection and does not govern selection or application behavior.

`branding_id`
- Type: UUID; Nullability: NULL; Default: none; FK: `company_document_branding.id`.
- Why: optionally selects the reusable branding row pinned by this template version.

`template_key`
- Type: VARCHAR(100); Nullability: NOT NULL; Default: none.
- Why: identifies a supported code-owned renderer/layout identity such as `STANDARD_V1`; configuration APIs validate it against the application registry. It is not an object key, uploaded HTML/CSS/JavaScript/layout JSON, or executable user code.

`version_no`
- Type: INTEGER; Nullability: NOT NULL; Default: none.
- Why: orders immutable selection versions within the Company.

`show_logo`
- Type: BOOLEAN; Nullability: NULL; Default: none.
- Why: legacy/non-governing physical field retained without schema churn; it is not exposed as an MVP Company setting.

`show_bank_details`
- Type: BOOLEAN; Nullability: NULL; Default: none.
- Why: legacy/non-governing physical field retained without schema churn; it is not exposed as an MVP Company setting.

`show_signature`
- Type: BOOLEAN; Nullability: NULL; Default: none.
- Why: legacy/non-governing physical field retained without schema churn; it is not exposed as an MVP Company setting.

`show_hsn_sac`
- Type: BOOLEAN; Nullability: NULL; Default: none.
- Why: legacy/non-governing physical field retained without schema churn; it is not exposed as an MVP Company setting.

`show_customer_reference`
- Type: BOOLEAN; Nullability: NULL; Default: none.
- Why: legacy/non-governing physical field retained without schema churn; it is not exposed as an MVP Company setting.

`status`
- Type: VARCHAR(20); Nullability: NOT NULL; Default: none; Controlled values: `ACTIVE`, `INACTIVE`.
- Why: controls availability for new document rendering while retaining used versions.

`created_at`
- Type: TIMESTAMPTZ; Nullability: NOT NULL; Default: `CURRENT_TIMESTAMP`.
- Why: records when this template version was created.

`updated_at`
- Type: TIMESTAMPTZ; Nullability: NOT NULL; Default: `CURRENT_TIMESTAMP`.
- Why: records when the current version row was last updated before it became historically pinned.

**Constraints and lifecycle**
- CHECK (`document_type IN ('PI', 'TI', 'CN', 'DN')`).
- CHECK (`version_no >= 1`).
- CHECK (`status IN ('ACTIVE', 'INACTIVE')`).
- CHECK (`status <> 'ACTIVE' OR document_type IS NULL`); current selections are Company-wide.
- UNIQUE (`company_id`, `version_no`).
- Partial UNIQUE index on (`company_id`) where `status = 'ACTIVE'`; a Company has at most one current template selection.
- A non-null `branding_id` must reference branding owned by the same `company_id`; cross-Company branding is invalid and requires backend/database enforcement.
- PI/TI/CN/DN do not form a selection key. The current template is selected once at Company level and future billing code will consume it without a per-document choice.
- The existing `show_*` columns are nullable legacy fields. New selections leave them NULL, the MVP API does not expose them, and no `show_stamp` column is added. The code-owned renderer controls presentation.
- A template change retires the current row and creates a new `ACTIVE` version. Historical versions remain retained and are not rewritten or hard-deleted.
- Migration 0027 retires every pre-existing `ACTIVE` per-document-type template row and every pre-existing `ACTIVE` branding row rather than guessing a winning current configuration. It deterministically renumbers retained template history by (`created_at`, `id`) within each Company. An administrator must then make an explicit Company-wide selection and, if wanted, create current branding.
- A finalized document later pins its template/output context and immutable PDF through Billing's artifact/snapshot design. This table stores no rendered PDF FK or binary.

**Relationships**
- Company 1:N Document Template Selection Versions, with zero or one current row
- Branding 1:N Templates

**Why this table exists**
1. One Company selection gives PI/TI/CN/DN a consistent approved layout without repeated document-time selection.
2. Selection versioning lets future output change without overwriting historical configuration.
3. It separates layout choice from reusable branding assets.
4. The code-owned renderer, rather than Company-configurable show/hide flags, controls MVP presentation and mandatory output.
5. It supports future additional standard templates without a generic HTML builder.
6. Removing it would force one hardcoded layout for every Company.

**Rendering boundary**
- Structured approved snapshot → server-side template identified by `template_key`/version → PDF renderer → immutable PDF artifact → `stored_files`/`ObjectStorage`.
- Template configuration and final output artifact remain separate identities.

---

# 7. Delivery / Reminder / Approval Configuration Closely Related to Company Setup

## 41. `email_provider_configs` — KEEP (Shared Infrastructure)

**Purpose:**
Shared email-provider configuration identity reusable by AR and potentially future modules.
Secrets must NOT be stored directly in PostgreSQL.

**Columns:**

`id`
- Type: UUID
- Nullability: NOT NULL
- Default: none
- PK/FK/Constraints: PRIMARY KEY
- Why: Unique identifier for the provider configuration.

`tenant_id`
- Type: UUID
- Nullability: NOT NULL
- Default: none
- PK/FK/Constraints: FK -> tenants.id
- Why: Ensures provider configuration is isolated to the correct Tenant.

`company_id`
- Type: UUID
- Nullability: NULL
- Default: none
- PK/FK/Constraints: FK -> companies.id
- Why: Links provider configuration to a specific Company when not shared at the Tenant level.

`provider_type`
- Type: VARCHAR(30)
- Nullability: NOT NULL
- Default: none
- Why: Defines the underlying email service (e.g., SMTP, SendGrid).

`sender_identity`
- Type: VARCHAR(320)
- Nullability: NOT NULL
- Default: none
- Why: Verified from-address or domain identity registered with the provider.

`secret_reference`
- Type: VARCHAR(500)
- Nullability: NOT NULL
- Default: none
- Why: External reference/URI to the actual credential in a secure secret manager.

`status`
- Type: VARCHAR(20)
- Nullability: NOT NULL
- Default: none
- PK/FK/Constraints: CHECK (status IN ('ACTIVE', 'INACTIVE'))
- Why: Active/inactive lifecycle state of the configuration.

`created_at`
- Type: TIMESTAMPTZ
- Nullability: NOT NULL
- Default: none
- Why: Record creation timestamp.

`updated_at`
- Type: TIMESTAMPTZ
- Nullability: NOT NULL
- Default: none
- Why: Record last-update timestamp.

**Rules:**
- `CHECK (status IN ('ACTIVE', 'INACTIVE'))`

**Meaning:**
- `company_id IS NULL` → provider configuration may be Tenant-shared
- `company_id IS NOT NULL` → provider configuration is Company-specific

If `company_id` is present, `companies.tenant_id` must equal `email_provider_configs.tenant_id`.

**Do not store:**
- SMTP password
- API key
- OAuth secret
- refresh token
- provider password

`secret_reference` stores only the approved secret-manager/config reference.
Do NOT freeze the exact `provider_type` vocabulary unless already approved.
Do NOT add provider-specific fields.

---

## 42. `company_invoice_delivery_settings` — KEEP

**Purpose:**
One current Company-level AR outgoing invoice-email configuration/default row.

**Columns:**

`company_id`
- Type: UUID
- Nullability: NOT NULL
- Default: none
- PK/FK/Constraints: PRIMARY KEY, FK -> companies.id
- Why: Links settings 1:1 to the Company.

`automatic_sending_enabled`
- Type: BOOLEAN
- Nullability: NOT NULL
- Default: false
- Why: Explicit ON/OFF control for automatic invoice email delivery.

`email_provider_config_id`
- Type: UUID
- Nullability: NULL
- Default: none
- PK/FK/Constraints: FK -> email_provider_configs.id
- Why: Selects the shared email provider infrastructure to use for this Company.

`sender_email`
- Type: VARCHAR(320)
- Nullability: NULL
- Default: none
- Why: Default From address used when resolving outgoing invoice delivery.

`reply_to_email`
- Type: VARCHAR(320)
- Nullability: NULL
- Default: none
- Why: Default Reply-To address for outgoing invoice emails.

`default_email_template_key`
- Type: VARCHAR(100)
- Nullability: NULL
- Default: none
- Why: Reference to the server-side email-body template to use.

`default_cc`
- Type: VARCHAR(320)[]
- Nullability: NULL
- Default: none
- Why: Array of default CC addresses for outgoing invoice emails.

`created_at`
- Type: TIMESTAMPTZ
- Nullability: NOT NULL
- Default: none
- Why: Record creation timestamp.

`updated_at`
- Type: TIMESTAMPTZ
- Nullability: NOT NULL
- Default: none
- Why: Record last-update timestamp.

**Important:**
`automatic_sending_enabled = false` means AUTO SEND OFF. It does NOT mean MANUAL SEND FORBIDDEN. Authorized manual sending remains possible.

Runtime validation before an actual send must confirm:
- applicable active provider
- valid sender
- resolved recipients
- final document artifact/PDF exists

Actual Customer recipients are NOT stored in Company Configuration. They come from Customer/Contact/Document context.

**Email Template Identity:**
Do NOT incorrectly reference `company_document_templates` for email-body templates. That table represents financial PDF/document presentation.
Use `default_email_template_key VARCHAR(100) NULL` for a controlled server-side email-template resource unless an authoritative current email-template master already exists elsewhere.

**Delivery Execution Boundary:**
Financial finalization/approval → durable delivery intent/request → asynchronous worker → provider attempt → sent/failed history.
SMTP/provider network calls must not run inside the invoice financial finalization transaction.
Email delivery failure must NOT reverse approval, release invoice number, remove receivable, or change finalized financial truth.

---

## 43. `reminder_policies` — KEEP

**Purpose:**
One current default Company reminder policy.

**Columns:**

`id`
- Type: UUID
- Nullability: NOT NULL
- Default: none
- PK/FK/Constraints: PRIMARY KEY
- Why: Unique identifier for the reminder policy.

`company_id`
- Type: UUID
- Nullability: NOT NULL
- Default: none
- PK/FK/Constraints: UNIQUE, FK -> companies.id
- Why: Links the policy 1:1 to the Company as the default behaviour.

`enabled`
- Type: BOOLEAN
- Nullability: NOT NULL
- Default: false
- Why: Master ON/OFF control for Company reminder evaluation.

`send_time`
- Type: TIME WITHOUT TIME ZONE
- Nullability: NULL
- Default: none
- Why: Preferred local time of day to trigger reminders, interpreted in the Company time zone.

`default_template_key`
- Type: VARCHAR(100)
- Nullability: NULL
- Default: none
- Why: Default reminder email template key unless overridden by the schedule step.

`created_at`
- Type: TIMESTAMPTZ
- Nullability: NOT NULL
- Default: none
- Why: Record creation timestamp.

`updated_at`
- Type: TIMESTAMPTZ
- Nullability: NOT NULL
- Default: none
- Why: Record last-update timestamp.

`enabled` is the current policy ON/OFF control.
`send_time` is interpreted using `companies.base_timezone` or the approved Company time-zone field. Do not store another timezone on the reminder policy.

**Reminder Template:**
Use `default_template_key VARCHAR(100) NULL` unless a separately approved reminder/email-template master already exists. Do not point Reminder email content at the PDF/document-template table.

**Reminder Precedence:**
Preserve: Company default → Customer override → Invoice override.
Invoice-level control has highest precedence for that invoice. Do NOT copy Company schedule rows into every Customer or Invoice.

---

## 44. `reminder_schedule_rules` — KEEP

**Columns:**

`id`
- Type: UUID
- Nullability: NOT NULL
- Default: none
- PK/FK/Constraints: PRIMARY KEY
- Why: Unique identifier for the reminder schedule rule.

`reminder_policy_id`
- Type: UUID
- Nullability: NOT NULL
- Default: none
- PK/FK/Constraints: FK -> reminder_policies.id
- Why: Links the schedule rule to its parent Reminder Policy.

`offset_days`
- Type: INTEGER
- Nullability: NOT NULL
- Default: none
- PK/FK/Constraints: UNIQUE with reminder_policy_id
- Why: Number of days relative to due date (negative = before, 0 = on due date, positive = overdue).

`template_key`
- Type: VARCHAR(100)
- Nullability: NULL
- Default: none
- Why: Specific template to use for this reminder step, overriding the policy default.

`status`
- Type: VARCHAR(20)
- Nullability: NOT NULL
- Default: none
- PK/FK/Constraints: CHECK (status IN ('ACTIVE', 'INACTIVE'))
- Why: Active/inactive lifecycle state of this specific schedule step.

`created_at`
- Type: TIMESTAMPTZ
- Nullability: NOT NULL
- Default: none
- Why: Record creation timestamp.

`updated_at`
- Type: TIMESTAMPTZ
- Nullability: NOT NULL
- Default: none
- Why: Record last-update timestamp.

**Constraints:**
- `UNIQUE (reminder_policy_id, offset_days)`
- `CHECK (status IN ('ACTIVE', 'INACTIVE'))`

No `status` default unless explicitly approved.

**offset_days semantics:**
- `-3` = 3 days before due date
- `0` = due date
- `3` = 3 days overdue
- `7` = 7 days overdue
Negative, zero and positive values are valid.

**Reminder Runtime Rule:**
Before every reminder send, runtime must recheck relevant stop conditions (e.g., outstanding balance is zero, document cancelled/voided, reminder hold, manual stop).
These are runtime Reminder Engine rules. Do NOT add `stop_if_paid`, `stop_if_cancelled`, `stop_if_hold` to Company-policy columns merely to make them configurable.
Actual planned/sent/skipped reminder occurrence history belongs to downstream runtime tables.

---

## 45. `company_approval_settings` — REVIEW

**What data would be stored**
- Only approval behavior that genuinely varies by Company and/or AR document type.

**Possible columns**
- `id` UUID PK
- `company_id` UUID FK
- `document_type`
- `approver_role`
- `allow_approver_edit`
- `allow_self_approval`
- `status`

**Relationships**
- Company 1:N document-specific approval settings

**Why we may keep it**
1. Different Companies/document types may require different approver roles.
2. `allow_approver_edit` may be a real Company/product configuration rather than a fixed rule.
3. It preserves a clean extension point for future workflow stages without building a workflow engine now.
4. It avoids storing approval config directly on `companies`.
5. It can support PI/TI/CN/DN differences if management requires them.
6. If every Company uses the same fixed approval behavior, this table adds no value and should be skipped; fixed rules remain in code.

**Fixed product rules should not become columns merely to look configurable.**

---

# 8. Company-Level User Access — Separate Decision

## 46. `company_user_memberships` — KEEP

**Reason:**
Tenant membership alone does NOT automatically authorize a user for every legal Company inside the Tenant. This table is primarily an authorization/data-isolation boundary.

Keycloak/IAM answers WHO is the user and WHAT broad permissions/roles does the user have.
ERP Company Membership answers WHICH Company may the user access.

**Columns:**

`id`
- Type: UUID
- Nullability: NOT NULL
- Default: none
- PK/FK/Constraints: PRIMARY KEY
- Why: Unique identifier for the membership row.

`company_id`
- Type: UUID
- Nullability: NOT NULL
- Default: none
- PK/FK/Constraints: FK -> companies.id
- Why: The specific legal Company being authorized for access.

`user_subject_id`
- Type: VARCHAR(255)
- Nullability: NOT NULL
- Default: none
- PK/FK/Constraints: UNIQUE with company_id
- Why: The external IAM subject identifier (e.g., Keycloak user ID) for the authorized user.

`status`
- Type: VARCHAR(20)
- Nullability: NOT NULL
- Default: none
- PK/FK/Constraints: CHECK (status IN ('ACTIVE', 'INACTIVE'))
- Why: Active/inactive lifecycle state of the user's access to this Company.

`created_at`
- Type: TIMESTAMPTZ
- Nullability: NOT NULL
- Default: none
- Why: Record creation timestamp.

`updated_at`
- Type: TIMESTAMPTZ
- Nullability: NOT NULL
- Default: none
- Why: Record last-update timestamp.

**Constraints:**
- `UNIQUE (company_id, user_subject_id)`
- `CHECK (status IN ('ACTIVE', 'INACTIVE'))`

Do NOT add `tenant_id`. Tenant ownership derives through `company_user_memberships.company_id` → `companies.id` → `companies.tenant_id`.

**Index:**
```sql
CREATE INDEX idx_company_user_memberships_active_user
ON company_user_memberships (user_subject_id, company_id)
WHERE status = 'ACTIVE';
```
Fast lookup for: "Which active Companies may this authenticated IAM subject access?"

**Company Authorization Rule:**
A Company-scoped operation requires:
1. authenticated IAM subject
2. target Company belongs to the current Tenant context
3. ACTIVE `company_user_memberships` row exists for `company_id` + `user_subject_id`
4. user also has the required IAM/RBAC permission for that action

Important distinction:
`company_user_memberships` = access scope
IAM/RBAC = action permissions

Do NOT add role arrays, permissions JSON, or workflow roles to this table.

---

# 9. Accounting Setup / Chart of Accounts Tables

The following eight tables are the approved current CoA and AR-accounting configuration foundation. They separate stable GL Account identity from effective-dated hierarchy placement and mapping policy. They do not define a predefined Chart of Accounts, accounting classifications, journal posting, reconciliation, period closing, inter-unit clearing, or accounting correction engine.

## 47. `account_hierarchies` — KEEP

**Owner:** Core / Accounting Configuration

**Used in flow:** Company Configuration → Accounting Setup → Hierarchies

### What data is stored

A Company-created hierarchy/view in which Account Groups and GL Accounts are arranged. Initial use is an `ACCOUNTING` hierarchy; a future `MANAGEMENT` hierarchy may arrange the same GL Accounts differently.

### Important columns

```text
id UUID PK
company_id UUID NOT NULL FK -> companies
hierarchy_name VARCHAR(150) NOT NULL
purpose_code VARCHAR(30) NOT NULL       -- ACCOUNTING initially; MANAGEMENT future
is_primary BOOLEAN NOT NULL DEFAULT false
status VARCHAR(20) NOT NULL
created_at TIMESTAMPTZ NOT NULL
updated_at TIMESTAMPTZ NOT NULL
```

### Relationships and constraints

- Company 1:N Account Hierarchies.
- Account Hierarchy 1:N Account Groups, Group Relationships, and GL Account Group Mappings.
- `purpose_code` is currently restricted to `ACCOUNTING`; `MANAGEMENT` remains future scope.
- `status` is exactly `ACTIVE` or `INACTIVE` and has no default.
- Only one active primary `ACCOUNTING` hierarchy is allowed per Company, enforced by a partial unique index on `company_id` where `purpose_code = 'ACCOUNTING' AND status = 'ACTIVE' AND is_primary = true`.
- An inactive historical primary retains its `is_primary` value and does not block a replacement.
- `hierarchy_name` must be non-blank and is case-sensitively unique on `(company_id, purpose_code, hierarchy_name)`; inactive hierarchies remain referenceable.
- `(company_id, id)` is unique so dependent tables can enforce same-Company hierarchy ownership with composite foreign keys.
- IDs use the established `gen_random_uuid()` database default. `created_at` and `updated_at` use the established `CURRENT_TIMESTAMP` insert default.
- Company ownership is mandatory and deletion is restricted once referenced.

### Why do we need this table?

1. A hierarchy is a view of accounts, not the GL Account identity itself.
2. A Company can reorganize reporting without replacing its accounts.
3. Accounting and future Management views can reuse the same GL Accounts.
4. Primary/current selection belongs to the hierarchy rather than a hardcoded product tree.
5. Inactive historical views remain explainable.
6. No predefined Revenue, Liability, or Sale-of-Services group is imposed.

### What happens if removed or merged?

Hierarchy purpose and lifecycle would be embedded in groups or GL Accounts, preventing the same stable account from participating in more than one view.

### Current decision

KEEP. Companies create/import their own hierarchy. `ACCOUNTING` is the initial purpose; detailed `MANAGEMENT` hierarchy behavior is DEFERRED.

### Flow

Create Company hierarchy → mark primary Accounting hierarchy → create Company groups → place groups/accounts with effective dates.

## 48. `account_groups` — KEEP

**Owner:** Core / Accounting Configuration

**Used in flow:** Company Configuration → Accounting Setup → Account Groups

### What data is stored

Company-created folders/reporting nodes inside one hierarchy. A Group is never a posting GL Account and stores no balance.

### Important columns

```text
id UUID PK
company_id UUID NOT NULL FK -> companies
hierarchy_id UUID NOT NULL FK -> account_hierarchies
group_name VARCHAR(200) NOT NULL
group_code VARCHAR(50) NULL
status VARCHAR(20) NOT NULL
created_at TIMESTAMPTZ NOT NULL
updated_at TIMESTAMPTZ NOT NULL
```

### Relationships and constraints

- Company 1:N Account Groups; Account Hierarchy 1:N Account Groups.
- `company_id` must match the referenced hierarchy's Company, enforced by the composite FK `(company_id, hierarchy_id) -> account_hierarchies(company_id, id)` without a redundant independent `hierarchy_id` FK.
- `status` is exactly `ACTIVE` or `INACTIVE` and has no default.
- `group_name` must be non-blank and is case-sensitively unique on `(company_id, hierarchy_id, group_name)`.
- `group_code` is optional, must be non-blank when supplied, and is case-sensitively unique on `(company_id, hierarchy_id, group_code)` when non-null; multiple null codes are allowed.
- IDs use the established `gen_random_uuid()` database default. `created_at` and `updated_at` use the established `CURRENT_TIMESTAMP` insert default.
- No `parent_group_id`, balance, posting flag, or GL Account columns are stored here.
- Used groups are made inactive; referenced groups use `ON DELETE RESTRICT`.
- A Group cannot be changed to `INACTIVE` while it has a current-effective or
  future-effective GL placement, or while it is the parent in a
  current-effective or future-effective child-Group relationship. Historical
  rows ending before the applicable inactivation point do not block the change.
  The lifecycle operation must never restructure or rewrite relationships
  automatically.

### Why do we need this table?

1. Folder/reporting nodes have identity and lifecycle separate from posting accounts.
2. Companies choose their own group names and codes.
3. A group can move over time without mutation of the Group itself.
4. Groups support multi-level trees through effective relationships.
5. Accounting and Management hierarchies can use different groups.
6. It prevents a used GL Account from being converted into a folder.

### What happens if removed or merged?

Groups would have to masquerade as GL Accounts, or hierarchy labels would be repeated as unvalidated text. Both choices blur posting identity and reporting structure.

### Current decision

KEEP as non-posting Company-created nodes. No predefined groups are seeded by the product.

### Flow

Select hierarchy → create groups → arrange them through effective-dated group relationships.

## 49. `account_group_relationships` — KEEP

**Owner:** Core / Accounting Configuration

**Used in flow:** Accounting hierarchy maintenance / historical reporting

### Approved business contract

This structure records effective-dated parent-child placement of an Account Group
within the Company's `ACCOUNTING` hierarchy.

- One Group has zero or one effective parent on a date; multiple effective parents
  are prohibited.
- A root Group is represented by the absence of an effective relationship row. A
  child-to-null relationship row is not part of the approved business model.
- Absence of an effective parent can also mean draft/incomplete setup. A later
  validation contract must distinguish intentional roots from incomplete
  hierarchy configuration.
- Parent and child belong to the same Company and hierarchy. Self-parentage and
  effective cycles such as A → B → C → A are prohibited.
- Reparenting preserves history by ending the old placement and creating the new
  placement. A normal move cannot accidentally introduce a business-date gap;
  moving to root is a separate explicit operation.
- Sibling presentation is alphabetical by Group name for MVP. No custom-order
  column is approved. Conceptual depth is unrestricted; no maximum is approved.
- Discontinuing a Group with children requires an effective-dated move of those
  children to its current parent, another Group, a new Group, or root. History is
  not overwritten.
- Changing a Group to `INACTIVE` is blocked while it remains the parent in a
  current-effective or future-effective child-Group relationship. The user must
  explicitly relocate or date-end those relationships first. Ended historical
  relationships remain stored and do not block inactivation.
- Historical relationship references are restrictive rather than cascading.

### Candidate physical database design — not frozen

A future physical table is expected to need a relationship identity, explicit
Company and hierarchy scope, a child Group, a parent Group present on every stored
relationship row, an effective interval, and audit metadata. Exact column names,
PostgreSQL datatypes, nullability/defaults, key shapes, interval bounds, indexes,
overlap enforcement, cycle enforcement, and division between database and service
validation remain unresolved. `daterange`/GiST and composite same-scope foreign
keys remain candidates, not an approved migration contract.

### Why do we need this table?

1. Group reorganizations may start at a Financial Year boundary or any approved date.
2. Historical reports must reproduce the hierarchy effective at that date.
3. Parent placement is temporal and does not belong permanently on `account_groups`.
4. Root periods are inferred from the absence of an effective parent relationship,
   without fake parent groups or artificial null-parent rows.
5. Non-overlap provides one deterministic parent per hierarchy/date.
6. Cycle prevention protects traversal and reporting.

### What happens if removed or merged?

A direct parent column would overwrite history whenever the Company reorganizes. Duplicate versioned group rows would change group identity merely to represent placement.

### Current decision

KEEP as the sole parent-placement structure for Account Groups.

### Flow

Choose child group → choose parent or explicit Move to Root and effective date →
validate Company/hierarchy/cycle/overlap and gap behavior → preserve superseded
relationship.

## 50. `gl_accounts` — KEEP

**Owner:** Core / Accounting Configuration

**Used in flow:** Company Configuration → Accounting Setup → GL Accounts

### What data is stored

Only stable Company posting-account identities consumed by AR mappings and future Accounting. Hierarchy, group membership, classifications, and calculated balances are excluded.

### Important columns

```text
id UUID PK
company_id UUID NOT NULL FK -> companies
account_code VARCHAR(50) NULL
account_name VARCHAR(200) NOT NULL
valid_from DATE NOT NULL
valid_to DATE NULL
status VARCHAR(20) NOT NULL
created_at TIMESTAMPTZ NOT NULL
updated_at TIMESTAMPTZ NOT NULL
```

### Relationships and constraints

- Company 1:N GL Accounts.
- GL Account 1:N hierarchy placements, Revenue GL Mappings, Tax GL Account Mappings, Bank Accounts, and finalized transaction references.
- `account_code`, when supplied, is unique within Company; database FKs always use `id`, never name/code.
- `valid_to IS NULL OR valid_to >= valid_from`.
- Used accounts are never hard-deleted; inactive/date-ended accounts cannot be selected for new mappings/postings.
- Rename or account-code changes preserve the stable UUID.
- No `parent_account_id`, `account_group_id`, `is_group`, `account_type_id`, or stored balance.

### Why do we need this table?

1. An actual posting account needs a stable identity independent of its label and placement.
2. Company-defined names/codes must never become product constants.
3. Mapping and finalized documents need durable FK references.
4. Validity/status prevents future use without erasing history.
5. Reorganization does not require replacing the account.
6. Company ownership maintains SaaS and multi-company isolation.

### What happens if removed or merged?

Mappings would depend on names/text or groups would become posting accounts. Either approach destroys stable accounting identity and reliable history.

### Current decision

KEEP the stable identity only. Accounting classifications such as ASSET, LIABILITY, EQUITY, INCOME, and EXPENSE—and the former `account_types` table—are DEFERRED to the full Accounting design.

### Split and merge rule

- **Split:** keep the old GL for history, create new GL Accounts, stop future use of the old account when appropriate, and change mappings from the approved date. Never convert the old GL into a Group.
- **Merge:** create/use a target GL for future mappings; retain and optionally inactivate the old GL Accounts. Historical transactions continue referencing their original IDs.

### Flow

Create/import stable GL Account → place it in a hierarchy through a dated mapping → configure AR mappings/settings → preserve resolved ID on finalized transactions.

## 51. `gl_account_group_mappings` — KEEP

**Owner:** Core / Accounting Configuration

**Used in flow:** GL placement / historical accounting and management reporting

### Approved business contract

This structure records effective-dated placement of one stable GL Account either
inside an Account Group or intentionally at the hierarchy root, without changing
the posting identity.

- The three approved states are: no effective row means unplaced; an effective row
  with `account_group_id` means placed in that Group; and an effective row with
  `account_group_id = NULL` means intentionally placed at hierarchy root. A null
  Group in an existing row never means unplaced.
- In the current `ACCOUNTING` hierarchy, one GL Account has at most one effective
  placement on a date, regardless of whether the placement is in a Group or at
  root. Absence of a row is allowed for draft/incomplete configuration and
  restructuring.
- GL Account and hierarchy must belong to the placement Company. When a Group is
  present, it must belong to the same Company and referenced hierarchy.
- Placement is a separate relationship. `gl_accounts` does not store a permanent
  Group or parent FK.
- A placement change retains the old effective relationship and creates the new
  one. Moving a GL or its containing Group never rewrites the GL Account recorded
  on a finalized transaction.
- Account Groups remain structural/non-posting. A posting GL Account is never
  converted to a Group when the Company introduces more detailed child GLs.
- A Group cannot be made `INACTIVE` while referenced by current-effective or
  future-effective GL placements. The user must explicitly relocate or date-end
  them first. Ended historical placements do not block inactivation, and no
  lifecycle action automatically creates, closes, moves, or rewrites placements.
- Historical references are restrictive rather than cascading.

### Final physical contract for future Migration 0018

```text
id UUID NOT NULL DEFAULT gen_random_uuid()
company_id UUID NOT NULL
hierarchy_id UUID NOT NULL
gl_account_id UUID NOT NULL
account_group_id UUID NULL
valid_from DATE NOT NULL
valid_to DATE NULL
created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
```

- `id` is the primary key, named `pk_gl_account_group_mappings`.
- `account_group_id` is deliberately nullable. In an existing row, null means an
  intentional root placement. Unplaced is represented only by absence of an
  effective row.
- The restrictive foreign keys are:
  - `fk_gl_account_group_mappings_company_id_companies`:
    `(company_id) -> core.companies(id)`;
  - `fk_gl_account_group_mappings_company_hierarchy`:
    `(company_id, hierarchy_id) -> core.account_hierarchies(company_id, id)`;
  - `fk_gl_account_group_mappings_company_gl_account`:
    `(company_id, gl_account_id) -> core.gl_accounts(company_id, id)`; and
  - `fk_gl_account_group_mappings_company_hierarchy_group`:
    `(company_id, hierarchy_id, account_group_id) ->`
    `core.account_groups(company_id, hierarchy_id, id)`.
- Every FK uses `ON DELETE NO ACTION`. Under PostgreSQL's default composite-FK
  `MATCH SIMPLE` behavior, a null `account_group_id` does not require a Group
  target. The separate Company and hierarchy FKs and the GL composite FK still
  require a valid Company, hierarchy, and same-Company GL for a root row.
- Existing `uq_gl_accounts_company_id_id`,
  `uq_account_hierarchies_company_id_id`, and
  `uq_account_groups_company_hierarchy_id` provide every required composite-FK
  target. Migration 0018 must add no supporting uniqueness to those tables.
- `ck_gl_account_group_mappings_valid_range` enforces
  `valid_to IS NULL OR valid_to >= valid_from`. Dates are inclusive, null
  `valid_to` is open-ended, and one-day periods are valid.
- `ex_gl_account_group_mappings_gl_hierarchy_period_overlap` uses `btree_gist`
  and excludes overlap on `(gl_account_id WITH =, hierarchy_id WITH =,
  daterange(valid_from, valid_to, '[]') WITH &&)`. It deliberately excludes
  `account_group_id`, so root/Group and root/root overlaps are rejected. It
  includes `hierarchy_id` so a future separately approved hierarchy purpose can
  place the same stable GL independently. `company_id` is unnecessary because
  `gl_account_id` is globally unique and Company scope is enforced by the
  composite FK. Migration 0018 must use the existing `btree_gist` extension and
  must neither create nor drop it.
- The only additional index is
  `ix_gl_account_group_mappings_company_hierarchy_group_dates` on
  `(company_id, hierarchy_id, account_group_id, valid_from, valid_to)`. PostgreSQL
  B-tree indexes retain null keys, so it supports Group-child lookup and root-level
  lookup (`account_group_id IS NULL`) as well as hierarchy loading. The exclusion
  index already supports GL/hierarchy/date lookup and overlap enforcement; no
  duplicate GL-history index is approved.
- Database constraints own identity, Company/hierarchy scope, valid ranges,
  non-overlap, and restrictive deletion. Creation/movement services must also
  validate active/date-applicable masters and provide useful errors.
- The future Migration 0018 downgrade drops only
  `core.gl_account_group_mappings` and its table-owned constraints/indexes. It
  preserves every Migration 0017 object and row, does not drop `btree_gist`, and
  does not alter `gl_accounts`, `account_groups`, or their supporting uniqueness.

Group inactivation is a transactional service/business-lifecycle rule rather
than a row-local database constraint. The service must reject inactivation if,
at the applicable business date, any GL placement referencing the Group or any
child-Group relationship for which it is the parent is current-effective or
future-effective. Rows whose `valid_to` precedes that date are historical and do
not block. Placement/relationship creation must likewise validate that its Group
is eligible. Both operations must coordinate through the Group row/transaction
so the check cannot race with a concurrent new relationship. No database trigger
or automatic restructuring is approved.

Approved transitions preserve all already-effective history:

- Group -> Group: end the old row and create the new Group row.
- Root -> Group: end the null-Group row and create the Group row.
- Group -> Root: end the Group row and create a null-Group row.
- Placed -> unplaced: end the existing row and create no replacement.
- Unplaced -> root: create a row with `account_group_id = NULL`.
- Unplaced -> Group: create a row with the selected Group UUID.

Adjacent periods use consecutive inclusive dates; for example, an old row ending
2027-03-31 and a replacement starting 2027-04-01 do not overlap. The multi-row
move must be atomic in the future service, but gaps remain representable during
draft/restructuring because no row means unplaced.

### Why do we need this table?

1. GL placement can change without changing GL identity.
2. Reorganization may apply from a Financial Year boundary or another effective date.
3. Historical hierarchy remains reproducible.
4. The relationship preserves an extension point for a separately approved future
   Management hierarchy without duplicating a GL identity.
5. Non-overlap gives deterministic placement at a date.
6. It prevents permanent `account_group_id` storage on `gl_accounts`.

### What happens if removed or merged?

A direct Group FK on the GL would overwrite history and prevent multiple hierarchy views. Copying GL Accounts per hierarchy would duplicate accounting identities.

### Current decision

KEEP as the only GL hierarchy-placement mechanism, including intentional root
placement.

### Flow

Select hierarchy/date → select stable GL → select Group or intentional root →
validate same Company/hierarchy and non-overlap → retain old placement.

## 52. `revenue_gl_mappings` — KEEP

**Owner:** AR Accounting Configuration

**Used in flow:** Accounting Setup → Revenue GL Mapping → Billing finalization

### What data is stored

One effective-dated Company rule mapping a resolved Supply Type and optional Company HSN/SAC to a stable GL Account.

### Important columns

```text
id UUID PK
company_id UUID NOT NULL FK -> companies
supply_type_code VARCHAR(30) NOT NULL
company_hsn_sac_code_id UUID NULL FK -> company_hsn_sac_codes
gl_account_id UUID NOT NULL FK -> gl_accounts
valid_from DATE NOT NULL
valid_to DATE NULL
status VARCHAR(20) NOT NULL
created_at TIMESTAMPTZ NOT NULL
updated_at TIMESTAMPTZ NOT NULL
```

### Relationships and constraints

- Company 1:N Revenue GL Mappings; GL Account 1:N mappings.
- Optional HSN/SAC and GL Account must belong to the same Company as the mapping.
- GL Account must be active and date-valid for the invoice date.
- `valid_to IS NULL OR valid_to >= valid_from`.
- Effective ranges for the same `(company_id, supply_type_code, company_hsn_sac_code_id)` condition must not overlap. PostgreSQL range exclusion is the preferred enforcement direction, including a normalized representation for the nullable HSN/SAC condition.
- Supply Type + matching HSN/SAC wins over Supply-Type-only; if neither matches, finalization blocks. Same-specificity ambiguity is rejected.

### Why do we need this table?

1. Billing needs deterministic automatic revenue-account resolution.
2. Supply Type is already resolved and can be used directly.
3. Optional HSN/SAC supports specific exceptions such as scrap.
4. Effective dating changes future resolution without rewriting history.
5. One row per condition is simpler than a header plus two child-condition tables.
6. Account names remain Company-defined and never hardcoded.

### What happens if removed or merged?

Invoice users would select ledgers manually or logic would depend on account names. Putting transaction conditions on `gl_accounts` would contaminate stable account identity.

### Current decision

KEEP. This single table replaces `revenue_account_mappings`, `revenue_mapping_supply_types`, and `revenue_mapping_hsn_sac`.

### Flow

Invoice date + Supply Type + line HSN/SAC → find effective specific mapping → else effective general mapping → block on none/ambiguity → snapshot `revenue_gl_account_id`.

## 53. `tax_gl_account_mappings` — KEEP

**Owner:** AR Accounting Configuration

**Used in flow:** Accounting Setup → Tax/Statutory GL Mapping → Billing or Receipt

### What data is stored

An effective-dated Company mapping from a controlled Tax Statutory Code—GST COMPONENT or TDS/TCS SECTION—to a stable GL Account.

### Important columns

```text
id UUID PK
company_id UUID NOT NULL FK -> companies
tax_statutory_code_id UUID NOT NULL FK -> tax_statutory_codes
gl_account_id UUID NOT NULL FK -> gl_accounts
valid_from DATE NOT NULL
valid_to DATE NULL
status VARCHAR(20) NOT NULL
created_at TIMESTAMPTZ NOT NULL
updated_at TIMESTAMPTZ NOT NULL
```

### Relationships and constraints

- Company 1:N Tax GL Account Mappings.
- Tax Statutory Code 1:N Company mappings; GL Account 1:N mappings.
- Statutory code must be applicable to the Company/country context; GL Account must belong to the same Company and be active/date-valid.
- `valid_to IS NULL OR valid_to >= valid_from`.
- Effective ranges for `(company_id, tax_statutory_code_id)` must not overlap; PostgreSQL range exclusion is the preferred implementation direction.
- Historical mappings and referenced accounts use `ON DELETE RESTRICT`.

### Why do we need this table?

1. Companies choose their own tax, TDS, and TCS ledger names.
2. GST component identity is controlled by FK rather than `tax_component_code` text.
3. Approved TDS/TCS SECTION codes can map without another mapping table; unreviewed statutory section numbers are not asserted here as current legal truth.
4. Effective dating changes future resolution without reclassifying old transactions.
5. Automatic resolution removes routine ledger choice from invoice/receipt users.
6. It preserves separation between tax calculation and accounting configuration.

### What happens if removed or merged?

Billing/Receipt would hardcode account names or accept manual/uncontrolled ledger selection. Merging it into statutory codes would make shared statutory identity Company-specific.

### Current decision

KEEP. Replace `tax_component_code` with `tax_statutory_code_id`; do not require an Account Type taxonomy in the current AR foundation.

### Flow

Calculated GST component or selected TDS/TCS section → resolve effective Company mapping → snapshot resolved GL Account ID where the transaction uses it.

## 54. `company_accounting_settings` — KEEP

**Owner:** Core / AR Accounting Configuration

**Used in flow:** Accounting Setup → Receivable Account → eligible Customer-Sale finalization

### What data is stored

The Company's current default receivable GL Account for the current one-default AR scope.

### Important columns

```text
company_id UUID PK/FK -> companies
default_receivable_gl_account_id UUID NOT NULL FK -> gl_accounts
updated_at TIMESTAMPTZ NOT NULL
updated_by UUID NULL
```

### Relationships and constraints

- Company 1:1 Accounting Settings.
- Default Receivable GL must belong to the same Company and be active/date-valid when resolved.
- Referenced GL uses `ON DELETE RESTRICT`; setting changes are audited.

### Why do we need this table?

1. Eligible Customer-Sale receivables need a deterministic Company GL Account.
2. Current scope requires one default rather than a condition/rule table.
3. It avoids another `accounts_receivable_mappings` table.
4. The stable GL FK avoids name-based selection.
5. A later settings change affects future transactions only.
6. Domestic/export/customer-category receivable routing can be designed later if required.

### What happens if removed or merged?

Receivable account choice would be hardcoded, manually selected, or hidden in a generic settings object. A separate mapping table would over-model the current single-default rule.

### Current decision

KEEP one default Receivable GL per Company. Expanded receivable routing is DEFERRED.

### Flow

Set Company default Receivable GL → eligible Customer-Sale document finalizes → snapshot resolved receivable GL Account ID.

## Future Account Determination — approved business direction, physical design deferred

The product direction includes future effective-dated Account Determination using
a controlled criterion vocabulary:

- Goods: Product Category, SKU, and optional HSN.
- Services: Service Category, Service Type, and optional SAC.
- Transaction context: Supply Type, Company Location, and GST/GST-location
  context.
- Fallback: an applicable Company Default GL.

A rule may combine one or more applicable criteria. Greater specificity wins,
then explicit priority resolves otherwise equally specific eligible rules; any
remaining ambiguity blocks resolution. Cost Centre is excluded. The design must
not use an uncontrolled `dimension_name` / `dimension_value` bag, and Industry,
Channel, Salesperson, Project, and Cost Centre are not approved criteria. Future
criteria require deliberate product approval. SKU and service records do not gain
a permanent `gl_account_id` for this resolver.

This is an approved business direction only. No Account Determination table,
column contract, datatype, key, index, priority representation, specificity
representation, conflict constraint, API, or resolver is approved here. The
meaning and scope of each Company-default fallback also remain to be frozen.

This direction does not supersede current `revenue_gl_mappings`,
`tax_gl_account_mappings`, `company_accounting_settings`, or direct Bank Account
GL references. In particular, current Revenue GL resolution remains Supply Type
plus optional HSN/SAC with specific-before-general precedence and no newly
invented priority field. Any replacement, coexistence, or migration plan requires
a later approved contract.

Future rules change prospective account selection only. Finalized transactions
retain their source GL Account IDs. Any current-year historical reporting
restatement is distinct from an explicit accounting reclassification; both
mechanisms, including journals, permissions, audit, and period behavior, remain
OPEN/DEFERRED. A possible future transaction-level account override is likewise
an OPEN AR transaction concern; if approved, it requires authorization, reason,
and audit evidence and does not modify Company master configuration.

## Accounting database safety rules

1. Use UUID primary keys and explicit Company ownership on every Company-scoped accounting table.
2. All historical master references use `ON DELETE RESTRICT`; deactivate/date-end used GL Accounts, Groups, Hierarchies, and mappings instead of deleting them.
3. Enforce `valid_to IS NULL OR valid_to >= valid_from` for every dated accounting row.
4. Reject cross-Company GL, Group, Hierarchy, HSN/SAC, Bank Account, and mapping relationships.
5. Reject cross-hierarchy Group relationships, parent cycles, and overlapping effective ranges.
6. Preserve stable GL IDs through name/code changes; never use `account_name` or `account_code` as a FK.
7. Do not store calculated balances in `gl_accounts` or `account_groups`.
8. Use PostgreSQL range types and GiST exclusion constraints where appropriate for non-overlap, together with backend validation for scope and cycle checks. Frontend validation alone is insufficient.

## Import/export readiness — DEFERRED implementation

The current design supports a future Company self-service import/export flow for Account Groups, GL Accounts, Group relationships, and GL hierarchy placements. Internal relationships use UUIDs. An external file may use `account_code` plus Company/template context for matching, subject to an approved conflict/idempotency specification. No import/export table, SQL/VPS procedure, or template engine is introduced now.

# 10. Shared File/Object Metadata

## 55. `stored_files` — KEEP

**Owner:** Core / Shared Object Storage Metadata

**Used in flow:** Company asset upload; future optional LUT evidence if a later requirement enables upload; later finalized document artifacts, explicit attachments and export artifacts

### What data is stored

One provider-neutral metadata identity for a Company-owned binary object. The actual bytes remain in object storage. This row contains no LUT, branding, invoice, attachment-link or export-job business semantics; each owning domain table later uses an explicit typed FK to `stored_files.id`.

### Columns and purpose

`id`
- Type: UUID; Nullability: NOT NULL; Default: none; Key: PRIMARY KEY.
- Why: stable database identity referenced by business and configuration records even if the storage provider changes.

`company_id`
- Type: UUID; Nullability: NOT NULL; Default: none; FK: `companies.id`.
- Why: identifies the Company that owns and authorizes use of the stored object.

`object_key`
- Type: VARCHAR(1024); Nullability: NOT NULL; Default: none; Constraint: UNIQUE.
- Why: immutable provider-neutral logical key used through `ObjectStorage` to locate the binary. It is not a public URL or temporary/signed URL.

`content_hash`
- Type: VARCHAR(128); Nullability: NOT NULL; Default: none.
- Why: integrity fingerprint of the exact stored bytes for detecting corruption, mismatch or replacement. Identical content may legitimately exist under separate file identities, so this column is not unique.

`content_type`
- Type: VARCHAR(255); Nullability: NOT NULL; Default: none.
- Why: MIME/content type, such as `application/pdf` or `image/png`, used for validation and safe handling.

`size_bytes`
- Type: BIGINT; Nullability: NOT NULL; Default: none; CHECK: `size_bytes >= 0`.
- Why: exact binary size used for validation and metadata without loading the file into PostgreSQL.

`original_filename`
- Type: VARCHAR(255); Nullability: NULL; Default: none.
- Why: optional source or user-facing filename; it is descriptive metadata and never object identity.

`created_at`
- Type: TIMESTAMPTZ; Nullability: NOT NULL; Default: none.
- Why: records when the stored-file metadata identity was created after successful object persistence.

### Keys, constraints and isolation

- PRIMARY KEY (`id`).
- FK (`company_id`) REFERENCES `companies.id`.
- UNIQUE (`object_key`).
- CHECK (`size_bytes >= 0`).
- `content_hash` is deliberately not unique; no deduplication engine is approved.
- Direct `tenant_id` is not stored. Current Company-child persistence derives Tenant ownership through `companies.tenant_id`; adding another Tenant column would duplicate scope and create a consistency invariant without a current requirement.
- Tenant-only stored objects without an owning Company are outside this frozen shape. If an approved future requirement needs them, scope must be reviewed explicitly rather than making `company_id` nullable by assumption.
- A consuming Company-owned domain row may reference only a `stored_files` row owned by the same Company. This same-Company rule requires backend/database enforcement and must not rely on temporary URL possession or frontend validation.

### Immutability and object-storage relationship

- After successful persistence, `object_key`, `content_hash`, `content_type` and `size_bytes` are immutable identity/integrity facts.
- Replacing bytes creates a new `stored_files` identity. A mutable domain configuration may move its current typed FK where allowed; a finalized financial document continues referencing its original artifact.
- Cloudflare R2 is the current binary store behind the provider-neutral `ObjectStorage` interface. Domain code reads `object_key` through that interface and does not call R2 APIs directly.
- Signed/public URLs are temporary access mechanisms and are never stored as permanent business identity.
- Server-side HTML/CSS `template_key` or template-version identity is separate from an output file. A rendered final PDF may have a `stored_files` row; template resources do not become uploaded file identities merely because they participate in rendering.

### Lifecycle and allowed consumers

- No `ACTIVE`/`INACTIVE` field is added. This is immutable object evidence/metadata rather than an editable master.
- Referenced financial artifacts must not be destructively removed by normal domain operations. Exact retention periods, orphan cleanup and exceptional deletion remain a separate policy decision; Cloudflare R2 versioning/retention provides infrastructure protection.
- Allowed consumers use explicit typed FKs when their schemas are reviewed: Company branding assets, future optional LUT evidence if a later requirement enables upload, later finalized document/revision artifacts, Company-scoped domain-specific attachments, POD evidence and export artifacts.
- No generic polymorphic attachment/link table is introduced.

### What must not be stored

- Raw binary/BYTEA content.
- Public, provider-specific or signed URLs as file identity.
- R2 bucket, Cloudflare account, provider ETag or other R2-specific API fields.
- Invoice-specific financial state, LUT/branding semantics, arbitrary `entity_type`/`entity_id` ownership, template identity or deduplication policy.

### Final financial PDF boundary

PostgreSQL financial transaction tables remain the structured financial truth; `stored_files` holds immutable metadata for a binary artifact; Cloudflare R2 holds the bytes. A later AR document-artifact review may connect a finalized document or revision to `stored_files.id`; that Billing relationship is not designed here.

# 11. Tables Removed / Moved Out of Company Configuration

## Removed / Merged / Replaced / Deferred
- `cost_centers` — generic master not required in the current explicit Business Segment, Cost Center Team, actual Team, and Location model.
- `cost_center_types` — no generic Cost Center master, so type master is also unnecessary.
- `cost_center_location_members` — direct `company_locations.cost_center_location_id` replaces it under current one-group-per-location rule.
- `cost_center_policies` — renamed/simplified to `company_cost_center_settings`.
- separate `business_segments` name — renamed to `cost_center_business_segments` to show its current reporting role.
- Team-to-Cost-Center-Team mapping table — not introduced; nullable `teams.cost_center_team_id` implements the current one-bucket-per-Team rule directly.
- `company_gst_registration_locations` — direct nullable `company_locations.gst_registration_id` under current 1:N rule.
- `company_base_currency` — base currency is a direct Company FK.
- separate `billing_currencies` and `payment_currencies` — merged into `company_ar_currencies` with purpose flags.
- `service_tax_assignments` / `sku_tax_assignments` and earlier `ar_service_tax_assignment` / `ar_sku_tax_assignment` names — current Company HSN/SAC, Base GST Nature, and conditional `selected_tax_rate_id` are stored directly on Service Type/SKU for MVP.
- `hsn_code_master` + `sac_code_master` and earlier `core_tax_classification` — replaced by Company-owned `company_hsn_sac_codes`; there is no global preloaded HSN/SAC catalogue.
- `tax_classifications` — renamed/replaced by `company_hsn_sac_codes` so HSN/SAC cannot be confused with a broad tax family.
- `tax_classification_rates` and earlier `core_classification_gst_rate` — renamed/replaced by `company_hsn_sac_tax_rates`.
- earlier `core_gst_rate` naming — represented by `tax_rates` linked to controlled `tax_types`; no parallel GST-only rate table.
- separate `tds_section` / `tcs_section` table families — generalized into `tax_statutory_codes` + `tax_statutory_code_rates`; transaction rules remain separate.
- `statutory_sections` / `statutory_section_rates` — renamed/generalized to `tax_statutory_codes` / `tax_statutory_code_rates` so GST COMPONENT and TDS/TCS SECTION identities share one controlled statutory layer without sharing calculation logic.
- free-text `tax_component_code` — replaced by `tax_gl_account_mappings.tax_statutory_code_id`.
- `account_types` — DEFERRED from the current AR CoA foundation; ASSET/LIABILITY/EQUITY/INCOME/EXPENSE and other accounting classifications await the full Accounting design.
- `gl_accounts.parent_account_id`, `gl_accounts.account_group_id`, `gl_accounts.is_group`, `gl_accounts.account_type_id`, and any stored balance — removed from the current GL identity design. Effective hierarchy placement uses relationship tables.
- `revenue_account_mappings`, `revenue_mapping_supply_types`, and `revenue_mapping_hsn_sac` — replaced by one effective-dated `revenue_gl_mappings` table.
- separate `accounts_receivable_mappings` — not created; current scope uses `company_accounting_settings.default_receivable_gl_account_id`.
- separate bank-to-GL mapping table — not created; `company_bank_accounts.gl_account_id` is the direct same-Company FK.
- `ar_billing_defaults` — defaults remain on owning masters.
- generic `company_settings` — rejected as a catch-all.

## Moved Out / Belongs to Downstream Flow
- recurring/periodic/milestone schedule configuration → Sales Order / contract / Billing Schedule.
- `billing_schedules`, `billing_requests`, `billing_actions` → Billing flow.
- customer/client tables → Customer Onboarding.
- invoice/PI/TI/CN/DN transaction tables → Billing.
- receipt/allocation/PI→TI allocation-transfer tables → Receipt/Knock-off.
- actual invoice-email logs / reminder state/occurrence → Invoice Delivery runtime, not Company Configuration.
- report-run tables → Reporting/analytics runtime, not Company Configuration master setup.

---

# 12. Current Open Decisions Before Database Freeze

1. **`supply_types`:** actual reference table or controlled enum? The vocabulary itself is confirmed.
2. **FX policy details:** Receipt / Reporting effective-date, rate-date, stale-rate, and conversion behavior while keeping approved `fx_policies`.
3. **Team membership scope:** exact physical IAM subject reference and database enforcement of one active actual-Team membership within the applicable Company scope.
4. **Company access:** every Tenant user sees every Company, or keep `company_user_memberships`?
5. **Approval settings:** does approval behavior actually vary by Company/document type enough to justify `company_approval_settings`?
6. **Numbering condition types:** which condition types are MVP vs later, while keeping the extensible condition model.
7. **Accounting posting:** exact journals, posting dates/status, idempotency, reversals, and reconciliation remain for the Accounting design.
8. **Inter-Unit accounting:** clearing and balancing GL treatment remains open while `INTER_UNIT` stays excluded from Customer AR.
9. **Accounting classifications:** whether/how ASSET, LIABILITY, EQUITY, INCOME, EXPENSE and other types are modeled is DEFERRED with `account_types` to the full Accounting module.
10. **Management hierarchy:** detailed creation, primary-selection, reporting, and authorization rules are DEFERRED; the schema only preserves the extension path.
11. **Accounting correction/reclassification:** changing historical accounting requires a future explicit correction/reclassification entry; no in-place rewrite is designed here.
12. **CoA import/export:** file format, validation report, idempotency, conflict resolution, and template semantics remain OPEN; manual SQL/VPS maintenance is not an acceptable product process.
13. **Expanded receivable routing:** Domestic/Export/customer-category receivable mappings are DEFERRED; current scope has one Company default.
14. **Stored-file lifecycle:** exact retention periods, orphan cleanup, exceptional deletion/legal-hold behavior, and canonical content-hash algorithm/encoding remain OPEN outside the shared metadata shape. Referenced financial artifacts cannot be destructively removed through normal domain operations.

---

# 13. Current Table Count Summary

### KEEP now / current design
- Core/Shared foundation and statutory: 29 KEEP tables through `supply_types`, including the three approved generic Company legal-identifier tables, `company_legal_name_versions`, `company_location_versions`, and `gst_registration_types`, and excluding the remaining REVIEW entries and `cost_center_locations`
- Catalogue/cost-center: 11 tables (`service_categories` through `company_cost_center_settings`, including `cost_center_locations` and separate actual `teams`)
- AR compliance/numbering/output: 6 tables (`company_luts` through `company_document_templates`)
- Delivery/reminders: 4 tables (`email_provider_configs` through `reminder_schedule_rules`)
- Company access: 1 table (`company_user_memberships`)
- Accounting setup: 8 tables (`account_hierarchies`, `account_groups`, `account_group_relationships`, `gl_accounts`, `gl_account_group_mappings`, `revenue_gl_mappings`, `tax_gl_account_mappings`, `company_accounting_settings`)
- Shared file/object metadata: 1 table (`stored_files`)

### REVIEW / conditional tables
- `company_gst_registration_versions`
- `supply_types`
- `company_approval_settings`

The Company Configuration review now contains **60 KEEP tables**, **3 REVIEW/conditional tables**, and **1 DEFERRED accounting-classification table (`account_types`)**. The point of this document is not to maximize table count. A table stays only when it represents a distinct business identity, repeated 1:N data, independent history, genuinely configurable Company behavior, or the approved shared metadata identity for externally stored binaries.

---

# 14. Downstream AR Database Design — Review Candidate

This section completes the transaction design outside Company Configuration. The Company Configuration and shared-file text in sections 1–13 remain the reviewed source of truth.

Every downstream table below is a **review candidate before schema implementation**. `ADD` means the table is proposed because a stated current business requirement needs it; it does not mean product approval has already been given. `REVIEW` and `DEFER` identify unresolved or later scope. No table exists merely to make a possible future capability easier.

The design uses the following current directions:

- Customer, Sales Order, AR Document, Receipt, and Reminder data stays Tenant-scoped and Company-scoped where the business transaction requires a seller Company.
- Customer ownership across a Tenant versus one Company and the hard-block uniqueness boundary for PAN/GSTIN remain **TBD / REVIEW**. The schema must not assert global uniqueness before that decision.
- Finalized AR documents hold structured transaction-time seller, customer, address, tax, currency, payment-term, bank, and line snapshots. They do not depend on current master values for historical rendering.
- PI, TI, CN, and DN use one document aggregate, but type-specific eligibility, balance, conversion, and correction rules remain explicit and unresolved rules remain **REVIEW**.
- Human approval records the submitted revision and each decision. This is not a generic workflow engine.
- Final numbers are consumed only in the successful approval/finalization transaction and are never reused.
- Valid LUT is required at finalization for the current without-payment routes `EXPWOP` and `SEZWOP`. `EXPWP` and `SEZWP` are not blocked solely for missing LUT.
- Normal users cannot edit or post in a locked/restricted historical period. Any policy-permitted Finance/Admin/Authority exception requires a reason and complete audit. A Company may later disable that exception. No accounting period-closing engine is added here, and Financial Year, Period Closing, and Period Lock remain distinct.
- Receipt cash stays separate from TDS and other non-cash settlement. Advanced TDS/TCS threshold and cumulative engines are outside this MVP design.
- Raw `storage_key`, `file_hash`, `pod_storage_key`, or `artifact_storage_key` fields shown in downstream ADD/REVIEW/DEFER candidates are legacy placeholders, not an approved parallel file-identity design. When each owning table is reviewed, it must use an explicit typed relationship to canonical `stored_files` metadata where a persisted object is required. This note does not freeze those consumer relationships or redesign their business tables.

# 15. Customer Onboarding Tables

## `customer_organisations`

**Status:** ADD

**Owner:** AR Customer

**Used in flow:** Customer Onboarding / Customer Search / Reporting

### What data is stored

An optional external-customer business grouping, such as a customer group with several legal customer entities. This is not the SaaS Tenant's internal `organisations` table, and a Customer can exist without a row here.

### Important columns

```text
id UUID PK
tenant_id UUID FK -> tenants
code nullable
name
status
created_at, updated_at
```

`tenant_id` prevents a customer grouping from crossing the SaaS isolation boundary. `code` is optional until a business-controlled group code is required.

### Relationships

- Tenant 1:N Customer Organisations.
- Customer Organisation 1:N Customers through nullable `customers.customer_organisation_id`.
- It has no FK to the seller-side `organisations` table.

### Why do we need this table?

1. One external business group may contain several separately billable legal customers.
2. Users may search and report those customers together without merging their PAN, GSTIN, or receivable identity.
3. The grouping has its own name, code, and active/inactive lifecycle.
4. A nullable customer FK preserves the confirmed rule that Organisation grouping is optional.
5. Keeping it separate prevents external-customer hierarchy from being confused with the Tenant's owned-Company hierarchy.
6. It avoids repeating a group name on every Customer and later trying to reconcile spelling changes.

### What happens if we remove this table?

The optional grouping could be omitted safely only if the product drops customer-group reporting and search. Storing a group name on `customers` would repeat mutable data and would not provide a stable group identity.

### Current decision

Propose the table for the optional external grouping. The exact business meaning of customer Organisation and the Customer Tenant/Company ownership boundary remain **REVIEW** before constraints are frozen.

### Flow

Customer Onboarding → optional Group selection → Customer approval → Customer reporting.

## `customers`

**Status:** ADD

**Owner:** AR Customer

**Used in flow:** Customer Onboarding / Sales Order / Billing / Receipt / Collections / Reporting

### What data is stored

The stable legal AR party identity called Customer or Client in the product. Locations, GST registrations, contacts, documents, and approval events remain child data rather than repeating columns on this row.

### Important columns

```text
id UUID PK
tenant_id UUID FK -> tenants
owning_company_id UUID nullable FK -> companies [scope decision pending]
customer_organisation_id UUID nullable FK -> customer_organisations
customer_code nullable until approval, then stable
legal_name
display_name nullable
legal_entity_type nullable
pan nullable
country_code
status
onboarding_status
current_revision_no
approved_at nullable
created_by, created_at, updated_by, updated_at
```

`owning_company_id` is intentionally unresolved: keep it only if Customer identity is confirmed as Company-specific. `customer_code` is assigned through the approved onboarding flow and remains stable after normal master edits.

### Relationships

- Tenant 1:N Customers.
- Customer Organisation 1:N Customers, optional.
- Customer 1:N Locations, GST Registrations, Contacts, Documents, approval submissions, Sales Orders, AR Documents, and Receipts.
- Company ownership is **TBD / REVIEW**; transaction tables still carry their explicit seller `company_id`.

### Why do we need this table?

1. Sales Orders, invoices, receipts, allocations, and collections need one stable customer key.
2. Client Code must remain stable even when the legal/display name or contacts change.
3. Onboarding status has a lifecycle independent of any one address or GST registration.
4. PAN and legal identity support duplicate detection and statutory validation.
5. Customer-level ageing and payment history require a common party identity across documents.
6. A separate row avoids copying legal-party data into every location, contact, and commercial transaction.

### What happens if we remove this table?

Legal identity would be duplicated across Sales Orders, invoices, receipts, and contacts. Updates could split one customer into inconsistent records, and there would be no stable Client Code or onboarding lifecycle.

### Current decision

Replace the legacy `clients` name with `customers` in this proposal for consistent product language. Confirm the Tenant-wide versus Company-specific ownership and PAN/GSTIN uniqueness scope before migration freeze.

### Flow

Search Existing Customer → Create/Edit Draft → Submit → Finance decision → Approved Client Code → Sales Order/Billing/Receipt.

## `customer_gst_registrations`

**Status:** ADD

**Owner:** AR Customer

**Used in flow:** Customer Onboarding / Sales Order / Billing / Tax Validation

### What data is stored

Each GST registration belonging to a Customer. A Customer may have many registrations or none, and a draft registration remains separate from the Customer's legal identity row.

### Important columns

```text
id UUID PK
tenant_id UUID FK -> tenants
customer_id UUID FK -> customers
gstin
registered_name
state_code
registration_type_code nullable
valid_from nullable
valid_to nullable
status
created_at, updated_at
```

`gstin` is normalized for duplicate checking. The exact database uniqueness boundary follows the pending Customer ownership decision rather than assuming global uniqueness.

### Relationships

- Customer 1:N GST Registrations.
- GST Registration 1:N Customer Locations through nullable `customer_locations.gst_registration_id` in the current proposal.
- GST Registration 1:N draft/final AR Documents as selected customer GST context; finalized documents also retain GSTIN snapshots.

### Why do we need this table?

1. One customer can transact through several state registrations.
2. GSTIN has statutory identity and validation rules distinct from a postal address.
3. A customer without GSTIN remains valid because the child collection can be empty.
4. Billing must select the applicable customer registration instead of reading one Customer-level GSTIN.
5. Registration status and validity can change without changing the Customer ID.
6. Duplicate GSTIN checks need normalized registration rows rather than searching free text in addresses.

### What happens if we remove this table?

Multiple GSTINs would require repeating numbered columns on `customers` or duplicating the Customer. Billing could not reliably select a registration, and statutory duplicate checks would become ambiguous.

### Current decision

Propose one registration table. Use a direct nullable FK from Customer Location while the relationship remains one registration to many locations and one current registration per location; add a mapping table only if a real many-to-many/history requirement is confirmed.

### Flow

Customer Draft → GST Registrations → Location association → Approval → Billing customer GST selection.

## `customer_locations`

**Status:** ADD

**Owner:** AR Customer

**Used in flow:** Customer Onboarding / Sales Order / Billing / Goods Dispatch

### What data is stored

Reusable customer addresses for registered, billing, shipping, branch, or office use. Contacts remain independent, and finalized AR documents copy the actual selected address into structured snapshot columns.

### Important columns

```text
id UUID PK
tenant_id UUID FK -> tenants
customer_id UUID FK -> customers
gst_registration_id UUID nullable FK -> customer_gst_registrations
location_code nullable
name
address_line_1
address_line_2 nullable
city
state_code
postal_code
country_code
is_registered_address
is_billing_address
is_shipping_address
is_branch
status
created_at, updated_at
```

Purpose flags cover the current fixed uses without a separate purpose table. `gst_registration_id` links a location to at most one current Customer GST registration under the proposed MVP relation.

### Relationships

- Customer 1:N Locations.
- Customer GST Registration 1:N Locations in the proposed direct-FK model.
- Location 1:N Sales Orders and AR Documents as selected bill-to/ship-to references while draft/current.
- No parent-child relationship to Customer Contacts.

### Why do we need this table?

1. One Customer may have several billing, shipping, registered, and branch addresses.
2. Sales Orders need stable selectable bill-to and ship-to IDs.
3. GST registration association helps validate the customer tax context selected for billing.
4. Address maintenance should not overwrite the Customer's stable legal identity.
5. Fixed purpose flags support current selection without a generic location-role engine.
6. Final invoice snapshots can identify the source Location while preserving the exact printed address.

### What happens if we remove this table?

Addresses would become repeating Customer columns or unvalidated free text on each Sales Order. Reuse and search would be lost, while putting only live addresses on invoices would also rewrite historical truth.

### Current decision

Propose a non-versioned current master for MVP. `customer_location_versions` stays deferred unless backdated customer-address resolution is separately required beyond document snapshots.

### Flow

Customer Draft → Locations → optional GST association → SO bill-to/ship-to selection → AR Document address snapshot.

## `customer_contacts`

**Status:** ADD

**Owner:** AR Customer

**Used in flow:** Customer Onboarding / Sales Order / Invoice Delivery / Collections

### What data is stored

People associated with a Customer, including their current communication details. A person is stored once even when they perform several roles, and location assignment is not mandatory.

### Important columns

```text
id UUID PK
tenant_id UUID FK -> tenants
customer_id UUID FK -> customers
name
email nullable
phone nullable
designation nullable
status
created_at, updated_at
```

Email and phone are contact data, not the authoritative invoice delivery history; each send request snapshots its resolved recipients.

### Relationships

- Customer 1:N Contacts.
- Contact 1:N Contact Roles.
- Contacts N:M Sales Orders through `sales_order_contacts`.
- Contacts are referenced during delivery/reminder recipient resolution but are not children of Customer Locations.

### Why do we need this table?

1. One Customer can have several billing, finance, operational, and escalation contacts.
2. The same person can serve multiple roles without duplicate Contact rows.
3. Sales Orders can select deal-specific contacts from the Customer master.
4. Invoice delivery and reminders need current recipient sources before creating immutable send snapshots.
5. A Contact can be deactivated without deleting prior delivery evidence.
6. Keeping Contacts separate prevents repeated name/email columns on Customer and Sales Order.

### What happens if we remove this table?

People would be duplicated by role or embedded in transactions. Email changes would be hard to maintain, and there would be no reusable recipient identity for SO, delivery, and collections.

### Current decision

Propose independent Customer Contacts. Do not require or infer a Location relationship in the MVP schema.

### Flow

Customer Draft → Contacts → role assignment → SO selection → Delivery/Reminder recipient resolution.

## `customer_contact_roles`

**Status:** ADD

**Owner:** AR Customer

**Used in flow:** Customer Onboarding / Sales Order / Invoice Delivery / Collections

### What data is stored

The roles performed by each Customer Contact. Current role codes include `PRIMARY`, `BILLING`, `FINANCE`, and `ESCALATION`; additional codes require product approval rather than free-text proliferation.

### Important columns

```text
id UUID PK
customer_contact_id UUID FK -> customer_contacts
role_code
status
created_at, updated_at
UNIQUE (customer_contact_id, role_code)
```

### Relationships

- Customer Contact 1:N Contact Roles.
- Customer has role-bearing contacts through its Contact children.
- Delivery/reminder logic reads roles but snapshots the resulting recipient addresses on runtime requests.

### Why do we need this table?

1. One person can be both Primary, Billing, Finance, and Escalation contact.
2. Roles can change without duplicating or replacing the person's identity.
3. Delivery can resolve Billing/Finance recipients from controlled role codes.
4. Collections can escalate to a different role without adding columns to `customer_contacts`.
5. The unique pair prevents the same role being assigned twice to one Contact.
6. It avoids multiple boolean role columns that must change whenever a new approved role appears.

### What happens if we remove this table?

Role information would need repeated Contact rows, multiple booleans, or free text. Duplicate people and inconsistent recipient resolution would follow; merging is safe only if the product permanently limits each Contact to one role, which contradicts the current requirement.

### Current decision

Replace the legacy `client_roles` concept with a role child of the stable Contact identity.

### Flow

Contact creation → assign one or more roles → select SO contacts → resolve delivery/collection recipients.

## `customer_documents`

**Status:** ADD

**Owner:** AR Customer

**Used in flow:** Customer Onboarding / Finance Review / Audit

### What data is stored

Metadata for Customer onboarding and statutory supporting files held in object/file storage. The database stores a storage reference and evidence metadata, not the file bytes.

### Important columns

```text
id UUID PK
tenant_id UUID FK -> tenants
customer_id UUID FK -> customers
document_type
reference_number nullable
document_date nullable
storage_key
file_name
file_hash nullable
status
uploaded_by, uploaded_at
```

`storage_key` locates the object; `file_hash` can prove that the reviewed file has not changed.

### Relationships

- Customer 1:N Documents.
- A submission may record the Customer revision that included the document set; no generic workflow-document mapping is introduced.

### Why do we need this table?

1. Finance may need PAN, GST, agreement, or other onboarding evidence.
2. One Customer can have several files and document types.
3. Upload actor/date and file hash support review and audit.
4. Status supports superseded or invalid documents without deleting evidence.
5. Object storage references avoid large PostgreSQL binary rows.
6. Keeping file metadata separate prevents repeating storage columns on `customers`.

### What happens if we remove this table?

Supporting documents would be unlinked, overwritten, or placed in repeating Customer columns. Approval could no longer show which files were available, unless the product explicitly removes onboarding documents.

### Current decision

Propose one Customer-owned document metadata table; do not store binary content in PostgreSQL.

### Flow

Customer Draft → upload evidence → Submit → Finance Review → retain approved/superseded evidence.

## `customer_approval_submissions`

**Status:** ADD

**Owner:** AR Customer

**Used in flow:** Customer Onboarding / Approval / Audit

### What data is stored

Each immutable Customer revision submitted for human review. It records who submitted, when, and which revision/hash was reviewed without creating a generic workflow engine or a giant snapshot JSON document.

### Important columns

```text
id UUID PK
tenant_id UUID FK -> tenants
customer_id UUID FK -> customers
revision_no
revision_hash
submitted_by
submitted_at
status
closed_at nullable
UNIQUE (customer_id, revision_no)
```

`revision_hash` covers the material Customer aggregate content. Edits after return increment `customers.current_revision_no` and require a new submission.

### Relationships

- Customer 1:N Approval Submissions.
- Approval Submission 1:N Approval Decisions.
- Shared `audit_events` records submission and material edit actions.

### Why do we need this table?

1. `customers.status` alone cannot say which revision Finance reviewed.
2. Returned and resubmitted drafts require separate immutable attempts.
3. It preserves submitter and submission time independently of the final Customer status.
4. The revision hash detects silent content changes after submission.
5. Future additional approval stages can add decisions without replacing the submission identity.
6. It separates approval evidence from mutable Customer master fields.

### What happens if we remove this table?

Only the current status would remain. The system would lose what revision was submitted, when it was submitted, and how resubmissions relate to decisions; audit events alone would not provide a stable decision target.

### Current decision

Propose submission records for the current single human approval stage. Exact self-approval/edit-in-review behavior remains **REVIEW**.

### Flow

Customer Draft revision → Submit → immutable submission → Finance decision → optional revised resubmission.

## `customer_approval_decisions`

**Status:** ADD

**Owner:** AR Customer

**Used in flow:** Customer Onboarding / Approval / Audit

### What data is stored

Human decisions against one Customer approval submission. Current decision codes are `APPROVED`, `RETURNED`, and `REJECTED`; edits create a new Customer revision rather than overwriting the submitted revision.

### Important columns

```text
id UUID PK
tenant_id UUID FK -> tenants
submission_id UUID FK -> customer_approval_submissions
decision
decision_by
decision_at
reason nullable except mandatory for RETURNED/REJECTED
```

### Relationships

- Approval Submission 1:N Decisions, allowing later staged review without a workflow builder.
- Decision actor references the existing IAM/user identity model.
- Approval actions also emit shared audit events.

### Why do we need this table?

1. It answers who approved, returned, or rejected a submitted revision.
2. It retains reasons/comments required for correction and review.
3. A Customer can pass through several submissions and decisions without erasing history.
4. Approval evidence remains distinct from field-change audit evidence.
5. It can support later multiple decisions while the MVP uses one authorized human stage.
6. It allows the approved Client Code event to be traced to a specific decision.

### What happens if we remove this table?

Decision actor, time, reason, and submission linkage would be lost or overloaded into the Customer row. Repeated review cycles could not be represented safely.

### Current decision

Propose a decision child table; do not add configurable workflow states, transitions, or route-builder tables.

### Flow

Submission → Finance/Authority decision → Approved Client Code or Return/Reject → audit.

## `customer_delivery_settings`

**Status:** REVIEW

**Owner:** AR Customer

**Used in flow:** Customer Onboarding / Invoice Delivery

### What data is stored

Optional Customer-level overrides between Company delivery defaults and one document's send intent. Possible values are automatic-send override, recipient-role selection, default CC, and template override; exact override semantics are not frozen.

### Important columns

```text
customer_id UUID PK/FK -> customers
automatic_send_override nullable
recipient_role_codes nullable
default_cc nullable
template_id nullable FK -> company_document_templates
status
updated_by, updated_at
```

Nullable fields mean “inherit Company configuration,” not false or empty.

### Relationships

- Customer 1:0..1 Delivery Settings.
- References existing Company document templates; it does not copy provider credentials or Company delivery configuration.
- Runtime `invoice_delivery_requests` snapshot the resolved sender, recipients, template, and artifact.

### Why do we need this table?

1. The documented precedence includes Customer-level delivery behavior.
2. Some Customers may require manual sending while the Company default is automatic.
3. Recipient roles or CC defaults may differ by Customer.
4. Nullable overrides preserve inheritance rather than duplicating Company values.
5. Runtime requests still retain the exact resolved send intent after settings change.
6. Separating optional settings keeps legal Customer identity free from delivery-only columns.

### What happens if we remove this table?

Removal is safe if the MVP supports only Company defaults plus per-document choices. If Customer-level overrides are required, moving them into `customers` would overload the legal master and still require clear nullable inheritance semantics.

### Current decision

Keep under review until the exact Company → Customer → Document delivery override rules are frozen. Do not implement solely because the legacy workbook listed `client_delivery_settings`.

### Flow

Company delivery defaults → optional Customer override → document send intent → delivery request/attempt.

## `customer_reminder_settings`

**Status:** REVIEW

**Owner:** AR Collections

**Used in flow:** Customer Onboarding / Collections / Reminder Planning

### What data is stored

Optional Customer-level reminder override data between Company reminder policy and Invoice-level controls. The exact replace-versus-merge behavior and schedule override semantics remain unresolved.

### Important columns

```text
customer_id UUID PK/FK -> customers
reminders_enabled_override nullable
reminder_policy_id nullable FK -> reminder_policies
recipient_role_codes nullable
hold_until nullable
hold_reason nullable
updated_by, updated_at
```

### Relationships

- Customer 1:0..1 Reminder Settings.
- Optionally references an existing Company-scoped Reminder Policy.
- `reminder_occurrences` records actual planned/sent/skipped runtime history.

### Why do we need this table?

1. Current direction gives Customer control precedence over Company reminder defaults.
2. A Customer may be placed on reminder hold without changing every open invoice.
3. Recipient roles may differ for collections communications.
4. Nullable values can inherit Company policy without copying its schedule rows.
5. Runtime occurrences remain stable when Customer settings later change.
6. A separate optional row avoids adding collections-only controls to every Customer.

### What happens if we remove this table?

Removal is safe only if Customer-level reminder overrides are postponed. Storing copied Company schedules per Customer would create stale duplicated policy and is not an acceptable replacement.

### Current decision

Review after reminder override semantics are specified. The current MVP must not duplicate Company policy rows into each Customer.

### Flow

Company reminder policy → optional Customer override → Invoice control → occurrence planning → runtime stop check.

# 16. Sales Order / Commercial Tables

## `sales_orders`

**Status:** ADD

**Owner:** AR Commercial

**Used in flow:** Sales Order / Approval / Billing / Reporting

### What data is stored

The commercial agreement or internal supply instruction from which billing is prepared. It classifies the transaction as a Customer Sale or Inter-Unit supply and retains the applicable source, destination, commercial, address, and reporting context without treating an internal destination as a Customer.

### Important columns

```text
id UUID PK
tenant_id UUID FK -> tenants
company_id UUID FK -> companies
transaction_classification               -- CUSTOMER_SALE / INTER_UNIT
customer_id UUID nullable FK -> customers
source_gst_registration_id UUID nullable FK -> company_gst_registrations
source_location_id UUID nullable FK -> company_locations
destination_gst_registration_id UUID nullable FK -> company_gst_registrations
destination_location_id UUID nullable FK -> company_locations
order_number
customer_reference nullable
customer_po_number nullable
order_date
effective_from nullable
effective_to nullable
supply_type_code
currency_code FK -> currencies
payment_term_id nullable FK -> payment_terms
bill_to_customer_location_id nullable FK -> customer_locations
ship_to_type nullable                      -- CUSTOMER_LOCATION / COMPANY_LOCATION
ship_to_customer_location_id nullable FK -> customer_locations
ship_to_company_location_id nullable FK -> company_locations
business_segment_id nullable FK -> cost_center_business_segments
team_id nullable FK -> teams
owner_user_id nullable
engagement_manager_user_id nullable
billing_method_code
status
current_revision_no
approved_at nullable
created_by, created_at, updated_by, updated_at
```

`billing_method_code` identifies one-time/advance/milestone/periodic/recurring commercial intent; it does not by itself create scheduler rules.

### Relationships

- Company 1:N Sales Orders; Customer 1:N Customer-Sale Sales Orders.
- Sales Order 1:N Service Lines, Goods Lines, Contacts, Documents, approval submissions, and optional Billing Schedule rows.
- Ship-To is a discriminated Customer Location or Company Location reference; exactly one matching FK is populated when Ship-To applies.
- Sales Order 1:N AR Documents where billing originates from the order.

### Why do we need this table?

1. Billing needs a stable commercial source distinct from Company catalogue defaults.
2. Customer-specific currency, price, payment term, and references belong to a Customer Sale; Inter-Unit supply instead retains same-Company source/destination GST and Location context.
3. One header groups several service and goods lines under one approval lifecycle.
4. Seller Company and supply context are chosen before invoice preparation.
5. Bill-to/ship-to and responsible Team/owner are selected once for the order, including Company Location Ship-To where required.
6. Approved order revisions provide traceable commercial authority for later documents.

### What happens if we remove this table?

Commercial terms would be copied directly into each invoice, with no approved deal identity or reusable source for recurring/periodic billing. Catalogue rows would be incorrectly overloaded with customer prices.

### Current decision

Propose one Sales Order header. `CUSTOMER_SALE` requires a Customer and excludes internal destination fields. `INTER_UNIT` requires source and destination GST Registration/Location within the same Company, uses no Customer, and does not create a normal AR outstanding. Detailed approval, billing-method, and later accounting/clearing behavior remain subject to their recorded decisions.

### Flow

Classification → Customer or internal destination → source seller context → Supply/Terms/Addresses → Lines/Contacts/Documents → Submit/Approve → Billing.

## `sales_order_service_lines`

**Status:** ADD

**Owner:** AR Commercial

**Used in flow:** Sales Order / Billing

### What data is stored

Customer-specific commercial service lines. Each line references the current Service Type identity while retaining the negotiated description, quantity, UOM, rate, discount, and amount used by this Sales Order.

### Important columns

```text
id UUID PK
sales_order_id UUID FK -> sales_orders
line_no
service_type_id UUID FK -> service_types
description
quantity
uom
unit_rate
discount_type nullable
discount_value nullable
line_amount
expected_billing_date nullable
status
```

Currency comes from the Sales Order header unless a later approved requirement permits mixed line currencies.

### Relationships

- Sales Order 1:N Service Lines.
- Service Type 1:N Sales Order Service Lines.
- Billing lines can reference their source SO line while retaining transaction snapshots.

### Why do we need this table?

1. One Sales Order can contain multiple billable services.
2. Customer-specific price belongs here, not in `service_types`.
3. Negotiated description and discount can differ from catalogue defaults.
4. Quantity/UOM/amount are repeating line data and cannot fit correctly on the header.
5. The Service Type FK preserves catalogue identity for tax and reporting defaults.
6. Billing can trace an invoice line back to the approved commercial line.

### What happens if we remove this table?

The header would need repeating service columns or one row per Sales Order/service combination, destroying the aggregate. Storing price on Service Type would incorrectly make it universal for all Customers.

### Current decision

Propose a dedicated service-line child because Services and Goods have different catalogue identities.

### Flow

Sales Order → add Service Type → negotiate quantity/rate/discount → approve → create AR Document line.

## `sales_order_goods_lines`

**Status:** ADD

**Owner:** AR Commercial

**Used in flow:** Sales Order / Billing / Goods Dispatch

### What data is stored

Customer-specific commercial goods lines. Each line references a SKU and stores negotiated values without introducing stock, warehouse, reservation, or inventory-movement behavior.

### Important columns

```text
id UUID PK
sales_order_id UUID FK -> sales_orders
line_no
sku_id UUID FK -> skus
description
quantity
uom
unit_rate
discount_type nullable
discount_value nullable
line_amount
expected_billing_date nullable
status
```

### Relationships

- Sales Order 1:N Goods Lines.
- SKU 1:N Sales Order Goods Lines.
- AR Document Goods Lines can reference the source SO Goods Line.

### Why do we need this table?

1. One Sales Order can contain several SKUs.
2. Customer-specific goods pricing and discounts belong to the commercial line.
3. SKU identity preserves HSN/UOM/reporting defaults without freezing live master values into history.
4. Quantity and line amount are repeating data that cannot belong on the header.
5. Billing can trace goods invoice lines to approved ordered quantities and prices.
6. Separate goods lines keep inventory/WMS concepts out of the AR commercial model.

### What happens if we remove this table?

Goods would need to share ambiguous service-line FKs or repeat header rows. A universal line table with both Service Type and SKU could work, but separate tables preserve the already-approved separate catalogue structures and clearer constraints.

### Current decision

Propose a dedicated goods-line child; do not add warehouse, stock, batch, or reservation tables.

### Flow

Sales Order → add SKU → negotiate quantity/rate/discount → approve → bill → optional minimal dispatch data.

## `sales_order_contacts`

**Status:** ADD

**Owner:** AR Commercial

**Used in flow:** Sales Order / Billing Preparation / Delivery Preparation

### What data is stored

The Customer Contacts selected for a specific Sales Order and the role they perform for that order. It is a relation, because one order can use several contacts and one Contact can participate in many orders.

### Important columns

```text
id UUID PK
sales_order_id UUID FK -> sales_orders
customer_contact_id UUID FK -> customer_contacts
role_code
is_primary_for_role
created_at
UNIQUE (sales_order_id, customer_contact_id, role_code)
```

### Relationships

- Sales Order N:M Customer Contacts through this table.
- Customer Contact roles provide defaults; `role_code` here records the order-specific use.

### Why do we need this table?

1. An order may identify Billing, Finance, and Operational contacts together.
2. The same Customer Contact may be used on several orders.
3. A person's general Customer role may differ from their role on one engagement.
4. The unique triple prevents duplicate selections.
5. Billing/delivery preparation can use the approved order contacts as inputs.
6. Repeating contact columns on `sales_orders` would cap the number of contacts and duplicate identities.

### What happens if we remove this table?

The Sales Order could store only fixed contact columns or infer contacts from current Customer roles. That would lose order-specific selections and would change historical commercial context when Customer roles change.

### Current decision

Propose the relation table. It does not duplicate Contact name/email snapshots; delivery requests capture the actual addresses used at send time.

### Flow

Customer Contacts → select order contacts/roles → SO approval → Billing/Delivery recipient preparation.

## `sales_order_documents`

**Status:** ADD

**Owner:** AR Commercial

**Used in flow:** Sales Order / Approval / Billing Audit

### What data is stored

Metadata for Purchase Orders, engagement letters, contracts, and other files supporting a Sales Order. Files remain in object storage.

### Important columns

```text
id UUID PK
sales_order_id UUID FK -> sales_orders
document_type
reference_number nullable
document_date nullable
storage_key
file_name
file_hash nullable
status
uploaded_by, uploaded_at
```

### Relationships

- Sales Order 1:N Documents.
- Submission revision/hash covers the order aggregate and its material supporting-document references.

### Why do we need this table?

1. One order may be supported by several commercial documents.
2. PO/reference numbers and dates are searchable business metadata.
3. Upload actor, time, and hash support approval evidence.
4. Superseded files can remain traceable without physical deletion.
5. Object storage avoids database binary payloads.
6. Repeating document columns on `sales_orders` would impose an arbitrary file limit.

### What happens if we remove this table?

Support files would be unlinked or forced into repeated header columns. Approval would lose the exact commercial references available to reviewers.

### Current decision

Propose a Sales Order-owned file metadata table.

### Flow

Sales Order Draft → attach PO/contract → Submit/Approve → use as billing evidence.

## `sales_order_approval_submissions`

**Status:** ADD

**Owner:** AR Commercial

**Used in flow:** Sales Order / Approval / Audit

### What data is stored

Each immutable Sales Order revision submitted for human approval. It identifies the exact revision/hash, submitter, submission time, and outcome status.

### Important columns

```text
id UUID PK
sales_order_id UUID FK -> sales_orders
revision_no
revision_hash
submitted_by
submitted_at
status
closed_at nullable
UNIQUE (sales_order_id, revision_no)
```

### Relationships

- Sales Order 1:N Approval Submissions.
- Submission 1:N Approval Decisions.
- Shared audit events capture submission and later edits.

### Why do we need this table?

1. It records which commercial revision was submitted.
2. Returned orders can be edited and resubmitted without overwriting the first attempt.
3. It preserves submitter/time independently of current order status.
4. A revision hash protects the submitted content boundary.
5. It provides a stable target for human decisions.
6. It leaves room for later staged decisions without implementing a workflow builder.

### What happens if we remove this table?

The current Sales Order row could show only the latest status. Prior submissions, exact reviewed revision, and resubmission history would be lost.

### Current decision

Replace legacy `sales_order_requests` with explicit revision submissions.

### Flow

SO Draft revision → Submit → immutable submission → Authority decision → approved commercial basis.

## `sales_order_approval_decisions`

**Status:** ADD

**Owner:** AR Commercial

**Used in flow:** Sales Order / Approval / Audit

### What data is stored

Human approval, return, or rejection decisions for a submitted Sales Order revision. Reasons are retained for returned/rejected decisions.

### Important columns

```text
id UUID PK
submission_id UUID FK -> sales_order_approval_submissions
decision
decision_by
decision_at
reason nullable except mandatory for RETURNED/REJECTED
```

### Relationships

- Submission 1:N Decisions.
- Decision actor references existing IAM/user identity.
- Decisions emit shared audit events.

### Why do we need this table?

1. It preserves who took each commercial approval action.
2. It records when the decision occurred.
3. Return/rejection reasons guide the next revision.
4. It keeps decision history when the order status later changes.
5. It distinguishes business approval evidence from generic field-change audit.
6. It supports future additional human decisions without route-builder tables.

### What happens if we remove this table?

Decision evidence would be reduced to mutable header fields, losing earlier actors, timestamps, and reasons.

### Current decision

Replace legacy `sales_order_actions` with decisions tied to an immutable submission.

### Flow

Sales Order Submission → Approve/Return/Reject → optional edit/resubmit → Billing eligibility.

## `sales_order_billing_schedules`

**Status:** REVIEW

**Owner:** AR Commercial

**Used in flow:** Sales Order / Billing Generation

### What data is stored

If the enabled release must generate Advance, Milestone, Periodic, or Recurring bills, this child would hold each planned billing obligation or recurrence state. Detailed schedule semantics are not yet frozen, so it is not an approved MVP table.

### Important columns

```text
id UUID PK
sales_order_id UUID FK -> sales_orders
billing_type
planned_date nullable
percentage nullable
amount nullable
frequency_code nullable
start_date nullable
end_date nullable
next_run_at nullable
status
last_generated_document_id nullable FK -> ar_documents
```

Columns are illustrative pending the recurring/milestone specification; do not implement incompatible nullable combinations before that review.

### Relationships

- Sales Order 1:N Billing Schedule rows if enabled.
- A Schedule row may generate several AR Documents for recurrence, or one document for a dated obligation; exact cardinality is **TBD**.

### Why do we need this table?

1. Recurring billing needs persisted next-run and generation state across worker restarts.
2. Milestone/periodic agreements can have several planned billing obligations per Sales Order.
3. Generated documents must trace to the commercial schedule entry.
4. Status can stop or complete a schedule independently of the order header.
5. Keeping schedules on the Sales Order preserves deal-specific behavior.
6. Header-only recurrence fields cannot represent multiple milestones or generated occurrences.

### What happens if we remove this table?

Removal is safe for a release that creates bills manually from approved Sales Orders. If automated recurrence/milestones are in the release, header fields would be insufficient and generation could duplicate after retries.

### Current decision

Review with the Sales Order/Recurring Billing specification. Do not implement merely because recurring billing is a future product capability; do not move it into Company Configuration.

### Flow

Approved Sales Order → optional planned/recurring schedule → idempotent draft AR Document generation → Approval.

# 17. Billing, Filing, Approval, Artifact, and Delivery Tables

## `ar_documents`

**Status:** ADD

**Owner:** AR Billing

**Used in flow:** Billing / Approval / Delivery / Receivables / Receipt / Collections

### What data is stored

The common header for PI, TI, CN, and DN with explicit document and transaction classifications. It supports Customer Sales and same-Company Inter-Unit documents while preserving structured transaction-time legal, tax, currency, commercial, presentation, and settlement meaning.

### Important columns

```text
id UUID PK
tenant_id UUID FK -> tenants
company_id UUID FK -> companies
transaction_classification               -- CUSTOMER_SALE / INTER_UNIT
customer_id UUID nullable FK -> customers
sales_order_id UUID nullable FK -> sales_orders
source_billing_schedule_id UUID nullable FK -> sales_order_billing_schedules [only if enabled]
document_type                           -- PI / TI / CN / DN
document_date
financial_year_id UUID FK -> financial_years
seller_gst_registration_id UUID FK -> company_gst_registrations
seller_location_id UUID FK -> company_locations
destination_gst_registration_id UUID nullable FK -> company_gst_registrations
destination_location_id UUID nullable FK -> company_locations
customer_gst_registration_id UUID nullable FK -> customer_gst_registrations
bill_to_customer_location_id UUID nullable FK -> customer_locations
ship_to_type nullable                      -- CUSTOMER_LOCATION / COMPANY_LOCATION
ship_to_customer_location_id UUID nullable FK -> customer_locations
ship_to_company_location_id UUID nullable FK -> company_locations
supply_type_code
place_of_supply_state_code nullable
currency_code FK -> currencies
exchange_rate_id UUID nullable FK -> exchange_rates
exchange_rate_used
base_currency_code
payment_term_id UUID nullable FK -> payment_terms
due_date nullable
bank_account_id UUID nullable FK -> company_bank_accounts
receivable_gl_account_id UUID nullable FK -> gl_accounts
business_segment_id UUID nullable FK -> cost_center_business_segments
team_id UUID nullable FK -> teams
document_sequence_id UUID nullable FK -> document_sequences
document_number nullable until finalization
current_revision_no
status
approval_status
taxable_total
cgst_total
sgst_total
igst_total
tcs_total
other_adjustment_total
gross_total
base_currency_gross_total nullable
seller_legal_name_snapshot
seller_pan_snapshot nullable
seller_gstin_snapshot nullable
seller_address_*_snapshot
customer_legal_name_snapshot nullable
customer_pan_snapshot nullable
customer_gstin_snapshot nullable
bill_to_*_snapshot nullable
ship_to_*_snapshot nullable
destination_company_legal_name_snapshot nullable
destination_gstin_snapshot nullable
destination_address_*_snapshot nullable
payment_term_name_snapshot nullable
credit_days_snapshot nullable
bank_*_snapshot nullable
branding_id nullable FK -> company_document_branding
template_id nullable FK -> company_document_templates
reminder_enabled_override nullable
reminder_hold_until nullable
reminder_hold_reason nullable
historical_override_used
historical_override_reason nullable
historical_override_by nullable
historical_override_at nullable
einvoice_status nullable                   -- NOT_REQUIRED / PENDING / GENERATED / CANCELLED
irn nullable
irn_acknowledgement_number nullable
irn_generated_at nullable
irn_generated_by nullable
submitted_at nullable
approved_at nullable
finalized_at nullable
cancelled_at nullable
created_by, created_at, updated_by, updated_at
UNIQUE (company_id, document_type, document_number) where document_number is not null
```

The `*_snapshot` groups are ordinary typed columns, not one giant snapshot JSON. `exchange_rate_used` is the actual rate applied; exact automatic rate selection remains TBD. `historical_override_reason/by/at` are mandatory together when a policy-permitted restricted-period exception is used. `receivable_gl_account_id` snapshots the effective Company default for eligible Customer-Sale receivable effects; it is null where the document creates no normal receivable. `outstanding_amount` is intentionally absent as an authoritative duplicate; only eligible `CUSTOMER_SALE` document effects participate in the derived receivable position. `INTER_UNIT` documents never create normal Customer AR outstanding.

`CUSTOMER_SALE` requires `customer_id` and excludes internal destination fields. `INTER_UNIT` requires source and destination GST Registration/Location within the same Company, requires different source and destination GST Registrations, and uses no Customer. Ship-To requires exactly one matching reference for its discriminator. Successful e-invoice/IRN generation is represented by `einvoice_status = GENERATED` with its IRN evidence and creates a hard edit lock.

### Relationships

- Company and optional Sales Order each have 1:N AR Documents; Customer has 1:N `CUSTOMER_SALE` AR Documents.
- AR Document 1:N Lines, relations, approval submissions, artifacts, delivery requests, payment allocations, settlement adjustments through allocations, and reminder occurrences.
- AR Document 1:0..1 Dispatch Details in the proposed simple goods model.
- Master FKs retain source identity; structured snapshots retain finalized historical truth.
- AR Document N:M GSTR-1 Filing Batches through auditable filing-batch membership.

### Why do we need this table?

1. PI, TI, CN, and DN share seller/destination/date/currency/totals/approval structure without four duplicated headers.
2. `document_type` supports explicit type-specific validation and accounting/settlement behavior.
3. Finalized snapshots prevent later Company, Customer, location, tax, terms, bank, or branding edits from changing historical output.
4. Seller Company, GSTIN, and Location remain explicit and independently validated billing context.
5. The header owns approval/finalization state and the final non-reusable number.
6. Receipts and reminders use only eligible Customer-Sale documents, while delivery, filing, e-invoice evidence, and document relations need one stable document identity for both classifications.

### What happens if we remove this table?

Four separate document headers would repeat nearly all columns and make shared approval, delivery, relations, and settlement inconsistent. A generic untyped invoice table would also be wrong; the explicit type and type-specific guards are required.

### Current decision

Propose one typed AR Document aggregate. GST/Tax Treatment values are confirmed; before an affected route is enabled, freeze PI/TI/CN/DN balance effects, CN/DN eligibility, correction/cancellation behavior, FX rules, and historical-override authorization. Finalization must revalidate seller/destination context, allowed currency/rate, tax, numbering, human approval, and LUT where required for the current without-payment routes `EXPWOP` and `SEZWOP`. `EXPWP` and `SEZWP` are not blocked solely for missing LUT. Inter-Unit accounting/clearing remains open for future Accounting clearing/balancing design.

### Flow

SO/manual Billing Draft → validate classification/context/tax/LUT → Submit → human decision → number/finalize → PDF/Delivery → filing/e-invoice controls → settlement/reminders only for eligible Customer Sales.

## `ar_document_lines`

**Status:** ADD

**Owner:** AR Billing

**Used in flow:** Billing / Approval / PDF / Tax / Reporting

### What data is stored

Service and Goods transaction lines for every AR Document. A line keeps a reference to the source catalogue/Sales Order identity and also stores the description, UOM, HSN/SAC, prices, Base GST Nature, transaction-level GST outcome where applicable, actual rates, components, TCS determination, and amounts actually used.

### Important columns

```text
id UUID PK
document_id UUID FK -> ar_documents
line_no
line_type                              -- SERVICE / GOODS
service_type_id UUID nullable FK -> service_types
sku_id UUID nullable FK -> skus
sales_order_service_line_id UUID nullable FK -> sales_order_service_lines
sales_order_goods_line_id UUID nullable FK -> sales_order_goods_lines
description_snapshot
uom_snapshot
hsn_sac_code_snapshot
hsn_sac_description_snapshot nullable
base_tax_treatment_code_snapshot      -- TAXABLE / NIL_RATED / EXEMPT / NON_GST
zero_rated_outcome_snapshot nullable  -- transaction result/context, not catalogue nature
quantity
unit_rate
discount_type nullable
discount_value nullable
taxable_value
gst_rate_snapshot nullable
revenue_gl_account_id UUID FK -> gl_accounts
cgst_rate, cgst_amount
cgst_gl_account_id UUID nullable FK -> gl_accounts
sgst_rate, sgst_amount
sgst_gl_account_id UUID nullable FK -> gl_accounts
igst_rate, igst_amount
igst_gl_account_id UUID nullable FK -> gl_accounts
tcs_check_required_snapshot
tcs_applicability_decision nullable     -- APPLICABLE / NOT_APPLICABLE / NOT_REQUIRED
tcs_section_code_snapshot nullable
tcs_rate_snapshot nullable
tcs_amount
line_total
base_taxable_value nullable
base_line_total nullable
UNIQUE (document_id, line_no)
```

Exactly one of `service_type_id` or `sku_id` must match `line_type`; the same applies to source SO line FKs. The HSN/SAC description is snapshotted when required for issued output. `tcs_check_required_snapshot = true` requires an explicit applicability decision, but does not automatically charge TCS. TCS section/rate/amount are populated only when the final Billing/Tax rules determine that TCS applies.

### Relationships

- AR Document 1:N Lines.
- Service Type or SKU 1:N AR Document Lines as source identity.
- Optional Sales Order Service/Goods Line 1:N billed lines, subject to quantity/value rules still to be specified.
- GL Account 1:N finalized AR Document Lines as the resolved revenue or applicable tax-component account.

### Why do we need this table?

1. A financial document can contain several service or goods items.
2. Catalogue FKs preserve source identity while snapshots preserve the approved transaction values.
3. Line-level HSN/SAC and GST components are needed for statutory output and totals.
4. Customer price, discount, taxable value, and line total are transaction data.
5. Resolved revenue and tax-component GL references preserve accounting classification when Company mappings change later.
6. TCS applicability and source SO-line traceability remain on the same finalized business line.

### What happens if we remove this table?

Repeating line columns would overload the header and impose an arbitrary item limit. Reading current Service Type/SKU values later would corrupt historical invoices. Separate service and goods document-line tables are possible but would duplicate tax and amount structure.

### Current decision

Propose one line table with strict line-type constraints. Billing automatically resolves `revenue_gl_account_id` using specific Supply Type + HSN/SAC first, then the general Supply-Type mapping. Applicable CGST/SGST/IGST account references resolve from Company Tax GL mappings. Missing or ambiguous active mappings block finalization; the invoice user does not normally choose these accounts. Catalogue Base GST Nature uses the confirmed four-value classification; future Billing derives the final outcome from Supply Type and other transaction context and snapshots both the base nature and actual result. Advanced TCS charging rules remain **REVIEW** before affected charging paths are released.

### Flow

SO/catalogue selection → Supply Type and HSN/SAC known → resolve Revenue GL → calculate components and resolve Tax GL account(s) → submit/approve → preserve final account references and immutable PDF/reporting values.

## `ar_document_relations`

**Status:** ADD

**Owner:** AR Billing

**Used in flow:** Billing / PI Conversion / Credit Note / Debit Note / Corrections / Receipt Transfer

### What data is stored

Explicit typed relationships between AR Documents. Current relation types are limited to approved cases such as `CONVERTED_TO`, `CREDIT_NOTE_FOR`, `DEBIT_NOTE_FOR`, `ADJUSTS`, and `REVERSAL_OF` as each module rule is frozen.

### Important columns

```text
id UUID PK
tenant_id UUID FK -> tenants
source_document_id UUID FK -> ar_documents
related_document_id UUID FK -> ar_documents
relation_type
related_amount nullable
reason nullable
created_by, created_at
UNIQUE (source_document_id, related_document_id, relation_type)
CHECK (source_document_id <> related_document_id)
```

Direction is defined by `relation_type`; for example a PI source `CONVERTED_TO` a TI related document. `related_amount` is used only if an approved partial relation needs it.

### Relationships

- AR Document N:M AR Documents through typed relations.
- PI-to-TI allocation transfers refer to the related documents indirectly through immutable source/replacement allocations.

### Why do we need this table?

1. PI-to-TI conversion must be queryable without arbitrary reference text.
2. CN/DN must identify the financial document they affect.
3. Correction/reversal lineage must survive number and status changes.
4. One document may relate to several documents and one source may receive several adjustments.
5. Typed relations allow eligibility and total checks for each approved relation type.
6. Reports and audit can follow document lineage directly.

### What happens if we remove this table?

References would become free text or multiple nullable columns on `ar_documents`. That would limit cardinality, weaken FKs, and make PI conversion or CN/DN lineage unreliable.

### Current decision

Propose the relation table, while marking exact CN/DN eligibility and partial-adjustment rules **REVIEW**. Do not add speculative relation types.

### Flow

Source AR Document → create conversion/adjustment/correction → persist typed relation → validate balances and audit lineage.

## `gstr1_filing_batches`

**Status:** ADD

**Owner:** AR Tax / Compliance

**Used in flow:** GSTR-1 Preparation / Filing / Invoice Edit Control / Audit

### What data is stored

The auditable header for one GSTR-1 return/filing batch, identified by GST Registration + Return Period + Return Type. Only `FILED` status makes included invoice membership a hard edit lock.

### Important columns

```text
id UUID PK
tenant_id UUID FK -> tenants
company_id UUID FK -> companies
gst_registration_id UUID FK -> company_gst_registrations
return_period
return_type
status                                 -- DRAFT / FILED
filing_reference nullable
filed_at nullable
filed_by nullable
created_by, created_at, updated_by, updated_at
UNIQUE (gst_registration_id, return_period, return_type)
```

`filing_reference`, `filed_at`, and `filed_by` are required together when status becomes `FILED`. A filed batch and its membership are immutable except through a separately approved statutory correction process.

### Relationships

- Company and GST Registration each have 1:N filing batches over return periods/types.
- GSTR-1 Filing Batch N:M AR Documents through `gstr1_filing_batch_documents`.

### Why do we need this table?

1. Filing status belongs to a return batch, not to an isolated invoice boolean.
2. GST Registration, Return Period, and Return Type define the filing context that was submitted.
3. Filing reference, timestamp, and actor provide auditable statutory evidence.
4. `DRAFT` and `FILED` batch statuses require different edit-lock behavior.
5. One batch groups the exact invoices filed together.
6. The batch gives the edit guard one authoritative `FILED` state to evaluate.

### What happens if we remove this table?

A generic invoice filing flag could not explain which GST Registration, period, return type, filing reference, or actor created the lock. `DRAFT` status would be indistinguishable from `FILED` status.

### Current decision

Add the batch. The hard rule is: **Invoice included in a FILED GSTR-1 return / filing batch.** A `DRAFT` batch does not permanently lock its invoices.

### Flow

Create DRAFT batch → identify GST Registration + Return Period + Return Type → add/remove documents with audit → file → freeze batch and membership → hard-lock included invoices.

## `gstr1_filing_batch_documents`

**Status:** ADD

**Owner:** AR Tax / Compliance

**Used in flow:** GSTR-1 Preparation / Filing / Invoice Edit Control / Audit

### What data is stored

Auditable membership of AR Documents in a GSTR-1 filing batch, including draft additions/removals and the exact active membership frozen when the batch is filed.

### Important columns

```text
id UUID PK
gstr1_filing_batch_id UUID FK -> gstr1_filing_batches
document_id UUID FK -> ar_documents
membership_status                     -- INCLUDED / REMOVED
added_by
added_at
removed_by nullable
removed_at nullable
removal_reason nullable
UNIQUE (gstr1_filing_batch_id, document_id)
```

Draft membership changes retain actor/time/reason evidence on the membership row and in `audit_events`, including repeated remove/re-add actions. When the parent batch becomes `FILED`, active `INCLUDED` rows are frozen. Only an active included row whose parent is `FILED` creates the hard invoice edit lock.

### Relationships

- GSTR-1 Filing Batch 1:N Document Membership rows.
- AR Document 1:N filing membership rows over filing contexts.

### Why do we need this table?

1. A batch contains many invoices and an invoice may appear in different permitted filing contexts over time.
2. The exact documents included in a filed return must be auditable.
3. Draft add/remove activity must remain visible without permanently locking the invoice.
4. Membership cannot be represented safely by an array or comma-separated IDs on the batch.
5. The row gives a direct relational test for the filed edit lock.
6. Immutable filed membership supports later cancellation/amendment/CN-DN traceability without rewriting history.

### What happens if we remove this table?

The batch could not identify its exact filed invoices with referential integrity, and draft membership changes would either be lost or incorrectly treated as permanent locks.

### Current decision

Add the membership table. Draft membership is changeable with audit; filed membership is immutable and locks only the included invoice.

### Flow

Eligible invoice → add to DRAFT batch → optionally remove/re-add with audit → batch becomes FILED → included membership freezes and edit guard activates.

## `ar_document_dispatch_details`

**Status:** REVIEW

**Owner:** AR Billing

**Used in flow:** Goods Billing / Dispatch / POD / GRN

### What data is stored

One simple dispatch/transport block for a goods AR Document if the enabled MVP requires those fields. It is a 1:1 child rather than a warehouse, shipment, inventory, or logistics aggregate.

### Important columns

```text
document_id UUID PK/FK -> ar_documents
dispatch_date nullable
delivery_date nullable
dispatch_from_snapshot nullable
vehicle_number nullable
vehicle_type nullable
lr_number nullable
lr_date nullable
airway_bill_number nullable
airway_bill_date nullable
shipping_bill_number nullable
shipping_bill_date nullable
eway_bill_number nullable
eway_bill_date nullable
dispatch_document_number nullable
pod_storage_key nullable
pod_received_at nullable
grn_reference nullable
grn_date nullable
updated_by, updated_at
```

### Relationships

- Goods AR Document 1:0..1 Dispatch Details under the proposed simple MVP.
- Any POD file is referenced by storage key; no WMS or stock-movement children are introduced.

### Why do we need this table?

1. Goods invoices may need several transport fields that do not apply to service documents.
2. A 1:1 child keeps the common AR header from becoming dominated by nullable logistics columns.
3. Dispatch/POD/GRN data may arrive after the commercial line is created.
4. The block can be displayed on the document and used for customer follow-up.
5. Storage references retain POD evidence without binary database storage.
6. The model remains deliberately limited to one simple dispatch per document.

### What happens if we remove this table?

Removal is safe if current goods billing does not capture dispatch data. If the fields are required, they could be placed on `ar_documents`, but that would add many service-inapplicable columns; multiple shipments would require a later redesign.

### Current decision

Review with the Billing/Goods requirements. Implement only if one simple invoice-level dispatch block is confirmed; a multiple-shipment or warehouse design is deferred.

### Flow

Goods AR Document → optional Dispatch details → POD/GRN update → Delivery/Collections evidence.

## `document_approval_submissions`

**Status:** ADD

**Owner:** AR Billing

**Used in flow:** Billing / Approval / Finalization / Audit

### What data is stored

Each immutable AR Document revision submitted for human approval. It is the stable decision target and records the policy/version reference only when an approved Company-specific policy record exists.

### Important columns

```text
id UUID PK
document_id UUID FK -> ar_documents
revision_no
revision_hash
submitted_by
submitted_at
status
approval_setting_id UUID nullable FK -> company_approval_settings
closed_at nullable
UNIQUE (document_id, revision_no)
```

`approval_setting_id` stays nullable because `company_approval_settings` itself is under review; a fixed product route can be identified by an application route/version code if needed.

### Relationships

- AR Document 1:N Approval Submissions.
- Submission 1:N Approval Decisions.
- Finalization accepts only an approved submission whose revision/hash still matches the document aggregate.

### Why do we need this table?

1. Human approval must apply to an exact document revision.
2. Returned documents can be edited and resubmitted without overwriting earlier evidence.
3. Submitter and submission timestamp are required independently of current header status.
4. The revision hash detects material changes between review and finalization.
5. It gives decisions a stable FK rather than attaching them to mutable document state.
6. It keeps future multi-stage decisions possible without a workflow builder.

### What happens if we remove this table?

Approval could only point to the current AR Document row, so later edits would make it unclear what was approved. Audit events alone would not enforce revision-specific finalization.

### Current decision

Propose one submission per document revision for the current human approval stage. Finance edit/self-approval semantics remain **REVIEW**; material edits require a new revision and decision evidence.

### Flow

AR Draft revision → Submit → immutable submission → authorized decision → guarded finalization.

## `document_approval_decisions`

**Status:** ADD

**Owner:** AR Billing

**Used in flow:** Billing / Approval / Historical Override / Audit

### What data is stored

Human decisions on an AR Document submission. Current decisions are `APPROVED`, `RETURNED`, and `REJECTED`; an authorized edit is an audited revision change followed by the applicable submission/decision path.

### Important columns

```text
id UUID PK
submission_id UUID FK -> document_approval_submissions
decision
decision_by
decision_at
reason nullable except mandatory for RETURNED/REJECTED
historical_override_authorized
historical_override_reason nullable
```

When a decision authorizes a policy-permitted restricted-period posting/edit, the override reason is mandatory and a matching shared audit event must be written.

### Relationships

- Approval Submission 1:N Decisions.
- Decision actor references existing IAM/user identity and authorization.
- An approved current-revision decision is required by finalization.

### Why do we need this table?

1. It preserves the authorized human action, actor, and time.
2. Return/rejection reasons remain available after resubmission.
3. It records whether a historical exception was explicitly authorized.
4. A separate child retains all decisions rather than overwriting header fields.
5. It distinguishes approval evidence from generic audit/change evidence.
6. Later additional stages can add decisions against the same submission without replacing this model.

### What happens if we remove this table?

The system would lose durable approval/return/rejection evidence and historical-override authorization. Header status could be changed without a specific human decision record.

### Current decision

Propose a decision child. Do not add workflow definition, stage, transition, or action-builder tables.

### Flow

Submission → Approve/Return/Reject → optional override evidence → number/finalize or revise.

## `document_artifacts`

**Status:** ADD

**Owner:** AR Billing

**Used in flow:** PDF Generation / Invoice Delivery / Audit / Historical Reproduction

### What data is stored

Metadata for the exact generated artifact of a finalized document, currently PDF. The file remains in object storage; the row pins the document revision, template/branding context, hash, and renderer evidence.

### Important columns

```text
id UUID PK
document_id UUID FK -> ar_documents
artifact_type                         -- PDF for current MVP
document_revision_no
document_revision_hash
template_id UUID nullable FK -> company_document_templates
branding_id UUID nullable FK -> company_document_branding
storage_key
file_hash
renderer_version
generated_by nullable
generated_at
status
```

### Relationships

- AR Document 1:N Artifacts, allowing regeneration as a new retained artifact when explicitly permitted.
- Artifact 1:N Invoice Delivery Requests.
- References the exact template/branding records used.

### Why do we need this table?

1. The system must resend the exact approved PDF rather than rebuild it from current masters.
2. File hash proves artifact integrity.
3. Template, branding, document revision, and renderer identify how the output was produced.
4. A replacement/regenerated artifact can coexist with the original for audit.
5. Delivery requests can attach a stable artifact ID.
6. Object storage avoids storing large PDF binaries in PostgreSQL.

### What happens if we remove this table?

Every resend would regenerate from mutable templates/branding and might differ from the originally approved output. A storage key on `ar_documents` could support only one artifact and would lose regeneration history.

### Current decision

Propose artifact metadata for finalized document PDFs; never store the binary in PostgreSQL under the current storage direction.

### Flow

Finalized AR Document → render exact revision → store PDF/object metadata → Delivery/Resend/Audit.

## `invoice_delivery_requests`

**Status:** ADD

**Owner:** AR Billing

**Used in flow:** Invoice Delivery / Manual Send / Resend / Audit

### What data is stored

One durable request to send a finalized AR Document artifact. It snapshots the resolved sender, recipients, CC, template, subject/body version, and attachment so later configuration/contact changes do not rewrite send intent.

### Important columns

```text
id UUID PK
tenant_id UUID FK -> tenants
company_id UUID FK -> companies
document_id UUID FK -> ar_documents
artifact_id UUID FK -> document_artifacts
send_type                              -- AUTO / MANUAL / RESEND
sender_email_snapshot
reply_to_snapshot nullable
to_recipients_snapshot                 -- typed text array
cc_recipients_snapshot nullable         -- typed text array
email_template_id UUID nullable FK -> company_document_templates
subject_snapshot
body_storage_key_or_hash nullable
requested_by nullable
requested_at
idempotency_key
status
completed_at nullable
UNIQUE (company_id, idempotency_key)
```

Recipient arrays represent the exact small recipient list for one request; they are not live Contact references. Provider credentials and Company defaults remain in the approved configuration tables.

### Relationships

- AR Document 1:N Delivery Requests.
- Document Artifact 1:N Delivery Requests.
- Delivery Request 1:N Delivery Attempts.
- Optional template FK identifies the source version, while subject/recipient snapshots preserve the resolved send intent.

### Why do we need this table?

1. Invoice approval must commit independently of external email success.
2. A durable request lets an asynchronous worker resume after restart.
3. Manual send and resend are distinct user intents, not retries of the same request.
4. Recipient/sender/template snapshots preserve what was intended at that time.
5. Idempotency prevents duplicate requests during API retry.
6. Users can see queued, processing, sent, or failed delivery state without changing financial status.

### What happens if we remove this table?

Email would need to run synchronously during approval or rely on an ephemeral queue message. Send intent, resolved recipients, and durable retry ownership would be lost.

### Current decision

Propose durable asynchronous delivery requests. Do not copy `email_provider_configs` or `company_invoice_delivery_settings` into runtime tables.

### Flow

Finalized document/artifact → auto/manual send request → worker attempts → sent/failed history; financial approval remains committed.

## `invoice_delivery_attempts`

**Status:** ADD

**Owner:** AR Billing

**Used in flow:** Invoice Delivery / Retry / Operations / Audit

### What data is stored

Each provider attempt made for one delivery request. It records attempt number, timing, provider identifiers, outcome, and bounded diagnostic information.

### Important columns

```text
id UUID PK
delivery_request_id UUID FK -> invoice_delivery_requests
attempt_no
provider_message_id nullable
attempted_at
completed_at nullable
status
error_code nullable
error_message nullable
provider_response_hash nullable
UNIQUE (delivery_request_id, attempt_no)
```

### Relationships

- Delivery Request 1:N Attempts.
- Attempts use the provider selected from existing configuration at execution time; provider credentials are never copied here.

### Why do we need this table?

1. One send request may require several retries.
2. Provider message ID supports reconciliation when the outcome is delayed or uncertain.
3. Operators and users need to see each failure and eventual success.
4. Attempt numbers prevent retry history from being overwritten.
5. Diagnostic codes support support investigation without changing document approval.
6. Delivery reliability can be measured separately from financial processing.

### What happens if we remove this table?

Only the latest request status would remain, hiding provider failures, retries, and unknown outcomes. Repeated attempts could not be distinguished from user-requested resends.

### Current decision

Propose one append-oriented attempt child per provider call. Email remains outside the invoice finalization transaction.

### Flow

Queued delivery request → attempt → success or retryable/final failure → update request outcome → audit.

# 18. Receipts, Settlement, and Collections Tables

## `receipts`

**Status:** ADD

**Owner:** AR Receipts

**Used in flow:** Payment Register / Receipt / Knock-off / Reporting

### What data is stored

The cash receipt received from a Customer. Its amount represents cash only; TDS, waiver, write-off, and other non-cash settlement must never inflate it.

### Important columns

```text
id UUID PK
tenant_id UUID FK -> tenants
company_id UUID FK -> companies
customer_id UUID FK -> customers
company_bank_account_id UUID FK -> company_bank_accounts
receipt_reference
external_reference_utr nullable
payment_date
value_date nullable
payment_mode_code
currency_code FK -> currencies
cash_amount
exchange_rate_id UUID nullable FK -> exchange_rates
exchange_rate_used nullable
base_currency_cash_amount nullable
remarks nullable
status
received_by nullable
created_by, created_at, updated_at
```

`exchange_rate_used` and base value are populated only when an approved Receipt FX rule requires conversion. Allocated and unallocated cash are derived from `cash_amount` and active allocation rows rather than stored as independently editable balances.

### Relationships

- Company and Customer each have 1:N Receipts.
- Company Bank Account 1:N Receipts.
- Receipt 1:N Payment Allocations; Receipt N:M AR Documents through those allocations.
- TDS/non-cash adjustments are children of allocations, not additions to Receipt cash.

### Why do we need this table?

1. A bank/customer payment is a business event with its own reference, date, currency, and amount.
2. One cash receipt may be allocated to several AR Documents.
3. Unallocated cash must remain visible until later knock-off.
4. Bank account and UTR/reference support reconciliation and duplicate detection.
5. Foreign-currency cash must retain its original currency and amount.
6. Keeping cash separate enforces the conservation rule: receipt cash equals active cash allocations plus unallocated cash.

### What happens if we remove this table?

Cash identity would be duplicated on each invoice allocation, making one bank receipt appear as several payments. Unallocated cash, UTR reconciliation, and receipt-level reversal would be lost.

### Current decision

Replace legacy `payment_receipts`/misspelled `payment_reciepts` with `receipts`. Cross-currency allocation/rate selection remains **REVIEW**; same-currency EEFC receipt and knock-off remain supported.

### Flow

Register cash receipt → validate Company/Customer/bank/currency → allocate now or retain unallocated cash → report/reconcile.

## `payment_allocations`

**Status:** ADD

**Owner:** AR Receipts

**Used in flow:** Knock-off / Receivables / PI-to-TI Transfer / Reversal

### What data is stored

Each application of receipt cash to one eligible `CUSTOMER_SALE` AR Document. `INTER_UNIT` documents are ineligible for normal Customer knock-off. Allocations are append-oriented and retain reversals; one mutable `invoice.payment_id` is not used.

### Important columns

```text
id UUID PK
receipt_id UUID FK -> receipts
document_id UUID FK -> ar_documents
allocated_cash_receipt_currency
applied_cash_document_currency
exchange_rate_used nullable
allocation_date
status                                 -- ACTIVE / REVERSED
reversal_of_allocation_id UUID nullable FK -> payment_allocations
reversed_by nullable
reversed_at nullable
reversal_reason nullable
created_by, created_at
```

Receipt-currency and document-currency values are both explicit so future approved cross-currency behavior does not reinterpret one ambiguous amount. For same-currency knock-off they are equal and the allocation rate is 1.

### Relationships

- Receipt 1:N Payment Allocations.
- AR Document 1:N Payment Allocations.
- Receipt N:M AR Documents through allocations.
- Allocation 1:N Settlement Adjustments.
- Allocation may participate as the source or replacement in Allocation Transfers.

### Why do we need this table?

1. One Receipt can settle several documents.
2. One document can receive cash from several Receipts.
3. Partial allocation and unallocated cash require per-application amounts.
4. Reversal history must remain instead of deleting or overwriting the original link.
5. PI-to-TI reallocation needs the original and replacement allocation identities.
6. Separate receipt/document currency amounts prevent FX ambiguity when that feature is approved.

### What happens if we remove this table?

The N:M relationship cannot be represented by a single receipt ID on an invoice. Partial/multi-document knock-off, reversals, and transfer history would be lost.

### Current decision

Propose an append-oriented allocation relation. `INTER_UNIT` is excluded. Eligibility for Customer-Sale PI/TI/DN/CN and cross-currency rules must be frozen before those paths are enabled.

### Flow

Receipt cash → select eligible document(s) → create active allocation(s) → derive outstanding/unallocated amounts → reverse/transfer with history if required.

## `settlement_adjustments`

**Status:** ADD

**Owner:** AR Receipts

**Used in flow:** Knock-off / TDS Settlement / Receivables / Audit

### What data is stored

Non-cash amounts applied with a Payment Allocation. The current MVP uses `TDS`; possible waiver/write-off/other types are not enabled until their business and authorization rules are approved.

### Important columns

```text
id UUID PK
payment_allocation_id UUID FK -> payment_allocations
adjustment_type                         -- TDS for current MVP
amount_document_currency
tax_statutory_code_id UUID nullable FK -> tax_statutory_codes
tax_statutory_code_rate_id UUID nullable FK -> tax_statutory_code_rates
section_code_snapshot nullable
rate_snapshot nullable
calculation_base nullable
resolved_gl_account_id UUID nullable FK -> gl_accounts
reason nullable
status                                  -- ACTIVE / REVERSED
reversal_of_adjustment_id UUID nullable FK -> settlement_adjustments
created_by, created_at
reversed_by nullable
reversed_at nullable
reversal_reason nullable
```

For TDS, the user selects an applicable section/code, the system resolves its configured applicable rate, and the row records the selected code/rate and calculated amount. Advanced thresholds, cumulative tracking, and sophisticated override logic are not represented here.

### Relationships

- Payment Allocation 1:N Settlement Adjustments.
- AR Document 1:N Settlement Adjustments through the parent allocations; no duplicate document FK is stored.
- TDS adjustments reference shared Tax Statutory Code/rate masters and retain transaction snapshots.
- Where accounting resolution is enabled, `resolved_gl_account_id` preserves the effective Company mapping used for the adjustment.

### Why do we need this table?

1. TDS settles part of a receivable but is not cash received.
2. One allocation may require more than one approved non-cash component over time.
3. Section/code and configured rate must be preserved with the transaction.
4. Reversal must retain the original adjustment rather than overwrite it.
5. Separate rows keep Receipt cash conservation mathematically correct.
6. Later waiver/write-off types can be added only after their own controls are approved, without altering cash identity.

### What happens if we remove this table?

TDS would have to be added to receipt cash or embedded in fixed allocation columns. The former falsifies bank cash; the latter cannot support multiple adjustment types or independent reversal evidence.

### Current decision

Propose the child table for the current simple TDS flow. Do not implement automatic withholding thresholds/cumulative engines or enable waiver/write-off types from this schema proposal alone.

### Flow

Receipt allocation → TDS applicable → select section/code → derive configured rate → calculate/record TDS → cash plus active TDS settles receivable.

## `allocation_transfers`

**Status:** ADD

**Owner:** AR Receipts

**Used in flow:** PI-to-TI Conversion / Knock-off / Audit

### What data is stored

The explicit history linking an original PI allocation reversal to the replacement TI allocation. The original allocation is never deleted or rewritten as though the Customer originally paid the TI.

### Important columns

```text
id UUID PK
source_allocation_id UUID FK -> payment_allocations
replacement_allocation_id UUID FK -> payment_allocations
transferred_cash_receipt_currency
transferred_amount_document_currency
transferred_by
transferred_at
reason
UNIQUE (replacement_allocation_id)
```

The source and target documents are derived from immutable allocation FKs, preventing redundant document IDs from drifting. The source allocation is reversed with a reason, and the replacement allocation is a new row against the TI.

### Relationships

- Payment Allocation 1:N outbound Transfer records if partial transfer is approved.
- Each Transfer points to exactly one replacement allocation.
- Both allocations point to the same Receipt; application validation enforces the approved PI-to-TI document relation.

### Why do we need this table?

1. It answers where cash was originally allocated.
2. It records when and by whom allocation moved from PI to TI.
3. It links the exact source reversal and replacement allocation.
4. It prevents conversion from double-counting settlement on PI and TI.
5. It supports partial transfers if later approved without deleting history.
6. Audit and customer statements can explain the movement clearly.

### What happens if we remove this table?

Separate reversal and new-allocation rows would exist but their business relationship would be implicit. The system could not reliably answer which TI replacement came from a specific PI allocation.

### Current decision

Propose linked reversal plus new allocation with this transfer record. Exact PI/TI balance behavior and partial-transfer eligibility remain **REVIEW** before release.

### Flow

PI allocation → PI converted to TI → reverse original allocation → create TI allocation → link both in Transfer → recompute positions.

## `reminder_occurrences`

**Status:** ADD

**Owner:** AR Collections

**Used in flow:** Reminder Planning / Collections / Invoice Delivery / Audit

### What data is stored

Each planned, sent, skipped, cancelled, or failed reminder occurrence for one AR Document and schedule rule. It records what actually happened while Company policy remains in `reminder_policies` and `reminder_schedule_rules`.

### Important columns

```text
id UUID PK
document_id UUID FK -> ar_documents
schedule_rule_id UUID FK -> reminder_schedule_rules
due_date_snapshot
planned_send_at
evaluated_at nullable
actual_send_at nullable
status
recipient_snapshot nullable
template_id UUID nullable FK -> company_document_templates
delivery_request_id UUID nullable FK -> invoice_delivery_requests
skip_reason nullable
policy_revision_or_hash nullable
created_at, updated_at
UNIQUE (document_id, schedule_rule_id, due_date_snapshot)
```

Before send, runtime rechecks active outstanding balance, paid/cancelled state, hold, manual stop, and applicable Company/Customer/Invoice controls. `policy_revision_or_hash` identifies the resolved rule without copying the entire policy into the invoice.

### Relationships

- AR Document 1:N Reminder Occurrences.
- Reminder Schedule Rule 1:N Occurrences.
- Occurrence 0..1 Delivery Request for an actual email send.
- Customer/Invoice overrides influence planning/evaluation but are not copied as new Company policy rows.

### Why do we need this table?

1. It prevents the same scheduled reminder from being sent twice.
2. Users need to know which reminders were planned, sent, skipped, or failed.
3. A policy change must not erase or recreate old occurrences silently.
4. Skip reason explains paid, cancelled, hold, manual stop, or zero-balance outcomes.
5. Recipient/template and delivery linkage preserve what happened.
6. Collections reporting needs occurrence history independent of current policy.

### What happens if we remove this table?

The scheduler would have no durable idempotency or history. It could resend old steps after restart/policy change, and users could not explain why a reminder did or did not send.

### Current decision

Propose runtime occurrences. Detailed override merge/replace, time-zone, recurrence, retry, and recipient rules remain **REVIEW** before automated reminders are enabled.

### Flow

Resolve Company/Customer/Invoice controls → plan occurrence → recheck balance/stops → create delivery request or record skip → retain outcome.

# 19. Shared Audit Table

## `audit_events`

**Status:** ADD

**Owner:** Core / Shared Audit

**Used in flow:** Customer Onboarding / Sales Order / Billing / Approval / Delivery / Receipt / Collections / Administration

### What data is stored

Append-only shared action and change evidence emitted by all modules. Subject references are intentionally generic evidence references, while each business table remains the authoritative source for its typed state and values.

### Important columns

```text
id UUID PK
tenant_id UUID FK -> tenants
company_id UUID nullable FK -> companies
event_type
subject_type
subject_id UUID
subject_revision_no nullable
actor_user_id nullable
actor_role_snapshot nullable
occurred_at
reason nullable
correlation_id nullable
request_id nullable
before_values nullable                 -- bounded JSONB change evidence
after_values nullable                  -- bounded JSONB change evidence
metadata nullable                      -- bounded JSONB evidence, not business state
```

JSONB here is non-authoritative audit evidence for variable field diffs and technical context. It is not a universal settings table or a substitute for typed Customer, SO, document, receipt, approval, allocation, artifact, delivery, or reminder data.

### Relationships

- Tenant 1:N Audit Events; Company 1:N when an action has Company context.
- `subject_type` + `subject_id` references a business record as evidence; polymorphic DB FKs are not claimed.
- Approval submissions/decisions and other business history stay in their typed tables and emit corresponding events.

### Why do we need this table?

1. Mandatory actions such as approval, allocation, transfer, delivery failure, and historical override need one searchable audit stream.
2. Actor, role, time, reason, and correlation data must survive current-state changes.
3. Field-change evidence can show before/after values without module-specific audit tables.
4. Cross-module investigations need consistent Tenant/Company/event metadata.
5. Restricted-period exceptions require complete audit evidence in addition to typed decision/document fields.
6. One shared table avoids duplicate `customer_audit`, `invoice_audit`, `payment_audit`, and `sales_order_audit` structures.

### What happens if we remove this table?

Each module would need a duplicate audit table or rely only on application logs, which are not durable business evidence. Typed approval and transfer tables alone would not cover configuration changes, failed sends, unauthorized attempts, or other required events.

### Current decision

Propose one shared append-only audit table because the current `database.md` has no physical shared audit table despite requiring audit behavior. Events include `CUSTOMER_APPROVED`, `SALES_ORDER_APPROVED`, `INVOICE_SUBMITTED`, `INVOICE_APPROVED`, `INVOICE_RETURNED`, `INVOICE_REJECTED`, `HISTORICAL_EDIT_OVERRIDE`, `PI_CONVERTED_TO_TI`, `PAYMENT_ALLOCATED`, `PAYMENT_REALLOCATED`, `REMINDER_SENT`, and `EMAIL_FAILED`. Do not create module-specific audit tables.

### Flow

Business action/change → commit typed state and audit event atomically where applicable → query/export evidence by Tenant/Company/subject/correlation.

# 20. Reviewed Tables Not Included in the Current Candidate Set

## `customer_location_versions`

**Status:** DEFER

**Owner:** AR Customer

**Used in flow:** Customer Onboarding / Historical Address Review

### What data is stored

This legacy candidate would retain effective-dated versions of a Customer Location. Current requirements need current selectable locations and finalized invoice address snapshots, but do not confirm backdated customer-address resolution.

### Important columns

```text
id UUID PK
customer_location_id UUID FK -> customer_locations
valid_from
valid_to nullable
address_* fields
change_reason
```

### Relationships

- Customer Location 1:N versions only if later enabled.
- Finalized AR Documents already hold their selected address snapshots independently.

### Why do we need this table?

1. It would answer what the Customer master address was on an arbitrary past date.
2. It could support backdated document preparation from effective address history.
3. It would retain location changes outside invoice history.
4. Multiple versions have a lifecycle distinct from the stable Location ID.
5. It becomes justified only when those historical queries are a current requirement.

### What happens if we remove this table?

Current addresses and finalized document truth remain safe. The lost capability is backdated reconstruction of the mutable Customer master itself, which is not currently confirmed.

### Current decision

Defer. Do not over-version Customer locations until a requirement beyond finalized-document snapshots is approved.

### Flow

Future Location change → effective version history → backdated selection; absent from current MVP flow.

## `industries`

**Status:** DEFER

**Owner:** AR Customer

**Used in flow:** Customer Onboarding / Reporting

### What data is stored

This legacy candidate would define reusable Customer industry classifications. No current onboarding, Billing, tax, approval, receipt, or collections rule requires an Industry FK.

### Important columns

```text
id UUID PK
code
name
status
```

### Relationships

- Potential Industry 1:N Customers; no current FK is proposed.

### Why do we need this table?

1. It could support customer segmentation.
2. It could provide consistent industry labels.
3. It could filter management reports.
4. It could support future risk/commercial analysis.
5. None of those uses is required by the current transaction flows.

### What happens if we remove this table?

No current AR lifecycle or statutory evidence is lost. It can be added later with a nullable Customer FK if an approved report or business rule needs it.

### Current decision

Defer; the legacy list alone is not a business requirement.

### Flow

Future Customer classification → Reporting; not used in current MVP.

## `sales_order_milestones`

**Status:** DEFER

**Owner:** AR Commercial

**Used in flow:** Sales Order / Billing Generation

### What data is stored

A separate milestone table could hold named completion/billing milestones. The current product confirms milestone billing as a concept but does not freeze milestone evidence, completion, percentage, or generation rules.

### Important columns

```text
id UUID PK
sales_order_id UUID FK -> sales_orders
name
planned_date nullable
percentage_or_amount
completion_status
completed_at nullable
```

### Relationships

- Potential Sales Order 1:N Milestones.
- If milestones are only billing schedule rows, this table should merge into `sales_order_billing_schedules` rather than duplicate them.

### Why do we need this table?

1. A deal may have several named commercial milestones.
2. Completion can have a lifecycle separate from planned billing date.
3. Evidence/approval may be required before draft generation.
4. Several invoices might relate to one milestone.
5. These needs are not yet confirmed for the enabled MVP.

### What happens if we remove this table?

Manual billing from an approved Sales Order still works. If later milestones are only dated billing obligations, they can be schedule rows; a separate table is needed only for an independently managed completion lifecycle.

### Current decision

Defer pending the recurring/milestone specification; do not implement alongside the schedule candidate without a distinct requirement.

### Flow

Future approved milestone → completion evidence → billing schedule/generation; absent from current MVP.

## `receivables`

**Status:** REMOVE

**Owner:** AR Receipts

**Used in flow:** Receivables / Collections / Reporting

### What data is stored

A separate mutable receivable row would repeat document balance/state already determined by finalized AR Documents, typed document relations, active cash allocations, and active non-cash settlement adjustments. No independent receivable instrument or lifecycle has been identified.

### Important columns

```text
No physical table proposed.
Derived position = eligible finalized CUSTOMER_SALE document effect
                 - active applied cash
                 - active non-cash settlement
                 + approved CN/DN/document relation effects
```

### Relationships

- Receivable views/read models derive only eligible `CUSTOMER_SALE` effects from `ar_documents`, `ar_document_relations`, `payment_allocations`, and `settlement_adjustments`; `INTER_UNIT` documents are excluded.
- A performance projection/materialized view may be added later with rebuild/reconciliation rules, but it is not another authority.

### Why do we need this table?

1. We would need it only if a receivable had an independent identity apart from a document.
2. We would need it for a true subledger event model with separately posted entries.
3. We might need a read projection for proven reporting performance.
4. We might need an independently controlled hold/dispute lifecycle not suitable on the document.
5. None of those requirements currently justifies a second mutable balance authority.

### What happens if we remove this table?

No source data is lost. Outstanding, paid, partial, overdue, and hold views derive from the document and settlement records; the design avoids balance drift across duplicate tables.

### Current decision

Remove as a current physical source table. If `outstanding_amount` is later cached on `ar_documents` or a projection, label it derived, update it atomically, and provide reconciliation/rebuild behavior.

### Flow

Finalized settleable document + active allocations/adjustments/relations → derived receivable position → collections/reporting.

## `report_runs`

**Status:** DEFER

**Owner:** Reporting

**Used in flow:** Management Reporting / Export

### What data is stored

This legacy candidate would record asynchronous report/export requests and generated artifacts. The current database exercise does not define a report catalogue, long-running export requirement, or report artifact lifecycle.

### Important columns

```text
id UUID PK
tenant_id UUID FK -> tenants
report_type
parameters
requested_by, requested_at
status
artifact_storage_key nullable
```

### Relationships

- Potential Tenant/User 1:N Report Runs.
- It should consume AR read data without becoming an AR transaction source.

### Why do we need this table?

1. Long-running exports may need durable job state.
2. Users may need to download a completed artifact later.
3. Retry/failure history may be operationally useful.
4. Report parameters may need audit evidence.
5. No current specified report requires this persistence.

### What happens if we remove this table?

Synchronous/current reports remain possible. Only durable asynchronous report jobs/artifacts are unavailable until a reporting specification justifies them.

### Current decision

Defer to the Reporting/Analytics design.

### Flow

Future report request → async generation → stored artifact; outside current AR transaction MVP.

## `report_run_exchange_rates`

**Status:** DEFER

**Owner:** Reporting

**Used in flow:** Management Reporting / Currency Conversion

### What data is stored

This legacy candidate would pin exchange rates used by one report run. It has no lifecycle without `report_runs`, and current reports can query existing `exchange_rates` under the eventual reporting FX policy.

### Important columns

```text
id UUID PK
report_run_id UUID FK -> report_runs
exchange_rate_id UUID FK -> exchange_rates
rate_used
purpose
```

### Relationships

- Potential Report Run 1:N pinned Exchange Rates.
- References existing shared `exchange_rates`; it never replaces them.

### Why do we need this table?

1. A retained report artifact may need reproducible conversion evidence.
2. One report could use several currency pairs/dates.
3. It could explain later differences after rate corrections.
4. It belongs to report execution, not Billing or Company Configuration.
5. It is unnecessary until durable report runs are approved.

### What happens if we remove this table?

Transaction documents still retain their own actual rates, and current reporting can use existing FX references. Only exact reproduction of a separately retained converted report run is deferred.

### Current decision

Defer together with `report_runs`.

### Flow

Future report run → resolve reporting rates → pin used rates → reproduce artifact.

## `uom_master`

**Status:** DEFER

**Owner:** Core / Shared Reference

**Used in flow:** Catalogue / Sales Order / Billing

### What data is stored

A reusable Unit of Measure vocabulary. The reviewed Company Configuration schema currently stores UOM directly on Service Type/SKU, and downstream lines snapshot that value.

### Important columns

```text
id UUID PK
code
name
precision nullable
status
```

### Relationships

- Potential UOM 1:N Service Types, SKUs, SO Lines, and AR Lines.
- Adding those FKs would change already-reviewed catalogue columns and therefore needs a separate requirement/review.

### Why do we need this table?

1. It could enforce consistent UOM codes.
2. It could centralize display labels and precision.
3. It could support statutory/export vocabularies.
4. It could validate catalogue and transaction entry.
5. Current requirements do not state that these values must be administrator-maintained rows.

### What happens if we remove this table?

Current catalogue UOM and transaction snapshots remain usable as controlled text. The lost benefit is database-FK validation against a master list.

### Current decision

Defer; do not silently alter the reviewed `service_types.uom` and `skus.uom` design.

### Flow

Future UOM reference → catalogue selection → SO/AR snapshot; current flow uses approved text values.

## `uom_conversion`

**Status:** DEFER

**Owner:** Core / Shared Reference

**Used in flow:** Goods/Service Quantity Conversion

### What data is stored

Conversion factors between Units of Measure. No current AR requirement asks to order in one UOM, invoice in another, convert inventory, or manage effective-dated conversion factors.

### Important columns

```text
id UUID PK
from_uom_id UUID FK -> uom_master
to_uom_id UUID FK -> uom_master
conversion_factor
valid_from nullable
valid_to nullable
```

### Relationships

- Potential UOM N:M UOM through conversion rows.
- Depends on the deferred `uom_master`.

### Why do we need this table?

1. It would support billing in a different unit from ordering.
2. It could normalize quantities for analytics.
3. It could support pack/case/unit conversions for goods.
4. It requires precision and effective-date rules.
5. None of these is part of the current non-WMS AR scope.

### What happens if we remove this table?

Current SO and invoice lines continue using the approved UOM and quantity directly. Cross-UOM conversion remains unavailable until explicitly designed.

### Current decision

Defer; do not introduce inventory-style conversion behavior into the AR MVP.

### Flow

Future catalogue conversion → order quantity conversion → billing; absent from current flow.

## `countries`

**Status:** SUPERSEDED — see current KEEP section 2A

**Owner:** Core / Shared Reference

**Used in flow:** Company/Customer Address Validation

### What data is stored

A database-maintained country reference. The reviewed configuration design currently uses `country_code`, and no admin-managed Country lifecycle is required by this downstream design.

### Important columns

```text
code PK
name
status
```

### Relationships

- Potential 1:N relationship to Company/Customer addresses by code.
- No new FK is introduced into the reviewed Company Configuration tables here.

### Why do we need this table?

1. It could provide consistent country names.
2. It could validate ISO-style codes.
3. It could populate address pickers.
4. It could carry locale metadata.
5. None requires an ERP-managed table instead of a controlled application reference in current scope.

### What happens if we remove this table?

Country codes remain stored on masters and snapshots. Only database-managed label/reference maintenance is absent.

### Current decision

Superseded by the approved global `core.countries` contract in current section 2A. Existing Entity Type and Company Country FKs remain a separate post-loader retrofit.

### Flow

Future shared reference → address selection/validation; current flow stores controlled country codes.

## `states`

**Status:** SUPERSEDED — replaced by current KEEP `country_subdivisions` section 2B

**Owner:** Core / Shared Reference

**Used in flow:** GST Registration / Address / Place of Supply

### What data is stored

A database-maintained State/Province reference. Current tables carry state/place-of-supply codes, while GST tax derivation uses controlled codes and product logic.

### Important columns

```text
id UUID PK
country_code
state_code
name
status
UNIQUE (country_code, state_code)
```

### Relationships

- Potential Country 1:N States.
- Potential 1:N relationship to GST registrations, locations, and document place-of-supply values.

### Why do we need this table?

1. It could validate state codes and names.
2. It could populate GST/location address choices.
3. It could support non-India provinces later.
4. It could centralize place-of-supply labels.
5. Current scope does not require administrators to maintain this reference in the database.

### What happens if we remove this table?

State codes and finalized snapshots remain present. Application-controlled reference validation can support the MVP without changing the approved schema.

### Current decision

Superseded by the jurisdiction-neutral `core.country_subdivisions` contract in current section 2B. No separate State-only master is introduced.

### Flow

Future state reference → GST/address/place-of-supply validation; current flow uses controlled codes.

# 21. Cross-Table Rules and Unresolved Decisions

The following rules apply across the downstream candidate tables:

1. Every FK relationship must stay inside the same Tenant. A transaction's `company_id`, selected Company-owned masters, Customer scope, and child rows must be validated together; UUID equality alone is insufficient.
2. Customer PAN/GSTIN duplicate detection is a hard-block direction, but the uniqueness scope across Tenant, Company, drafts, and establishments remains **TBD / REVIEW**. Do not add a global unique index until that scope is approved.
3. A submitted Customer, Sales Order, or AR Document revision cannot be materially changed in place. Return/edit creates a new revision and a new submission; decisions always point to the reviewed submission.
4. Final AR Document snapshots are structured header/line columns. Master FKs explain origin but cannot be used to regenerate a historical finalized document from current values.
5. Final number allocation, document finalization, approved-revision verification, and mandatory audit/delivery intent creation occur in one guarded database transaction. PDF rendering and provider delivery occur asynchronously afterward.
6. LUT validation is required before finalization for the current without-payment routes `EXPWOP` and `SEZWOP`, using the selected seller GST registration and applicable fiscal period. Missing a required valid LUT blocks finalization. `EXPWP` and `SEZWP` are not blocked solely for missing LUT.
7. `tcs_check_required` requires an explicit invoice-line TCS applicability decision; it never means “charge TCS automatically.” Threshold, cumulative, exemption, and advanced calculation rules remain later Billing/Tax decisions.
8. Current TDS settlement is user-section driven: select an applicable section/code, resolve the configured rate, calculate/record TDS, and allow cash plus TDS to settle the receivable. Threshold/cumulative automation is deferred.
9. Receipt cash conservation is enforced from `receipts.cash_amount` and active `payment_allocations`. Non-cash adjustments never increase Receipt cash.
10. Outstanding receivable is derived from eligible finalized document effects and active settlement/relationship data. PI/TI/CN/DN balance effects must be frozen before the corresponding route is enabled.
11. PI-to-TI conversion keeps the document relation, original allocation reversal, replacement allocation, and explicit transfer link. No history is deleted or rewritten.
12. Normal users cannot edit/post into a locked or restricted historical period. An authorized Finance/Admin/Authority exception is allowed only when Company policy permits, with mandatory reason and complete typed/audit evidence. Full Period Closing/Lock tables are outside this AR MVP.
13. GSTR-1 is an auditable batch identified by GST Registration + Return Period + Return Type. The hard edit rule is: **Invoice included in a FILED GSTR-1 return / filing batch.** Membership in `DRAFT` does not permanently lock a document; filed membership is immutable.
14. Successful e-invoice/IRN generation independently hard-locks the issued document. Corrections use the applicable cancellation, amendment, CN, or DN process.
15. `CUSTOMER_SALE` and `INTER_UNIT` are explicit transaction classifications. Inter-Unit documents use same-Company source/destination GST Registration and Location, never model the destination as a Customer, and never create normal AR outstanding.
16. Ship-To is discriminated as `CUSTOMER_LOCATION` or `COMPANY_LOCATION`; only its matching FK is populated and the final document snapshots the address.
17. Catalogue Base GST Nature resolves from `tax_treatments` as one of `TAXABLE`, `NIL_RATED`, `EXEMPT`, or `NON_GST`; it is not a numeric Tax Rate Type or the final transaction GST outcome. `ZERO_RATED` is transaction context and not a catalogue nature.
18. Reminder send-time checks always re-evaluate positive outstanding balance, paid/cancelled status, hold, manual stop, and current applicable control. Planning an occurrence does not guarantee sending.
19. The shared audit stream supplements, rather than replaces, typed approval, relation, allocation, transfer, filing, e-invoice, artifact, delivery, and reminder history.
20. Effective `revenue_gl_mappings` use the invoice date, already-resolved Supply Type, and line HSN/SAC. A specific Supply Type + HSN/SAC mapping wins over a general Supply-Type-only mapping.
21. If no effective Revenue GL Mapping matches, or more than one matches at the same specificity, configuration validation/finalization blocks. It never chooses a GL Account by name or arbitrary row order.
22. Applicable CGST, SGST, and IGST COMPONENT identities resolve through effective `tax_gl_account_mappings` using `tax_statutory_code_id`. Revenue and tax accounts are not normally selected by the invoice user.
23. Finalized AR Documents/Lines retain the resolved receivable, revenue, and applicable tax GL Account IDs. Later mapping or hierarchy changes do not reclassify historical transactions.
24. HSN/SAC is a statutory classification and is not permanently equal to one GL Account. Supply Type provides transaction context; the optional HSN/SAC condition refines a mapping.
25. `tax_types` identifies the broad family; `company_hsn_sac_codes` identifies Company-configured item classifications; `tax_rates` stores ordinary numeric rates; `company_hsn_sac_tax_rates` stores effective eligibility; `tax_treatments` supplies controlled Base GST Nature references for catalogue use; and `tax_statutory_codes`/`tax_statutory_code_rates` store COMPONENT/SECTION identities and their effective section-rate cases. These concepts must not be merged.
26. Service Type must reference a Company SAC and SKU must reference a Company HSN. `TAXABLE` and `NIL_RATED` require direct `selected_tax_rate_id` eligibility through an active effective `company_hsn_sac_tax_rates` row for the transaction/setup date; `NIL_RATED` additionally requires exactly 0%. `EXEMPT` and `NON_GST` require NULL.
27. HSN/SAC and Base GST Nature never determine the complete GST outcome or CGST versus SGST versus IGST by themselves. Future Billing considers Supply Type, seller GST context, Place of Supply, transaction date, and LUT context; the finalized line snapshots code/description as required, Base GST Nature, zero-rated outcome where applicable, actual rate, components and amounts.
28. `gl_accounts` stores stable posting-account identity only. Groups, parents, hierarchy placements, classifications, and balances do not belong on that table.
29. Account Group parentage and GL hierarchy placement are effective-dated,
same-Company, same-hierarchy, non-cyclic where parentage applies, and
non-overlapping. A GL placement row with a null Group is intentional root
placement; absence of a row is unplaced. PostgreSQL exclusion constraints plus
backend validation enforce the applicable rules.
30. Hierarchy changes do not change accounting amounts or resolved GL IDs. A future historical reclassification requires an explicit correction entry rather than master-data mutation.
31. One default Receivable GL resolves through `company_accounting_settings`; eligible Customer-Sale documents snapshot it. No separate receivable-mapping table exists in current scope.
32. Bank-to-GL association uses `company_bank_accounts.gl_account_id`; no separate bank mapping table exists.
33. A used GL is never converted into a Group. Splits/merges create or select new target GL Accounts for future mappings while retaining old account IDs for history.
34. Accounting master/mapping FKs use UUIDs and `ON DELETE RESTRICT`; account codes/names are business-facing values and never relational keys.

Open decisions before downstream schema freeze are:

- Customer Tenant-wide versus Company-specific identity and PAN/GSTIN uniqueness boundary.
- FX source, date, override, and Receipt cross-currency rules.
- Finance edit/self-approval behavior and invalidation when material context changes.
- PI/TI/CN/DN balance, conversion, correction, cancellation, and settlement eligibility rules.
- Customer delivery/reminder override semantics.
- Whether automated recurring/milestone generation is part of the enabled MVP.
- Whether current goods Billing requires one simple dispatch block.
- Inter-Unit clearing/balancing account treatment. Approved Revenue and Tax GL mapping applies where relevant, but normal Customer AR remains excluded and the clearing design is not finalized.
- Full Accounting posting journals, posting status/date, idempotency, reversals, reconciliation, and period-close integration.
- Whether optional starter CoA templates require persistent template tables later; no template engine is included now.
- Accounting classification design, including whether `account_types` returns and how ASSET/LIABILITY/EQUITY/INCOME/EXPENSE semantics are represented.
- Management hierarchy product behavior beyond the current schema extension point.
- CoA import/export file format, validation, matching, idempotency, and conflict handling.
- Historical accounting correction/reclassification entries; current masters never rewrite old accounting.
- Any future receivable mapping beyond one Company default.

# Database Design Change Log

| Date | Flow | Old table / design | Action | New table / design | Reason |
|---|---|---|---|---|---|
| 2026-09-29 | Catalogue Base GST Nature | `service_types.tax_treatment_id` / `skus.tax_treatment_id` implied a complete transaction treatment and selected GST rates were mandatory for every item | SUPERSEDE / IMPLEMENT | `base_tax_treatment_id` on Service Type/SKU plus conditional nullable `selected_tax_rate_id` | Catalogue items store only TAXABLE/NIL_RATED/EXEMPT/NON_GST Base GST Nature. TAXABLE requires an eligible rate, NIL_RATED requires eligible 0%, and EXEMPT/NON_GST require NULL. ZERO_RATED remains a transaction-context result for future Billing resolution, not a catalogue nature |
| 2026-09-22 | Company Billing Document Template and Branding | Company/document-type template rows and required `show_*` values permitted multiple current selections per Company; branding-current cardinality was unresolved | SUPERSEDE / IMPLEMENT | Company-wide versioned `company_document_templates` selection plus immutable versioned `company_document_branding` | Migration 0027 makes current selection independent of PI/TI/CN/DN, enforces at most one ACTIVE selection and branding row per Company, preserves/retire existing history without guessing a winner, retains legacy `document_type` and `show_*` columns only as nullable non-governing data, and keeps same-Company stored-file/branding integrity |
| 2026-09-22 | Company Location Address History and Lifecycle | Approved version concept was not implemented; current address PATCH was destructive and inactive Locations remained mutable in assignment paths | FINALIZE / IMPLEMENT | `core.company_location_versions`; atomic current projection/version updates; terminal Location inactivation | Migration 0026 uses the existing Country/Subdivision representation, restrictive FKs, inclusive non-overlapping DATE ranges, one open version, deterministic creation-date backfill, and stable Location identity. MVP edits are immediately effective; future/backdated workflows remain excluded, and inactive Locations remain readable but cannot be reactivated or mutated |
| 2026-09-21 | GL Account Hierarchy Placement / Group Inactivation | Root GL placement and mapping-table physical details were open; Group inactivation behavior with current/future children was unresolved | FREEZE BUSINESS AND PHYSICAL CONTRACT | Nullable-Group `core.gl_account_group_mappings` contract for a future Migration 0018; transactional Group-inactivation guard | Distinguish unplaced, Group-placed, and intentionally root-placed GLs; preserve inclusive effective history and same-scope integrity; prohibit overlap and automatic restructuring while keeping Account Determination separate |
| 2026-09-21 | Accounting Hierarchy History / Future Account Determination | Candidate Group relationship represented root with a null-parent row; future account selection direction was not separated from current AR mappings | FREEZE BUSINESS CONTRACT / DEFER PHYSICAL DESIGN | Absence-of-parent-row root semantics; zero-or-one effective Accounting parent and GL placement; controlled future Account Determination direction | Preserve effective structure and stable posting identity without freezing relationship columns or a rule engine. Current Revenue, Tax, default Receivable, and Bank GL contracts remain unchanged; persistence, resolver, restatement, reclassification, and override behavior require later approval |
| 2026-09-19 | Core Company Bank Account Foundation | Bank Account physical ownership remained Boundary TBD and no persistence existed | RESOLVE / CONFIRM KEEP / IMPLEMENT | `core.company_bank_accounts` | Migration 0013 establishes the reusable Company-owned Core/Shared Bank Account identity with one Currency per account, optional same-Company GL Account, active Billing-default uniqueness per Company/Currency, restrictive history, and no account-number uniqueness. AR selection APIs, routing, posting, duplicate policy, account-type vocabulary, identifier-format rules, and data-masking policy remain outside this slice |
| 2026-09-19 | Company Cost Center Configuration Foundation | Approved Location Cost Center, Business Segment, Cost Center Team bucket, actual Team, and settings contracts were not yet implemented; catalogue and Location relationships were deferred | CONFIRM KEEP / IMPLEMENT | `core.cost_center_locations`, `core.cost_center_business_segments`, `core.cost_center_teams`, `core.teams`, `core.company_cost_center_settings`; nullable direct links from AR catalogue leaves and Company Locations | Migration 0010 implements only the three approved reporting bases and their direct same-Company relationships. It adds Tenant-safe configuration/create APIs without a generic Cost Center or dimension framework. IAM-backed `team_memberships`, assignment APIs, lifecycle transitions, authentication/authorization, and downstream posting/reporting remain deferred |
| 2026-09-19 | Cost Center Team Reporting | `cost_center_teams` combined the actual Company Team and reporting bucket, and `team_memberships` linked users directly to that combined identity | SUPERSEDE / ADD KEEP | `cost_center_teams` reporting buckets; separate actual `teams` with nullable direct `cost_center_team_id`; `team_memberships.team_id` | One Team-based reporting bucket may group multiple operational Teams while each actual Team belongs to zero or one bucket. User/IAM membership history belongs to actual Teams. Same-Company enforcement is required, complete coverage remains optional, and no M:N or generic Cost Center mapping is introduced |
| 2026-09-19 | Tax Reference and Company Catalogue Foundation | Catalogue implementation was blocked by absent mandatory tax references; Country FKs, lifecycle, setup-date behavior, and Business Segment timing were unresolved | UPDATE / CONFIRM KEEP / IMPLEMENT | `core.tax_types`, `core.company_hsn_sac_codes`, `core.tax_rates`, `core.company_hsn_sac_tax_rates`, `core.tax_treatments`; AR Service and Goods catalogue tables | Migrations 008 and 009 sequence controlled tax prerequisites before Company-owned catalogues. New catalogue records are ACTIVE, references must be active, setup does not evaluate rate applicability against today's date, same-Company hierarchy is protected, and Business Segment FKs remain deferred without placeholders |
| 2026-09-18 | Company GST Registration Foundation | GST lifecycle, physical State/UT reference, draft Registration-Type nullability, GSTIN validation boundary, and Location integrity were unresolved | UPDATE / CONFIRM KEEP / IMPLEMENT | `core.gst_registration_types`, `core.company_gst_registrations`, `country_subdivisions.gst_state_code`, and nullable `company_locations.gst_registration_id` | Migration 007 adds country-scoped optional GST State codes, platform Registration-Type structure without seed values, DRAFT-first GST registrations with global GSTIN uniqueness and structural validation, and a composite Location FK enforcing same-Company/same-Subdivision mapping. Service creation requires an India Company, active provisioned Indian Subdivision, and matching GSTIN prefix; checksum, activation, defaults, LUT, Billing, and tax calculation remain deferred |
| 2026-09-18 | Company Fiscal Settings / Financial Years | Typed pattern, universally valid recurring date, lifecycle values, normal generation API, and physical overlap enforcement were unresolved | UPDATE / CONFIRM KEEP / IMPLEMENT | `core.company_fiscal_settings` and `core.financial_years` | Migration 006 stores `APR_MAR`/`JAN_DEC`/`CUSTOM` with explicit recurring month/day, rejects dates unavailable in non-leap years, retains transition representation including one-day ranges, adds `DRAFT`/`OPEN`/`CLOSED`, and prevents same-Company overlap with a PostgreSQL exclusion constraint. Normal APIs configure the pattern and generate DRAFT annual instances without arbitrary dates |
| 2026-09-18 | Core Company Location Foundation | Company Location Country/Subdivision representation remained OPEN and the wider KEEP contract depended on unimplemented GST and Cost Center modules | UPDATE / CONFIRM KEEP / IMPLEMENT | `core.company_locations` plus supporting Country/Subdivision composite uniqueness | Migration 005 implements required Company ownership, current address fields, fixed multi-purpose flags, required purpose, ACTIVE/INACTIVE lifecycle, mandatory Country, optional compatible Subdivision, and race-safe active Registered Office uniqueness. GST/default, Location Cost Center, address-version, activation, and replacement workflows remain outside this slice |
| 2026-09-18 | Core Geographic Reference Masters | Country and State masters were deferred while existing tables stored controlled jurisdiction codes directly | UPDATE / CONFIRM KEEP / IMPLEMENT | `core.countries` and `core.country_subdivisions` | Migration 004 adds global platform-managed Country and ISO-compatible first-level subdivision masters with controlled lifecycle, timestamps, integrity checks, restrictive Country ownership, and only the required lookup index. It adds no seed data, existing Entity Type/Company Country FKs, Company subdivision relationship, or City/District/postal/address hierarchy |
| 2026-09-18 | Core Company Identity Foundation | Currency provisioning details, Organisation code, Company Code scope/generation, Draft nullability, and same-Tenant Organisation enforcement were not fully frozen | UPDATE / CONFIRM KEEP / IMPLEMENT | `core.currencies`, `core.organisations`, `core.company_code_seq`, `core.next_company_code()`, and `core.companies` | One Migration 003 establishes the global Currency reference without seed data, code-free Tenant-owned Organisation grouping, database-enforced same-Tenant Company grouping, global concurrency-safe `COM` codes, explicit Draft lifecycle/nullability, restrictive FKs, and focused constraints/indexes. Activation services, profile history, Countries, Locations, fiscal/AR configuration, RLS, and generic frameworks remain outside this slice |
| 2026-09-18 | Entity Type Master | Mandatory jurisdiction representation, UUID generation, code constraints, name uniqueness, status storage, and migration scope were not frozen | UPDATE / CONFIRM KEEP / IMPLEMENT | `core.entity_types` | PostgreSQL generates UUIDs; jurisdiction is stored directly as an uppercase two-letter `country_code` without a Countries FK; canonical code is jurisdiction-unique and format-constrained; name is required but not unique; status uses `VARCHAR(20)` plus CHECK with no default. Countries, timestamps, seed data, extra indexes, delete automation, RLS, Company, and identifier rules remain outside Migration 002 |
| 2026-09-18 | Tenant Master | UUID, code allocation, status storage, timestamp defaults, deletion, and first-migration isolation details were not frozen | UPDATE / CONFIRM KEEP / IMPLEMENT | `core.tenants`, `core.tenant_code_seq`, and `core.next_tenant_code()` | PostgreSQL generates UUIDs and concurrency-safe sequential `TEN` codes; status uses `VARCHAR(20)` plus CHECK with no default; timestamps use insert defaults without an update trigger; blank checks, PK, and unique code are the only initial constraints/indexes. Hard-delete workflow, cascade, RLS, authentication, and memberships remain excluded |
| 2026-09-17 | AR Compliance / Numbering / Payment Terms / Output Configuration | Tables 35–40 had incomplete physical definitions, stale blanket LUT wording, raw branding references, and unresolved numbering/template selection details | UPDATE / CONFIRM KEEP | Refined `company_luts`, `document_sequences`, `document_sequence_conditions`, `payment_terms`, `company_document_branding`, and `company_document_templates` | Exact PostgreSQL datatypes, nullability, defaults, keys, checks, history/lifecycle and same-Company invariants are documented. LUT is GST Registration + FY specific and required for current without-payment routes `EXPWOP`/`SEZWOP`; LUT upload remains outside MVP. Numbering uses independent atomic counters and controlled conditions without a generic rules engine; unresolved first-release condition/operator/priority semantics remain OPEN. Branding uses typed `stored_files` FKs, templates remain versioned server-side configuration, and final PDFs remain separate immutable artifacts |
| 2026-09-17 | Shared File / Object Metadata | Domain-specific raw storage keys and branding references existed without one approved provider-neutral metadata identity | ADD / KEEP | `stored_files` | One Company-scoped UUID identity stores immutable object key, content hash, MIME type, size and optional original filename while bytes remain in Cloudflare R2 behind `ObjectStorage`. Domain tables later use typed FKs; signed URLs/provider fields and a generic attachment framework are excluded. Final artifact retention is preserved while detailed deletion/retention policy remains OPEN |
| 2026-09-17 | Cost Center / Management Reporting | Five KEEP tables had compact physical definitions; current requirements still mentioned a fourth Custom Cost Center basis and category-level Segment assignment | UPDATE / CONFIRM KEEP | Refined `cost_center_locations`, `cost_center_business_segments`, `cost_center_teams`, `team_memberships`, and `company_cost_center_settings` for the three current bases | Exact PostgreSQL datatypes, nullability, defaults, keys, status checks, Company-scoped uniqueness, same-Company invariants, direct item/Location relationships, configuration-driven enablement, and effective Team history are documented. The physical IAM subject reference and exact one-active-membership enforcement remain OPEN; broader custom dimensions remain DEFERRED, and no generic accounting-dimension engine is introduced |
| 2026-09-17 | Tax Reference / Company HSN-SAC Configuration | Eight tax-reference/configuration tables had incomplete physical definitions; GST Registration Type was separated from Company GST Registration; ordinary item rates and statutory SECTION/case rates needed a sharper boundary | UPDATE / CONFIRM KEEP / REORDER | Refined `gst_registration_types`, `tax_types`, `company_hsn_sac_codes`, `tax_rates`, `company_hsn_sac_tax_rates`, `tax_treatments`, `tax_statutory_codes`, and `tax_statutory_code_rates`; moved GST Registration Type beside Company GST Registration and renumbered current-state headings | Exact PostgreSQL datatypes, nullability, keys, checks, lifecycle, effective-date and non-overlap rules are frozen. `tax_rates` remains ordinary item/supply rates; statutory SECTION/case rates remain separate with no `tax_rate_id`. HSN/SAC stays India-first, foreign generalization is deferred, and no generic tax engine is introduced |
| 2026-09-17 | Bank Accounts / Exchange Rates / FX Policy | Bank/FX tables lacked frozen datatypes and constraints; Billing default-bank scope and `default_rate_type` semantics were incomplete; provisional `override_role` mixed policy with IAM | UPDATE / CONFIRM KEEP | Refined `company_bank_accounts`, `exchange_rates`, and `fx_policies`; added Admin/Billing UI references | Billing Bank default is per Company + Currency; nullable direct Bank-to-GL and same-Company validation remain. FX uses positive exact `NUMERIC(28,12)` directional CORPORATE/SPOT facts with valid, non-overlapping active periods. Policy default is an Exchange Rate Type preselection, Billing retains Corporate/Spot choice, User Fixed requires policy plus authorization and optional mandatory reason, and `override_role` is removed/deferred. Receipt/Reporting detail remains OPEN |
| 2026-09-17 | Currency Configuration | Currency, Reporting Currency, and AR Currency tables lacked frozen physical datatypes and constraints | UPDATE / CONFIRM KEEP | Refined `currencies`, `company_reporting_currencies`, and `company_ar_currencies` | Currency uses canonical uppercase `VARCHAR(3)` identity and explicit minor units. Additional Reporting Currency uses Company/Currency composite PK and excludes redundant Base Currency. Rich AR Currency retains UUID plus one-row-per-Company/Currency uniqueness, independent Billing/Receipt permissions, enabled-default checks, active-row usefulness, and one active default per operation. Base-Currency AR permission is explicit; Reporting and AR controls remain separate; FX rates/policies stay outside these tables |
| 2026-09-17 | Company Fiscal Pattern / Financial Years | Fiscal pattern and actual FY distinction lacked frozen columns/constraints; display code was described as optional; close/lock separation was brief | UPDATE / CONFIRM KEEP | Refined `company_fiscal_settings` and `financial_years` | Company has one recurring start-month/day pattern using `company_id` as PK/FK, without redundant end/current/close/lock fields. Actual FY dates are authoritative, same-Company ranges cannot overlap, Company-scoped display code is required/unique, transition intent is explicit, settings changes affect only future proposals, and creating the next FY never closes/locks the prior FY. Exact FY status values remain OPEN; accounting close/lock remains future Accounting scope |
| 2026-09-17 | Company Location / Address History | `company_locations` retained an unused nullable `location_code`; `company_location_versions` remained REVIEW with broad/unclear scope | UPDATE / CONFIRM KEEP | Refined `company_locations`; KEEP `company_location_versions` for address/jurisdiction only | UUID plus Location Name are sufficient current identities. Direct nullable GST and Cost Center relationships, same-Company ownership, State/UT compatibility, fixed multi-purpose flags, one active Registered Office, default-per-GSTIN preselection, historical inactivation, non-overlapping effective address periods, and independent finalized-document snapshots are retained. Full temporal GST/Cost Center/purpose configuration is excluded; physical Country/State references remain OPEN |
| 2026-09-17 | Company / GST Registration Identity | Company columns incompletely frozen; ambiguous `registered_name`; Company/GST history not separated | UPDATE / ADD REVIEW | Reviewed current `companies`; refined `company_gst_registrations`; `company_profile_versions` and `company_gst_registration_versions` REVIEW concepts | Direct PAN/CIN/LLPIN remain replaced. Company and GSTIN legal names have distinct current meanings and histories; GSTIN is globally unique, State/UT is mandatory, Registration Type is retained, finalized seller snapshots remain immutable, and no global default GSTIN is added. Open Company fields, physical jurisdiction references, GST status values, and full version columns are not guessed |
| 2026-09-17 | Company Legal Identifiers | Direct `companies.pan`, `companies.cin`, and `companies.llpin` columns | REPLACE / ADD | `company_identifier_types`, `company_identifiers`, and `entity_type_identifier_rules` | Generic jurisdiction-scoped identifiers avoid repeated Company schema changes. Platform controls types/rules; Company users provide values; one current value per type applies. Full statutory matrix, format/normalization, jurisdiction FK representation, and version/audit mechanics remain OPEN; import aliases remain DEFERRED |
| 2026-09-17 | Entity Type Reference | Compact legal-form table with nullable `country_code` and no frozen canonical identity rules | UPDATE / CONFIRM KEEP | Platform-managed Entity Type with stable UUID, mandatory jurisdiction, canonical stable machine code, separate display name, ACTIVE/INACTIVE lifecycle, and Company FK selection | Entity Type is controlled primary legal-form reference data, not Tenant-owned or Company free text. Code uniqueness is jurisdiction-scoped; exact jurisdiction representation, identifier-applicability rules, and complete India matrix remain OPEN, while import alias normalization is DEFERRED |
| 2026-09-17 | Organisation Architecture | Compact optional grouping definition without frozen constraints | UPDATE / CONFIRM KEEP | Optional Tenant-scoped grouping with mandatory Tenant FK, Tenant-scoped unique name, optional Tenant-scoped unique code, ACTIVE/INACTIVE lifecycle, and no configuration inheritance | Company remains directly Tenant-owned and is the legal/billing/tax/accounting boundary. Cross-Tenant Organisation assignment must be impossible; exact database enforcement will be finalized during the `companies` review |
| 2026-09-17 | Tenant Architecture | `tenants` had a nullable code and only a compact ownership description | UPDATE / CONFIRM KEEP | Small authoritative Tenant master with UUID identity, non-unique display name, required unique stable code, controlled lifecycle, timestamps, and direct Company ownership | Tenant is the SaaS ownership/isolation boundary rather than a legal Company. Code should preferably be system-generated; Company retains direct Tenant ownership. Tenant/User membership and audit attribution remain open under IAM and generic Audit design |
| 2026-09-17 | CoA Identity / Hierarchy | Hierarchy embedded through `gl_accounts.parent_account_id` and account/group conflation | REPLACE | `account_hierarchies`, `account_groups`, `account_group_relationships`, `gl_account_group_mappings` | GL Account remains the stable posting identity while effective-dated relationships preserve reorganizations and historical hierarchy |
| 2026-09-17 | CoA Hierarchy | One permanent accounting tree | EXTEND | Purpose-scoped hierarchies with `ACCOUNTING` now and `MANAGEMENT` later | The same GL Accounts can support a future Management reporting view without duplicating accounting identities |
| 2026-09-17 | GL Account | Type, parent, group/flag or balance could live on `gl_accounts` | UPDATE | Stable Company GL identity with name/code, validity and status only | Rename/code changes preserve ID; hierarchy and balances cannot mutate account identity or historical accounting |
| 2026-09-17 | Accounting Classification | `account_types` required in current AR CoA foundation | DEFER | Full Accounting classification design | ASSET/LIABILITY/EQUITY/INCOME/EXPENSE and mapping-eligibility semantics are not approved and must not be guessed |
| 2026-09-17 | Revenue Mapping | `revenue_account_mappings` + `revenue_mapping_supply_types` + `revenue_mapping_hsn_sac` | REPLACE / SIMPLIFY | Effective-dated `revenue_gl_mappings` | One row represents one business condition, retains specific-before-general resolution, prevents overlap, and removes unnecessary header/child structure |
| 2026-09-17 | Tax Statutory Identity | TDS/TCS-specific `statutory_sections` and free-text GST component code | RENAME / GENERALIZE | `tax_statutory_codes` with COMPONENT/SECTION | CGST/SGST/IGST are components, not sections; all statutory identities can be controlled without merging their calculation rules |
| 2026-09-17 | Tax Statutory Rates | `statutory_section_rates` | RENAME / GENERALIZE | `tax_statutory_code_rates` | Rate cases follow generalized statutory-code identity while ordinary GST item rates remain in `tax_rates` |
| 2026-09-17 | Tax GL Mapping | `tax_gl_account_mappings.tax_component_code` text | REPLACE | `tax_statutory_code_id` FK plus effective dates | Controlled statutory identity replaces free text and supports GST components plus approved TDS/TCS section mappings |
| 2026-09-17 | Receivable GL | No explicit current default or a possible separate mapping table | ADD / SIMPLIFY | `company_accounting_settings.default_receivable_gl_account_id` | Current scope needs one Company default; richer Domestic/Export/customer-category routing is deferred |
| 2026-09-17 | Bank GL | Separate bank mapping could be introduced | UPDATE | `company_bank_accounts.gl_account_id` | Direct same-Company FK is sufficient and avoids another table |
| 2026-09-17 | Accounting History | Current hierarchy/mapping could be used to reinterpret old documents | CLARIFY | Effective-dated structures plus finalized resolved GL Account IDs | Hierarchy and mapping changes affect future dates only; historical correction requires a future explicit reclassification/correction entry |
| 2026-09-17 | CoA Import/Export | Manual SQL/VPS maintenance risk | DEFER IMPLEMENTATION | Schema supports future Groups, GLs, relationships, and placements import/export | Company self-service is the intended direction; file/matching/idempotency rules remain OPEN and no implementation is added now |
| 2026-09-15 | Customer | No distinct external customer grouping | ADD | `customer_organisations` | Optional customer-group identity must remain distinct from the Tenant's internal `organisations`; exact business scope remains reviewable |
| 2026-09-15 | Customer | `clients` | RENAME | `customers` | Use consistent Customer language for the stable AR legal party; no data is split merely for naming |
| 2026-09-15 | Customer | `client_gst_registration` | RENAME | `customer_gst_registrations` | One Customer can have multiple or zero GST registrations |
| 2026-09-15 | Customer | `client_locations` | RENAME | `customer_locations` | Multiple selectable addresses have their own rows and invoice snapshots preserve history |
| 2026-09-15 | Customer | Separate customer GST/location mapping assumed | REMOVE | Nullable `customer_locations.gst_registration_id` proposal | Direct FK is sufficient for one registration to many locations and one current registration per location; revisit only for real M:N/history |
| 2026-09-15 | Customer | `client_contacts` | RENAME | `customer_contacts` | Contacts are stable Customer children independent of locations |
| 2026-09-15 | Customer | `client_roles` | RENAME / RESHAPE | `customer_contact_roles` | One Contact can perform multiple roles without duplicate people |
| 2026-09-15 | Customer | `client_documents` | RENAME | `customer_documents` | Preserve supporting-file metadata in object storage references |
| 2026-09-15 | Customer | `client_onboarding_requests` | RENAME / RESHAPE | `customer_approval_submissions` | Approval must target an immutable Customer revision |
| 2026-09-15 | Customer | `client_onboarding_actions` | RENAME / RESHAPE | `customer_approval_decisions` | Preserve human decision actor/time/reason against a submission |
| 2026-09-15 | Customer | `client_location_versions` | DEFER | `customer_location_versions` | Final documents snapshot addresses; backdated Customer-master address resolution is not confirmed |
| 2026-09-15 | Customer | `industries` | DEFER | No current table | No current onboarding, billing, tax, or reporting requirement needs an Industry FK |
| 2026-09-15 | Delivery | `client_delivery_settings` | RENAME / REVIEW | `customer_delivery_settings` | Customer override precedence is directionally required, but exact fields/inheritance are not frozen |
| 2026-09-15 | Collections | No explicit Customer reminder override row | ADD / REVIEW | `customer_reminder_settings` | Company → Customer → Invoice precedence exists; merge/replace semantics remain unresolved |
| 2026-09-15 | Sales Order | `sales_order` | RENAME | `sales_orders` | Standard plural table name for the commercial aggregate |
| 2026-09-15 | Sales Order | `sales_order_service_lines` | KEEP / CLARIFY | `sales_order_service_lines` | Customer-specific Service pricing remains on the SO line |
| 2026-09-15 | Sales Order | `sales_order_goods_lines` | KEEP / CLARIFY | `sales_order_goods_lines` | Customer-specific SKU pricing remains on the SO line without inventory behavior |
| 2026-09-15 | Sales Order | Fixed/repeated SO contact columns or no relation | ADD | `sales_order_contacts` | One order selects multiple Customer Contacts/roles and one Contact can serve many orders |
| 2026-09-15 | Sales Order | Separate SO address-selection table candidate | MERGE | `sales_orders.bill_to_customer_location_id` and `ship_to_customer_location_id` | Current header needs one selected location per role; full addresses snapshot only on AR Documents |
| 2026-09-15 | Sales Order | `sales_order_documents` | KEEP / CLARIFY | `sales_order_documents` | Multiple PO/contract/supporting files require child metadata rows |
| 2026-09-15 | Sales Order Approval | `sales_order_requests` | RENAME / RESHAPE | `sales_order_approval_submissions` | Record immutable submitted revision rather than a generic request |
| 2026-09-15 | Sales Order Approval | `sales_order_actions` | RENAME / RESHAPE | `sales_order_approval_decisions` | Record human approval/return/rejection against the revision |
| 2026-09-15 | Sales Order / Billing | `billing_schedules` as Billing-owned table | MOVE / REVIEW | `sales_order_billing_schedules` | Recurrence/milestones belong to the commercial agreement; exact enabled-MVP need is unresolved |
| 2026-09-15 | Sales Order / Billing | Separate `sales_order_milestones` candidate | DEFER | Use schedule rows if milestones are only billing obligations | A separate table needs an independently managed milestone-completion lifecycle |
| 2026-09-15 | Billing | `proforma_invoices` | MERGE | `ar_documents` with `document_type = PI` | Avoid duplicated header schema while preserving PI-specific rules |
| 2026-09-15 | Billing | `tax_invoices` | MERGE | `ar_documents` with `document_type = TI` | Reuse the common financial-document aggregate with TI-specific rules |
| 2026-09-15 | Billing | `credit_notes` | MERGE | `ar_documents` with `document_type = CN` | CN is a typed AR financial document; source eligibility remains reviewable |
| 2026-09-15 | Billing | `debit_notes` | MERGE | `ar_documents` with `document_type = DN` | DN is a typed AR financial document; source eligibility remains reviewable |
| 2026-09-15 | Billing | `pi_service_lines` | MERGE | `ar_document_lines` | Common structured line snapshots with explicit Service identity |
| 2026-09-15 | Billing | `pi_goods_lines` | MERGE | `ar_document_lines` | Common structured line snapshots with explicit Goods identity |
| 2026-09-15 | Billing | `ti_service_lines` | MERGE | `ar_document_lines` | Avoid duplicate tax/amount/line-history structure |
| 2026-09-15 | Billing | `ti_goods_lines` | MERGE | `ar_document_lines` | Avoid duplicate tax/amount/line-history structure |
| 2026-09-15 | Billing | `credit_note_lines` | MERGE | `ar_document_lines` | CN line semantics remain type-specific while physical structure is shared |
| 2026-09-15 | Billing | `debit_note_lines` | MERGE | `ar_document_lines` | DN line semantics remain type-specific while physical structure is shared |
| 2026-09-15 | Billing | `pi_ti_conversions` | MERGE | `ar_document_relations` | Typed PI → TI lineage belongs in the common document relation table |
| 2026-09-15 | Billing | `pi_ti_conversion_lines` | MERGE / DEFER DETAIL | `ar_document_relations` plus source SO/document line references | No separate conversion-line table until partial line-conversion behavior is confirmed |
| 2026-09-15 | Billing Approval | `billing_requests` | MERGE | `document_approval_submissions` | A request must identify the immutable submitted AR Document revision |
| 2026-09-15 | Billing Approval | `billing_actions` | MERGE | `document_approval_decisions` | Human decisions require actor/time/reason and a submission FK |
| 2026-09-15 | Billing | Header/line live-master joins for historical output | REMOVE | Structured snapshots on `ar_documents` and `ar_document_lines` | Finalized output must not change when Company/Customer/catalogue/tax masters change |
| 2026-09-15 | Billing / Goods | `dispatch_details` | RENAME / REVIEW | `ar_document_dispatch_details` | One 1:1 block is enough only if simple invoice-level dispatch is confirmed |
| 2026-09-15 | Billing | No explicit document relationship | ADD | `ar_document_relations` | PI conversion, CN/DN references, adjustments, and reversals require typed FKs |
| 2026-09-15 | Approval | Status-only approval | ADD | submission and decision tables per aggregate | Preserve revision-specific human approval without a generic workflow engine |
| 2026-09-15 | PDF | Regenerate from current templates/branding | ADD | `document_artifacts` | Preserve exact approved PDF metadata, hash, and storage reference |
| 2026-09-15 | Delivery | `email_templates` | MOVE / MERGE | Existing `company_document_templates` | Do not duplicate reviewed Company template configuration downstream |
| 2026-09-15 | Delivery | `invoice_email_logs` | MERGE / RESHAPE | `invoice_delivery_requests` + `invoice_delivery_attempts` | Separate durable send intent from provider retry attempts |
| 2026-09-15 | Delivery | Synchronous SMTP during approval | REMOVE | Durable asynchronous delivery request/worker | Provider/PDF failure must not roll back document approval |
| 2026-09-15 | Collections | `invoice_reminder_state` | MERGE / RESHAPE | `reminder_occurrences` | One row per planned/sent/skipped occurrence prevents duplicates and preserves history |
| 2026-09-15 | Collections | Copy Company reminder schedules to invoices | REMOVE | Resolve policy at planning and pin occurrence evidence | Avoid stale duplicate policy while retaining what actually happened |
| 2026-09-15 | Receivables | Separate mutable `receivables` balance table | REMOVE | Derived receivable position | Avoid multiple mutable authorities for the same outstanding balance |
| 2026-09-15 | Receipt | `payment_receipts` / `payment_reciepts` | RENAME / CLARIFY | `receipts` | Receipt amount is cash only and retains bank/currency identity |
| 2026-09-15 | Receipt | `payment_allocations` with one ambiguous amount | KEEP / RESHAPE | `payment_allocations` with receipt/document currency amounts and reversals | Preserve N:M knock-off, FX meaning, and history |
| 2026-09-15 | TDS | TDS included in Receipt cash or fixed allocation columns | REMOVE | `settlement_adjustments` | TDS is non-cash, uses selected configured section/rate, and needs independent reversal/history |
| 2026-09-15 | Receipt | `pi_ti_allocation_transfer` | RENAME / RESHAPE | `allocation_transfers` linking reversal and replacement allocation | Preserve where cash was first allocated and who moved it to TI |
| 2026-09-15 | Audit | Module-specific Customer/SO/Invoice/Payment audit tables | REMOVE | Shared `audit_events` | One append-only evidence store avoids duplicate audit structures while typed business history remains separate |
| 2026-09-15 | Reporting | `report_runs` | DEFER | Reporting/Analytics specification | No current durable report-job/artifact lifecycle is defined |
| 2026-09-15 | Reporting | `report_run_exchange_rates` | DEFER | Reporting/Analytics specification | Only justified with retained reproducible report runs |
| 2026-09-15 | Shared Reference | `uom_master` | DEFER | Keep reviewed catalogue UOM columns | Do not alter approved Company Configuration without a controlled-UOM requirement |
| 2026-09-15 | Shared Reference | `uom_conversion` | DEFER | No current table | Cross-UOM and inventory conversion are not current AR requirements |
| 2026-09-15 | Shared Reference | `countries` | DEFER | Controlled `country_code` values | No ERP-administered Country master requirement is confirmed |
| 2026-09-15 | Shared Reference | `states` | DEFER | Controlled state/place-of-supply codes | No ERP-administered State master requirement is confirmed |
| 2026-09-15 | Commercial | `credit_period` | MERGE | Existing `payment_terms` | Immediate/Net Days already own reusable term identity; invoice keeps term/due-date snapshot |
| 2026-09-15 | Company Location | GST Registration association without a default Location | UPDATE | `company_locations.is_default_for_gstin` | One GST Registration can have several Locations and, where applicable, exactly one active mapped default; state/GST compatibility and historical inactivation are enforced |
| 2026-09-15 | Tax Family | `tax_type` / `tax_scheme` text embedded directly in tax references | ADD / REFERENCE | `tax_types`; `tax_rates.tax_type_id`; `statutory_sections.tax_type_id` | GST, TDS, TCS, VAT and CESS use one controlled family identity without mixing their calculation models |
| 2026-09-15 | Catalogue / Tax | Shared full HSN/SAC catalogue or ambiguous `tax_classifications` | RENAME / REPLACE | Company-owned `company_hsn_sac_codes` | A Company configures only relevant HSN/SAC codes and the table name cannot imply GST/TDS/TCS classification |
| 2026-09-15 | Catalogue / Tax | `tax_classification_rates` | RENAME / REPLACE | `company_hsn_sac_tax_rates` | The name makes Company ownership and the HSN/SAC-to-eligible-rate relationship explicit |
| 2026-09-15 | Catalogue / Tax | GST Treatment pending or repeated as a code/rate type | ADD / NORMALIZE | `tax_treatments` with TAXABLE/NIL_RATED/EXEMPT/NON_GST | Treatment is a controlled concept distinct from the eligible numeric rate; `ZERO_RATED` is not introduced |
| 2026-09-15 | Catalogue / Tax | Direct or uncontrolled item tax percentage | CLARIFY | Company HSN/SAC → effective eligible-rate mapping → `service_types.selected_tax_rate_id` / `skus.selected_tax_rate_id` → final line snapshot | Preserves multiple valid rates while recording the current catalogue default and preventing uncontrolled percent text |
| 2026-09-15 | Catalogue / Tax | Separate `ar_service_tax_assignment` / `ar_sku_tax_assignment` proposal | REMOVE | Direct Company SAC/HSN, Tax Treatment and selected eligible-rate FKs on Service Type/SKU | No confirmed current requirement needs separate effective assignment history; finalized invoice lines preserve transaction facts |
| 2026-09-15 | Billing Tax History | Final lines could depend on current tax masters | CLARIFY | HSN/SAC code/description, Tax Treatment, applied rate, GST components and applicable TCS details snapshotted | Later Company HSN/SAC, treatment, or rate changes must not rewrite issued documents |
| 2026-09-15 | Sales Order / Billing | Customer-only transaction context | UPDATE | `transaction_classification` plus same-Company source/destination GST Registration and Location fields | `INTER_UNIT` is not a Customer sale and must not create normal AR outstanding |
| 2026-09-15 | Sales Order / Billing | Ship-To limited to Customer Location | UPDATE | `ship_to_type` plus Customer Location or Company Location FK | Ship-To may be external or the seller Company's own Location; final documents snapshot the selected address |
| 2026-09-15 | GSTR-1 Filing | Generic GST filing completion flag/wording | ADD | `gstr1_filing_batches` keyed by GST Registration + Return Period + Return Type | Filing context, status, reference, timestamp, and actor require an auditable batch header |
| 2026-09-15 | GSTR-1 Filing | Invoice considered locked when merely placed in a filing batch | ADD / CLARIFY | `gstr1_filing_batch_documents`; hard lock only for active membership in a FILED batch | Draft membership remains changeable with audit; filed membership freezes the exact documents |
| 2026-09-15 | E-Invoice | No explicit successful IRN edit guard | UPDATE | E-invoice status and IRN evidence on `ar_documents` | Successful e-invoice/IRN generation independently blocks in-place invoice editing |
| 2026-09-15 | Historical Editing | Broad month-end edit restriction | UPDATE | Period-lock authorization rule plus statutory GSTR-1/IRN locks | Normal users cannot edit/post in a locked period; a policy-permitted authorized exception needs reason and full audit, while filed/IRN statutory locks follow their correction processes |
| 2026-09-15 | Receivables | Every eligible document classification could affect Customer outstanding | UPDATE | Derived receivable position limited to eligible `CUSTOMER_SALE` documents | Inter-Unit documents may have statutory effects but never create normal Customer AR outstanding |
| 2026-09-15 | Accounting | Fixed revenue-account names or completed inter-unit clearing design | CLARIFY | Company-specific CoA direction under review at that point | Historical decision before the approved mappings below; fixed account names were rejected and Inter-Unit clearing remains open |
| 2026-09-15 | Company Configuration / Accounting | Chart of Accounts identified only as future open design | UPDATE | Company-specific Accounting Setup and Chart of Accounts | Companies must create their own accounts before AR can resolve accounting references; full posting remains separate |
| 2026-09-15 | Accounting | No controlled broad account nature | ADD | `account_types` | Revenue and Tax Mapping screens need type-based eligibility without inferring meaning from account names |
| 2026-09-15 | Accounting | No Company-owned account identity | ADD | `gl_accounts` | Company-defined names, optional codes, types, hierarchy, and lifecycle need stable references |
| 2026-09-15 | Revenue Mapping | Revenue account selection left to later/manual handling | ADD | `revenue_account_mappings` | Billing needs a named Company configuration that resolves an appropriate revenue GL automatically |
| 2026-09-15 | Revenue Mapping | Supply context not normalized for account resolution | ADD | `revenue_mapping_supply_types` | Existing B2B/B2C/Export/SEZ Supply Types drive mappings without arrays or a magic `DOMESTIC` value |
| 2026-09-15 | Revenue Mapping | HSN/SAC-to-account relationship entirely open | ADD | `revenue_mapping_hsn_sac` | Optional Company HSN/SAC conditions support specific revenue exceptions without making classification equal to one account |
| 2026-09-15 | Revenue Mapping | No deterministic general-versus-specific order | CLARIFY | Specific Supply Type + HSN/SAC before general Supply Type | Scrap/other exceptions must win; missing or same-specificity ambiguous matches block instead of selecting silently |
| 2026-09-15 | Tax Mapping | Tax ledger selected manually or inferred from a fixed name | ADD | `tax_gl_account_mappings` | Calculated CGST/SGST/IGST components resolve appropriate Company tax-liability accounts automatically |
| 2026-09-15 | Billing UX | Invoice user could be asked to choose revenue/tax ledgers | UPDATE | Automatic mapping resolution | Account policy is configured once; routine invoice entry consumes the resolved Supply Type, classification, and components |
| 2026-09-15 | Billing History | Mapping changes could reinterpret historical accounting classification | UPDATE | Final GL Account references on `ar_document_lines` | Finalized lines retain resolved revenue and applicable tax-component account IDs |
| 2026-09-15 | Accounting Flexibility | Example account names could become fixed product values | CLARIFY | Mappings reference Company GL Account IDs | `Sales - Domestic`, `Sales - Export`, `Scrap Sales`, and Output Tax names are examples only |
| 2026-09-15 | Accounting Setup | Starter Chart of Accounts could become a mandatory fixed list | DEFER / CLARIFY | Optional future starter templates | Templates may seed Company accounts but no full template engine or compulsory 15–20-account list is added |
| 2026-09-15 | Inter-Unit Accounting | All Inter-Unit accounting treatment could be inferred from AR mapping | CLARIFY | Clearing/inter-unit GL treatment remains OPEN | Inter-Unit may post accounting but never creates normal Customer AR; balancing/clearing design requires later Accounting decisions |

# 22. Table Decision Summary

## Company Configuration — reviewed section

Sections 1–13 remain the source of truth. They contain **59 KEEP tables**, **4 REVIEW/conditional tables**, and **1 DEFERRED accounting-classification table**. This includes the global Country and Country Subdivision masters, three generic Company legal-identifier tables, KEEP `company_location_versions`, `gst_registration_types`, two controlled tax masters, generalized statutory-code tables, separate Team reporting-bucket and actual-Team identities, eight approved Accounting Setup tables, and shared `stored_files` metadata; Company/GST profile-version concepts remain REVIEW and `account_types` is DEFERRED.

With the **32 downstream ADD** proposals, the conditional physical catalogue would total **91 tables** only if every ADD table is later approved. Renamed/replaced/deferred legacy structures are dispositions, not additional physical tables.

## Downstream current review candidates

### ADD — 32 tables

- Customer: `customer_organisations`, `customers`, `customer_gst_registrations`, `customer_locations`, `customer_contacts`, `customer_contact_roles`, `customer_documents`, `customer_approval_submissions`, `customer_approval_decisions` — 9.
- Sales Order: `sales_orders`, `sales_order_service_lines`, `sales_order_goods_lines`, `sales_order_contacts`, `sales_order_documents`, `sales_order_approval_submissions`, `sales_order_approval_decisions` — 7.
- Billing/Approval/Delivery/Compliance: `ar_documents`, `ar_document_lines`, `ar_document_relations`, `gstr1_filing_batches`, `gstr1_filing_batch_documents`, `document_approval_submissions`, `document_approval_decisions`, `document_artifacts`, `invoice_delivery_requests`, `invoice_delivery_attempts` — 10.
- Receipt/Collections: `receipts`, `payment_allocations`, `settlement_adjustments`, `allocation_transfers`, `reminder_occurrences` — 5.
- Shared Audit: `audit_events` — 1.

### REVIEW — 4 downstream tables

- `customer_delivery_settings`
- `customer_reminder_settings`
- `sales_order_billing_schedules`
- `ar_document_dispatch_details`

### DEFER — 8 Company Configuration/downstream/legacy candidates

- `customer_location_versions`
- `industries`
- `sales_order_milestones`
- `report_runs`
- `report_run_exchange_rates`
- `uom_master`
- `uom_conversion`
- `account_types` — deferred from the current AR CoA foundation to the full Accounting classification design.

### REMOVE — 1 reviewed standalone candidate

- `receivables` — use a derived receivable position; it is not a current physical source table.

The change log also records **33 legacy table/design entries with MERGE, REMOVE, or REPLACE actions**, including replaced Company-identifier, tax, and accounting structures, into current aggregates or reviewed Company Configuration tables. Renames, moves, and reshaped replacements are traceability actions and are not additional current tables.

## Combined counts for the whole document

| Decision | Count | Included as current physical tables? |
|---|---:|---|
| KEEP | 59 | Yes; reviewed Company Configuration and shared metadata, including Country/Subdivision references, generic Company identifiers, Location address versions, GST Registration Types, separate Cost Center Team and actual Team identities, generalized tax/statutory references, eight Accounting Setup tables, and `stored_files` |
| ADD | 32 | Proposed downstream candidates; implement only after table-by-table approval |
| REVIEW | 8 | No automatic implementation: 4 Company Configuration + 4 downstream |
| DEFER | 8 | No; includes deferred `account_types` plus 7 existing downstream/legacy candidates |
| REMOVE / MERGED / REPLACED | 33 | No; legacy table/design change-log entries, including replaced Company-identifier/tax/accounting structures and the standalone `receivables` removal |

The proposed current physical catalogue is therefore **91 tables only if all 32 downstream ADD candidates are approved**. The 8 REVIEW and 8 DEFER entries are not part of that total, and the 33 removed/merged/replaced legacy change-log entries are never counted as current tables.
