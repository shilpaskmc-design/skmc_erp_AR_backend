# Company Configuration Business Rules

## Status and authority

**Document status:** `PROPOSED` Company Configuration decision baseline.

`CONFIRMED` domain rules below govern the current proposal but do not authorize implementation. Unresolved matters are isolated in [Open Decisions](open_decisions.md). Physical table detail belongs in [Data Model](data_model.md).

## 1. Ownership & Domain Boundary

**Status: `CONFIRMED`**

- **Tenant** is the SaaS isolation boundary. Every Company-scoped record must resolve to exactly one Tenant through authoritative ownership relationships.
- **Organisation** is an optional non-legal grouping layer inside a Tenant. A Company may exist directly under a Tenant without an Organisation, and an Organisation supplies no configuration inheritance in MVP.
- **Company** is the legal entity, seller/billing boundary, tax registration owner, and accounting boundary.
- Shared facts about a Company belong to Core/Shared; AR-only policies stay within the AR configuration boundary.
- No shared Party, Vendor, Contact, or Counterparty master is introduced.

## 2. Company Identity & Lifecycle

**Status: `CONFIRMED`**

- Company Code is generated from a global concurrency-safe sequence as `COM000001`, is globally unique, and is immutable in normal operation.
- Entity Type selection identifies the Company's primary legal form from jurisdiction-scoped, platform-managed reference data (`entity_types`).
- Company legal identifiers (PAN, CIN, LLPIN, etc.) are captured using generic `company_identifiers` driven by `entity_type_identifier_rules`. No permanent identifier-specific columns exist on `companies`.
- Dedicated effective-dated legal-name history (`company_legal_name_versions`) preserves prior values for stable Company identity.
- Normal MVP legal-name changes take effect immediately, close the prior inclusive date range on the preceding day, and create a new current version atomically with the current projection.
- Company Status supports `DRAFT`, `ACTIVE`, and `INACTIVE`. `INACTIVE` is terminal in MVP; an inactive Company is read-only, and historical transactions remain accessible.

## 3. Locations & Addresses

**Status: `CONFIRMED`**

- At most one active Registered Office exists per Company at all times. Exactly one active Registered Office is required for activation.
- `location_code` is the immutable Company-scoped stable reference; `location_name` is mutable display/search text.
- One physical Location can serve multiple fixed purposes (e.g., Registered Office + Billing Office). Non-Registered-Office purposes may repeat across Locations.
- A Location belongs to zero or one GST Registration through a direct nullable association (`gst_registration_id`). Mapped Location state/jurisdiction must match the GST Registration.
- At most one active mapped Location is the default for a GST Registration (`is_default_for_gstin`).
- Location address and jurisdiction history is effective-dated via `company_location_versions`.
- Location lifecycle is terminal `ACTIVE` → `INACTIVE`. An inactive Location cannot be reactivated or edited.

## 4. GST Registrations & LUTs

**Status: `CONFIRMED`**

- GST Registrations are State-scoped (`country_subdivisions.gst_state_code`), use a 15-character structurally valid GSTIN, and follow `DRAFT` → `ACTIVE` → `INACTIVE`.
- At most one active GST registration is supported per Company per Indian State/UT in MVP.
- Company Legal Name and GST Registration Legal Name are distinct current facts.
- Excel Bulk Import supports GST Registrations and Location Mappings with create-or-compare, non-editing, and additive mapping rules.
- LUT references (`company_luts`) apply to without-payment Export/SEZ routes (`EXPWOP` and `SEZWOP`). At most one active LUT exists per GSTIN and fiscal period.
- Missing required LUT blocks finalization for `EXPWOP` and `SEZWOP`; `EXPWP` and `SEZWP` are not blocked solely for missing LUT.

## 5. Fiscal Settings & Financial Years

**Status: `CONFIRMED`**

- A Company defines one recurring fiscal start pattern (`APR_MAR`, `JAN_DEC`, or `CUSTOM` with explicit start month and day).
- Actual Financial Years (`financial_years`) are dated, carry display codes (e.g. `2026-27`), and follow `DRAFT` → `OPEN` → `CLOSED`.
- Financial Years for the same Company must not overlap. Short or transition Financial Years are explicitly supported.
- Creating a future Financial Year leaves the prior Financial Year's close/lock state unchanged.
- Financial Year, accounting close, and accounting lock remain separate concepts.

## 6. Business Nature & Catalogues

**Status: `CONFIRMED`**

- Business Nature selection: Services, Goods, or Both.
- **Service Catalogue**: Service Category → Service Type. Service Type stores SAC, Base GST Nature (`TAXABLE`, `NIL_RATED`, `EXEMPT`, `NON_GST`), conditional selected eligible rate, `tcs_check_required` flag, and optional Business Segment.
- **Goods Catalogue**: Product Category → Product → SKU. SKU stores SKU Code, Product, HSN, Base GST Nature, conditional selected eligible rate, UOM, `tcs_check_required` flag, and optional Business Segment.
- **HSN / SAC Classification**: Company configures relevant codes (`company_hsn_sac_codes`) and effective eligible rates (`company_hsn_sac_tax_rates`). Service Type references SAC; SKU references HSN.
- Terminal inactivation hierarchy applies: parents cannot be inactivated while active children exist. Child re-parenting is prohibited.

## 7. Cost Centers & Management Reporting

**Status: `CONFIRMED`**

- `company_cost_center_settings` enables or disables independent bases: Business Segment, Team, and Location.
- Business Segment: direct association with Service Types and SKUs (max 1 Segment per item).
- Team: Cost Center Team reporting buckets group actual Company Teams; actual Teams hold effective-dated user memberships.
- Location Cost Center: groups physical Company Locations.
- Inactivation is terminal `ACTIVE` → `INACTIVE`. Inactive masters remain readable for history.

## 8. Payment Terms & Customer Code Configuration

**Status: `CONFIRMED`**

- Payment Terms (`IMMEDIATE` and `NET_DAYS`) maintain at most one active Company default.
- Customer Onboarding selects one active same-Company Payment Term as Customer Default Credit Period, falling back to Company default.
- Customer Code is system-generated and belongs to Company Configuration.
- The prefix is Company-configured (NOT hard-coded).
- Numeric padding/digits are Company-configured.
- Sequence is scoped to the Company, starts at 1, and does not automatically reset.
- Code is allocated only during successful `NEW_CUSTOMER` approval/publication and remains stable once allocated.
- Prefix validation, padding overflow behavior, and the Company-readiness / Customer-approval configuration gate remain `REVIEW` items.

## 9. AR Document Numbering

**Status: `CONFIRMED`**

- Proforma Invoice (PI), Tax Invoice (TI), Debit Note (DN), and Credit Note (CN) series are configured per FY/context.
- Final document numbers are allocated atomically upon approval/finalization and are never reused after cancellation. Parallel series retain independent counters.

## 10. Currencies, Banking & Output Settings

**Status: `CONFIRMED`**

- Configures Base Currency, additional Reporting Currencies, and AR Currencies (Billing & Receipt permissions).
- Directional corporate/spot Exchange Rates (`exchange_rates`) and FX Policies (`fx_policies`).
- Bank Accounts with currency, account type, optional Bank GL FK, and default billing bank per currency.
- Branding assets (logo, signature, stamp) stored in `stored_files`; versioned document templates (`company_document_templates`).
- Automatic invoice send default is `OFF`.
