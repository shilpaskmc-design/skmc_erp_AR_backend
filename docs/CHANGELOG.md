# Documentation and Design Change Log

Git records file-level history. This file records the meaning, authority, and disposition of important product, domain, architecture, and database-design changes. It does not replace Git history, the governing requirement, or a standalone decision record when one is required.

## Entry Statuses

| Status | Meaning |
|---|---|
| PROPOSED | Submitted for review; not approved for implementation. |
| APPROVED | Explicitly accepted as the current decision for its stated scope. |
| IMPLEMENTED | Delivered in implementation and supported by repository evidence. |
| SUPERSEDED | Replaced by a later approved change. |
| REJECTED | Considered and deliberately not adopted. |
| DEFERRED | Intentionally postponed and excluded from the current implementation slice. |
| CORRECTED | Fixes an error or ambiguity without introducing an unapproved new product rule. |

## Change IDs

Use `CHG-YYYY-MM-DD-NNN`, where the final three digits are a sequence for that date.

## Entry Template

### CHG-YYYY-MM-DD-NNN — Short title

- **Change ID:** CHG-YYYY-MM-DD-NNN
- **Date:** YYYY-MM-DD
- **Status:** PROPOSED | APPROVED | IMPLEMENTED | SUPERSEDED | REJECTED | DEFERRED | CORRECTED
- **Area:** Product | Domain | Architecture | Database Design | Cross-cutting
- **Source / discussion context:** Link or describe the approving request, review, or decision record.
- **Decision:** State the current decision and its scope.
- **Reason:** Explain why the change was made.
- **Supersedes:** List earlier change IDs, decision records, or clearly identified prior directions; use “None” when applicable.
- **Affected documents:** List the owning and impacted documents.
- **Implementation impact:** State whether implementation work is required, prohibited, completed, or separately pending.
- **Open follow-ups:** List unresolved consequences without deciding them by assumption.

## Baseline Established — 2026-09-17

All product, architecture, requirement, database-design, reference, and historical documentation that existed before this governance setup is treated as the imported documentation baseline. Importing the baseline does not promote every statement to approval: each document and statement retains its own FINAL, CONFIRMED, MVP, PROPOSED, KEEP, ADD, REVIEW, TBD, CONFIGURE, DIRECTION, DEFERRED, POST-MVP, FUTURE, or historical status.

This log does not attempt to reconstruct every prior discussion or Git event. Future meaningful proposed or approved product/design changes must receive a new change ID and must identify any superseded direction.

### CHG-2026-09-17-019 — Finalize AR Delivery, Reminders, and Company Access configuration

- **Change ID:** CHG-2026-09-17-019
- **Date:** 2026-09-17
- **Status:** APPROVED
- **Area:** Domain / Database Design
- **Description:**
  - Resolved `company_user_memberships` from REVIEW to KEEP as the required explicit authorization boundary. Tenant membership alone does not grant access.
  - Finalized AR Invoice Delivery Configuration (`email_provider_configs`, `company_invoice_delivery_settings`) as KEEP with explicit physical definitions. Clarified automatic/manual send behaviour and asynchronous execution.
  - Finalized AR Reminder Defaults (`reminder_policies`, `reminder_schedule_rules`) as KEEP. Defined the single Company default policy, reminder schedule offsets, and Company → Customer → Invoice override precedence.
  - Removed unapproved default 'ACTIVE' values for accounting status columns in `account_groups` and `gl_accounts`.
  - Clarified that LUT document upload is deferred until a later requirement enables it.

### CHG-2026-09-17-001 — Current Accounting and AR GL configuration baseline

- **Change ID:** CHG-2026-09-17-001
- **Date:** 2026-09-17
- **Status:** APPROVED
- **Area:** Domain / Database Design
- **Source / discussion context:** Latest approved Accounting/CoA direction already reflected in the current Product Overview, Company Configuration requirements, AR MVP architecture, focused Billing/Tax documents, and the dated Accounting entries in `requirements/database.md`.
- **Decision:** Each Company creates or imports its own Account Groups, stable GL Accounts, and hierarchy. The current design uses `account_hierarchies`, `account_groups`, `account_group_relationships`, stable-identity `gl_accounts`, and effective-dated `gl_account_group_mappings`. AR account configuration uses `company_accounting_settings`, `revenue_gl_mappings`, `tax_gl_account_mappings`, `tax_statutory_codes`, `tax_statutory_code_rates`, and `company_bank_accounts.gl_account_id`. Eligible finalized AR Documents preserve the resolved Receivable GL ID, and finalized AR lines preserve resolved Revenue and applicable tax GL IDs.
- **Reason:** Separating stable GL identity from effective-dated hierarchy placement preserves historical reporting through reorganizations, permits future Management views to reuse the same accounts, removes hardcoded account-name assumptions, and prevents later mapping changes from silently rewriting finalized accounting references.
- **Supersedes:** `account_types` as a current AR/CoA foundation; hierarchy embedded in `gl_accounts`; `revenue_account_mappings`, `revenue_mapping_supply_types`, and `revenue_mapping_hsn_sac`; `statutory_sections` and `statutory_section_rates` as the current names; free-text Tax GL component mapping. Older intermediate designs may remain in historical change-log text but are not current design authority.
- **Affected documents:** `PRODUCT_OVERVIEW.md`; `AR_MVP_ARCHITECTURE.md`; `architecture/moduleboundaries.md`; `requirements/COMPANY_CONFIGURATION.md`; `requirements/database.md`; `requirements/billing_and_invoicing.md`; `requirements/tax_satutory_rules.md`; `requirements/approval_and_audit`.
- **Implementation impact:** This records the approved documentation baseline. It does not prove implementation and does not authorize migrations, models, APIs, frontend work, or a full Accounting engine. Implementation requires a separately requested and approved slice.
- **Open follow-ups:** Accounting classifications; detailed Management-hierarchy behavior; CoA import/export format and validation; historical accounting correction/reclassification entries; expanded Receivable routing; posting journals, reconciliation, period closing, and Inter-Unit clearing.

### CHG-2026-09-17-002 — Align Accounting module boundaries

- **Change ID:** CHG-2026-09-17-002
- **Date:** 2026-09-17
- **Status:** CORRECTED
- **Area:** Architecture / Module Boundaries / Accounting
- **Source / discussion context:** Post-governance alignment of `architecture/moduleboundaries.md` to the Accounting/CoA direction already approved in CHG-2026-09-17-001.
- **Decision:** No new product decision was introduced. Core/Shared ownership now states Company accounting identity, effective hierarchy placement, default Receivable GL configuration, Bank-to-GL association, and shared statutory identities; AR ownership states Revenue/Tax GL resolution and preservation of resolved transaction references.
- **Reason:** Correct the boundary presentation and ensure stale intermediate Account Type, Revenue Mapping, and statutory-section terminology is replaced by the already-approved stable-GL, `revenue_gl_mappings`, Tax Statutory Code, and effective-mapping direction.
- **Supersedes:** Documentation wording only; no approved product or architecture decision is superseded.
- **Affected documents:** `architecture/moduleboundaries.md`.
- **Implementation impact:** Documentation only. No code, migration, schema, API, frontend, or infrastructure change is authorized or required by this correction.
- **Open follow-ups:** Existing deferred Accounting responsibilities remain deferred; this entry resolves none of them.

### CHG-2026-09-17-003 — Align Company Location purpose multiplicity

- **Change ID:** CHG-2026-09-17-003
- **Date:** 2026-09-17
- **Status:** CORRECTED
- **Area:** Company Configuration / Company Locations
- **Source / discussion context:** Post-governance correction of stale TBD wording in the Company Location requirement to the already-approved fixed-purpose Location model.
- **Decision:** No new product rule was introduced. One physical Company Location may serve multiple applicable fixed purposes, while exactly one active Registered Office remains required per Company. The direct relationship from one GST Registration to multiple Company Locations is unchanged.
- **Reason:** Align the owning requirement with the current database and architecture direction and avoid duplicate Location records for one physical address.
- **Supersedes:** The stale statement that Location-purpose multiplicity was still TBD; no approved product decision is superseded.
- **Affected documents:** `requirements/COMPANY_CONFIGURATION.md`.
- **Implementation impact:** Documentation only. No database, code, migration, API, frontend, or infrastructure change is authorized or required.
- **Open follow-ups:** Existing unrelated Company Configuration decisions remain open.

### CHG-2026-09-17-004 — Align Sales Order accounting boundary

- **Change ID:** CHG-2026-09-17-004
- **Date:** 2026-09-17
- **Status:** CORRECTED
- **Area:** Sales Order / Accounting Boundary
- **Source / discussion context:** Post-governance correction of stale Sales Order wording against the already-approved Company CoA and AR GL mapping foundation.
- **Decision:** No new business decision was introduced. Sales Order does not normally select Revenue or Tax GL Accounts or own accounting posting; Billing resolves the configured AR mappings and finalized transactions preserve the resolved references.
- **Reason:** Remove the implication that Company-specific CoA and Revenue/Tax account design are entirely future or undefined.
- **Supersedes:** Stale Sales Order wording only; no approved product or architecture decision is superseded.
- **Affected documents:** `requirements/sales_order_commercial_setup.md`.
- **Implementation impact:** Documentation only. No database, code, migration, API, frontend, or infrastructure change is authorized or required.
- **Open follow-ups:** Full Accounting posting and Inter-Unit clearing/balancing remain open or deferred.

### CHG-2026-09-17-005 — Clarify Accounting ownership across current documentation

- **Change ID:** CHG-2026-09-17-005
- **Date:** 2026-09-17
- **Status:** CORRECTED
- **Area:** Accounting Ownership / Documentation Consistency
- **Source / discussion context:** Final documentation consistency-audit corrections against the Accounting ownership already approved in CHG-2026-09-17-001 and reflected in `architecture/moduleboundaries.md`.
- **Decision:** No new Accounting or AR decision was introduced. Core/Shared owns the current Company CoA structure, default Receivable GL configuration, Bank GL association, and shared statutory identities; AR owns Revenue/Tax GL mapping and resolution and preservation of finalized AR GL references.
- **Reason:** Remove mixed ownership labels and stale wording that could imply the Company CoA foundation remains future.
- **Supersedes:** Documentation wording only; no approved product, Accounting, or AR decision is superseded.
- **Affected documents:** `requirements/COMPANY_CONFIGURATION.md`; `AR_MVP_ARCHITECTURE.md`; `requirements/database.md`.
- **Implementation impact:** Documentation only. No database, code, migration, schema, API, frontend, infrastructure, or test change is authorized or required.
- **Open follow-ups:** Full Accounting journals/posting, ledger processing, reconciliation, closing/locking, accounting correction/reclassification, and Inter-Unit clearing/balancing remain future or open.

### CHG-2026-09-17-006 — Approve the Organisation grouping design

- **Change ID:** CHG-2026-09-17-006
- **Date:** 2026-09-17
- **Status:** APPROVED
- **Area:** Company Configuration / Database Design
- **Source / discussion context:** Approved review of the `organisations` business definition and database-design boundary.
- **Decision:** Organisation is an optional Tenant-scoped, non-legal grouping of Companies. It provides no Company configuration inheritance; Company remains the legal, billing, tax, and accounting entity and retains direct authoritative Tenant ownership.
- **Reason:** Preserve a structured grouping reference for multi-Company Tenants without forcing an extra layer, weakening Tenant isolation, or moving Company configuration to Organisation.
- **Supersedes:** The earlier compact `organisations` description; no conflicting approved business rule is superseded.
- **Affected documents:** `requirements/database.md`; `requirements/COMPANY_CONFIGURATION.md`.
- **Implementation impact:** Documentation and database design only. No migration, model, SQL, API, frontend, test, or infrastructure work is authorized or completed.
- **Open follow-ups:** Finalize database enforcement of Company/Organisation Tenant consistency during the `companies` table review. Generic Audit/retention behavior remains future work.

### CHG-2026-09-17-007 — Approve the controlled Entity Type reference design

- **Change ID:** CHG-2026-09-17-007
- **Date:** 2026-09-17
- **Status:** APPROVED
- **Area:** Company Configuration / Shared Reference / Database Design
- **Source / discussion context:** Approved review of the `entity_types` business definition and database-design boundary.
- **Decision:** Entity Type is a jurisdiction-scoped, platform-managed primary legal-form reference. Companies save `entity_type_id` rather than free text; the stable machine code and display name have separate purposes, and normal Company users cannot create arbitrary Entity Types.
- **Reason:** Prevent spelling variants and hardcoded legal forms while preserving stable Company relationships and future jurisdiction expansion.
- **Supersedes:** The earlier compact `entity_types` description and nullable-jurisdiction direction; no conflicting approved legal-form list is superseded.
- **Affected documents:** `requirements/database.md`; `requirements/COMPANY_CONFIGURATION.md`.
- **Implementation impact:** Documentation and database design only. No migration, model, seed data, SQL, API, frontend, test, or infrastructure work is authorized or completed.
- **Open follow-ups:** Resolve the physical mandatory jurisdiction reference with the Country-master review; design legal-identifier applicability separately; keep import aliases/normalization deferred; do not freeze the complete India matrix, Section 8, or Foreign Company classification here.

### CHG-2026-09-17-008 — Approve generic Company legal identifiers

- **Change ID:** CHG-2026-09-17-008
- **Date:** 2026-09-17
- **Status:** APPROVED
- **Area:** Company Configuration / Shared Reference / Database Design
- **Source / discussion context:** Approved review of the generic Company legal-identifier architecture.
- **Decision:** Replace permanent PAN/CIN/LLPIN columns on `companies` with `company_identifier_types`, `company_identifiers`, and `entity_type_identifier_rules`. Platform-managed jurisdiction-scoped types and applicability rules drive required/optional inputs; Company users provide the actual values.
- **Reason:** Support future jurisdictions without repeatedly widening the Company schema or duplicating statutory rules in frontend and backend.
- **Supersedes:** The current direct PAN/CIN/LLPIN Company-column direction; historical references remain change history.
- **Affected documents:** `requirements/database.md`; `requirements/COMPANY_CONFIGURATION.md`.
- **Implementation impact:** Documentation and database design only. No migration, model, SQL, seed data, API, frontend, test, or infrastructure work is authorized or completed.
- **Open follow-ups:** Finalize jurisdiction representation, statutory applicability matrices, identifier value uniqueness/format/normalization, and profile version/audit mechanics. Import aliases remain deferred; GSTIN remains in GST Registration architecture.

### CHG-2026-09-17-009 — Refine Company and GST Registration identity

- **Change ID:** CHG-2026-09-17-009
- **Date:** 2026-09-17
- **Status:** APPROVED
- **Area:** Company Configuration / GST Registration / Database Design
- **Source / discussion context:** Approved Company-master column review and GST Registration design refinement.
- **Decision:** Freeze the currently approved Company columns and distinguish current Company legal name from each GSTIN's registered legal name. Confirm globally unique Company-owned GSTINs, retained GST Registration Type and mandatory State/UT jurisdiction, separate Company/GST version-history concepts, and immutable finalized seller snapshots.
- **Reason:** Preserve legal and statutory identity across asynchronous Company-name and GST-registration amendments without widening Company with jurisdiction-specific fields or rewriting historical invoices.
- **Supersedes:** Ambiguous `registered_name` wording and incomplete current Company/GST column descriptions; direct PAN/CIN/LLPIN columns remain superseded by CHG-2026-09-17-008.
- **Affected documents:** `requirements/database.md`; `requirements/COMPANY_CONFIGURATION.md`.
- **Implementation impact:** Documentation and database design only. No migration, model, SQL, seed data, API, frontend, test, or infrastructure work is authorized or completed.
- **Open follow-ups:** Company code rules, Company draft nullability, Company lifecycle values, Country/State physical references, GST statutory status values, complete profile/GST version columns, and Audit/retention mechanics remain open.

### CHG-2026-09-17-010 — Approve Company Location and address-history design

- **Change ID:** CHG-2026-09-17-010
- **Date:** 2026-09-17
- **Status:** APPROVED
- **Area:** Company Configuration / Company Location / Database Design
- **Source / discussion context:** Approved Company Location and effective-dated address-history review.
- **Decision:** Confirm `company_locations` and narrowly scoped `company_location_versions` as KEEP. Retain direct nullable GST Registration and Location Cost Center relationships, fixed multi-purpose flags, Registered Office/default-per-GSTIN rules, and same-Company/jurisdiction protections. Remove/defer unused `location_code`; version only effective address/jurisdiction state.
- **Reason:** A stable Location may move while preserving master-data history, while UUID plus Location Name already provide current identity and finalized documents preserve independent transaction-time snapshots.
- **Supersedes:** The REVIEW status for `company_location_versions`, the open direct GST/Location-cardinality question, and the speculative nullable `location_code` in the current Location design.
- **Affected documents:** `requirements/database.md`; `requirements/COMPANY_CONFIGURATION.md`.
- **Implementation impact:** Documentation and database design only. No migration, model, SQL, seed data, API, frontend, test, or infrastructure work is authorized or completed.
- **Open follow-ups:** Physical Country/State reference representation and exact future-dated master/version synchronization mechanics remain open; no historical GST/Cost Center/purpose mapping design is introduced.

### CHG-2026-09-17-011 — Approve Company fiscal pattern and Financial Year design

- **Change ID:** CHG-2026-09-17-011
- **Date:** 2026-09-17
- **Status:** APPROVED
- **Area:** Company Configuration / Fiscal Setup / Database Design
- **Source / discussion context:** Approved Company fiscal-pattern and actual Financial-Year review.
- **Decision:** Confirm `company_fiscal_settings` and `financial_years` as KEEP. Separate the one current recurring start-month/day pattern from authoritative actual FY instances; prohibit same-Company overlap, retain explicit transition periods and Company-scoped unique display codes, and allow future-FY proposals without closing or locking prior years.
- **Reason:** Preserve stable historical period identity while supporting normal future-year setup and exceptional transition periods without conflating Financial Years with Accounting close or lock state.
- **Supersedes:** Optional Financial Year display-code wording and incomplete current constraints for fiscal-pattern changes, FY overlap, transition intent, and next-FY creation.
- **Affected documents:** `requirements/database.md`; `requirements/COMPANY_CONFIGURATION.md`.
- **Implementation impact:** Documentation and database design only. No migration, model, SQL, seed data, API, frontend, test, or infrastructure work is authorized or completed.
- **Open follow-ups:** Exact Financial Year lifecycle status values and exact next-FY timing/UI workflow remain open; Accounting-period closing and locking remain future Accounting scope.

### CHG-2026-09-17-012 — Approve Currency configuration design

- **Change ID:** CHG-2026-09-17-012
- **Date:** 2026-09-17
- **Status:** APPROVED
- **Area:** Company Configuration / Currency / Database Design
- **Source / discussion context:** Approved Currency master, additional Reporting Currency, and AR Billing/Receipt Currency review.
- **Decision:** Confirm `currencies`, `company_reporting_currencies`, and `company_ar_currencies` as KEEP with exact datatypes and constraints. Use canonical `VARCHAR(3)` Currency identity, a Company/Currency composite Reporting key, and a UUID-backed AR configuration with independent Billing/Receipt permissions and constrained active defaults.
- **Reason:** Keep shared Currency identity, management-reporting choices, and AR operational permissions distinct while preventing free text, redundant Base-Currency reporting rows, unusable active AR rows, and ambiguous defaults.
- **Supersedes:** Incomplete datatype/nullability documentation and underspecified keys, enablement checks, Base-Currency handling, and default uniqueness for the three Currency configuration tables.
- **Affected documents:** `requirements/database.md`; `requirements/COMPANY_CONFIGURATION.md`.
- **Implementation impact:** Documentation and database design only. No migration, model, SQL, seed data, API, frontend, test, or infrastructure work is authorized or completed.
- **Open follow-ups:** Exact Base-Currency AR-row setup automation remains an implementation workflow detail. Detailed FX selection, Receipt FX, rate precedence, and stale-rate rules remain outside this decision.

### CHG-2026-09-17-013 — Approve Bank Account, Exchange Rate, and FX Policy design

- **Change ID:** CHG-2026-09-17-013
- **Date:** 2026-09-17
- **Status:** APPROVED
- **Area:** Company Configuration / Bank Accounts / FX / Database Design
- **Source / discussion context:** Approved Company Bank Account, Exchange Rate, FX Policy, and Billing FX UI-reference review.
- **Decision:** Confirm `company_bank_accounts`, `exchange_rates`, and `fx_policies` as KEEP with exact physical definitions. Scope Billing-default Bank Accounts by Company + Currency; retain nullable direct Bank-to-GL mapping; define exact directional CORPORATE/SPOT rate facts; treat Billing's default Rate Type as preselection; and permit User Fixed only through policy plus user authorization. Remove/defer provisional `override_role`.
- **Reason:** Separate Currency choice, reusable FX facts, process defaults, and IAM authorization while preserving deterministic rate resolution, historical transaction truth, and Currency-specific settlement-account selection.
- **Supersedes:** Vague Bank/FX datatypes and constraints, a global-default Bank implication, ambiguity between reusable Rate Types and User Fixed, any forced-default Billing interpretation, and the provisional FX-policy role column.
- **Affected documents:** `requirements/database.md`; `requirements/COMPANY_CONFIGURATION.md`.
- **Implementation impact:** Documentation and database design only. No migration, model, SQL, seed data, API, frontend, test, binary UI asset, or infrastructure work is authorized or completed.
- **Open follow-ups:** Bank account-type vocabulary and duplicate-detection policy; detailed Receipt/Reporting FX selection, rate-date, stale-rate, and conversion behavior; exact IAM permission names; and provider-specific rate-source integration remain open.

### CHG-2026-09-17-014 — Freeze tax-reference and Company HSN/SAC schema

- **Change ID:** CHG-2026-09-17-014
- **Date:** 2026-09-17
- **Status:** APPROVED
- **Area:** Company Configuration / Tax Reference / Database Design
- **Source / discussion context:** Approved physical review of GST Registration Type, Tax Type, Company HSN/SAC, ordinary Tax Rates, Tax Treatments, and statutory COMPONENT/SECTION references and rates.
- **Decision:** Confirm all eight tax-reference/configuration tables as KEEP with exact PostgreSQL datatypes, nullability, keys, checks, lifecycle, and effective-period constraints. Move `gst_registration_types` beside Company GST Registration and keep the seven-table tax-reference block together. Separate ordinary item/supply `tax_rates` from effective statutory SECTION/case `tax_statutory_code_rates`; do not add `tax_rate_id` to statutory code rates.
- **Reason:** Preserve distinct statutory identities and deterministic effective-date validation without mixing GST item rates, HSN/SAC, treatments, components, or TDS/TCS section cases into a generic tax engine.
- **Supersedes:** Incomplete physical field definitions, the open enum-versus-table decision for GST Registration Type, and unclear ordinary-rate versus statutory-case-rate boundaries.
- **Affected documents:** `requirements/database.md`; `requirements/tax_satutory_rules.md`; `requirements/COMPANY_CONFIGURATION.md`.
- **Implementation impact:** Documentation and database design only. No migration, model, SQL, seed data, API, frontend, test, or infrastructure work is authorized or completed.
- **Open follow-ups:** Exact GST Registration Type values, canonical Country FK target, foreign tax-registration/classification abstraction, and advanced TDS/TCS thresholds, cumulative behavior, exemptions, certificates, and transaction calculation rules remain open/deferred.

### CHG-2026-09-17-015 — Freeze Company service and product catalogue schemas

- **Change ID:** CHG-2026-09-17-015
- **Date:** 2026-09-17
- **Status:** APPROVED
- **Area:** Company Configuration / Service and Product Catalogue / Database Design
- **Source / discussion context:** Approved physical review of Service Category, Service Type, Product Category, Product, and SKU, with a proposed Supply Type reference schema retained under REVIEW.
- **Decision:** Freeze exact PostgreSQL datatypes, nullability, defaults, Company-scoped uniqueness, lifecycle, same-Company relationships, SAC/HSN validation, eligible GST-rate and Treatment validation, direct optional Business Segment references, and TCS applicability-check semantics for the five KEEP catalogue tables. Document the proposed `supply_types` shape without promoting its table-versus-enum decision.
- **Reason:** Make catalogue persistence implementable and auditable while preserving current commercial hierarchy, Company ownership, tax-reference boundaries, and one-segment-per-item direction.
- **Supersedes:** Compact/vague catalogue column lists and undocumented Company-scoped uniqueness, nullability, default, and cross-reference validation details.
- **Affected documents:** `requirements/database.md`; `requirements/COMPANY_CONFIGURATION.md`.
- **Implementation impact:** Documentation and database design only. No migration, model, SQL, seed data, API, frontend, test, or infrastructure work is authorized or completed.
- **Open follow-ups:** `supply_types` table-versus-enum storage, platform-suggestion versus Company-adoption ownership, optional Service UOM use, and exact database mechanics for cross-Company protection remain open where not already established.

### CHG-2026-09-17-016 — Freeze Cost Center reporting-basis configuration

- **Change ID:** CHG-2026-09-17-016
- **Date:** 2026-09-17
- **Status:** APPROVED
- **Area:** Company Configuration / Cost Center Reporting / Database Design
- **Source / discussion context:** Approved refinement of the current Cost Center and management-reporting configuration design.
- **Decision:** Confirm Business Segment, Team, and Location as the three current Company-owned reporting bases. A Company may enable any supported combination through `company_cost_center_settings`, and the UI follows those settings. Retain the three bases as separate domain identities because Business Segments relate to Service Types/SKUs, Teams own effective-dated membership history, and Location Cost Centers group physical Company Locations. Freeze the exact physical definitions and constraints for the five KEEP tables without introducing a generic user-defined accounting-dimension engine.
- **Reason:** Make current reporting configuration implementable and Company-specific while preserving the distinct relationships and lifecycle of each supported basis.
- **Supersedes:** Current-MVP wording for a simple Custom Cost Center, category-level Business Segment assignment, and compact/vague physical definitions for the five Cost Center tables.
- **Affected documents:** `PRODUCT_OVERVIEW.md`; `requirements/COMPANY_CONFIGURATION.md`; `requirements/database.md`.
- **Implementation impact:** Documentation and database design only. No migration, model, SQL, seed data, API, frontend, test, or infrastructure work is authorized or completed.
- **Open follow-ups:** The physical user/IAM subject reference, exact database enforcement of one active Team membership per user within Company scope, and whether an enabled but incomplete Cost Center configuration draft may be saved remain OPEN. Department, Project, Region, arbitrary Company-defined reporting dimensions, and broader custom-dimension design remain DEFERRED.

### CHG-2026-09-17-017 — Freeze shared stored-file metadata persistence

- **Change ID:** CHG-2026-09-17-017
- **Date:** 2026-09-17
- **Status:** APPROVED
- **Area:** Core / Shared File Metadata / Database Design
- **Source / discussion context:** Verification of shared file/object metadata persistence before LUT, branding, and document-output table review.
- **Decision:** Add and KEEP `stored_files` as the canonical Company-scoped, provider-neutral metadata identity for externally stored binaries. PostgreSQL stores a stable UUID, immutable object key, content hash, MIME type, size, optional original filename, and creation time. Domain tables later reference that identity with typed FKs; no generic polymorphic attachment framework is introduced.
- **Reason:** Company assets, optional LUT evidence, final financial PDFs, explicit attachments, and export artifacts need one stable database identity that survives storage-provider changes without duplicating object metadata or persisting temporary URLs.
- **Supersedes:** Raw branding-reference strings and domain-specific storage-key/hash fields as a future canonical file identity. Existing downstream candidates remain subject to their own review and are not redesigned by this change.
- **Affected documents:** `requirements/database.md`; `requirements/COMPANY_CONFIGURATION.md`.
- **Implementation impact:** Documentation and database design only. No migration, model, SQL, API, frontend, test, storage adapter, seed data, or infrastructure work is authorized or completed.
- **Architecture alignment:** Cloudflare R2 remains the current provider behind `ObjectStorage`; binaries remain outside PostgreSQL; provider URLs/APIs are not domain identity; final financial PDFs remain immutable artifacts. No platform architecture decision changed.
- **Open follow-ups:** Exact retention periods, orphan cleanup, exceptional deletion/legal hold, canonical content-hash algorithm/encoding, and each consumer table's typed FK/lifecycle are resolved in their owning reviews.

### CHG-2026-09-17-018 — Freeze AR compliance, numbering, payment-term, and output configuration

- **Change ID:** CHG-2026-09-17-018
- **Date:** 2026-09-17
- **Status:** APPROVED
- **Area:** Company Configuration / AR Compliance / Numbering / Output / Database Design
- **Source / discussion context:** Approved documentation review of Tables 35–40 after the shared `stored_files` foundation was frozen, including the current LUT applicability correction for without-payment Export/SEZ routes.
- **Decision:** Confirm `company_luts`, `document_sequences`, `document_sequence_conditions`, `payment_terms`, `company_document_branding`, and `company_document_templates` as KEEP with explicit PostgreSQL datatypes, nullability, defaults, keys, constraints, lifecycle/history rules, and column purposes. LUT remains GST Registration + Financial Year specific and is required for current `EXPWOP` and `SEZWOP` routes; `EXPWP` and `SEZWP` are not blocked solely for missing LUT. LUT upload remains outside the MVP. Numbering keeps independent atomic counters and controlled applicability conditions without becoming a generic executable rules engine. Payment Terms keep at most one ACTIVE Company default and an inactive term cannot remain marked default. Branding references same-Company canonical `stored_files` identities, template configuration is versioned over server-side `template_key` values, and final rendered PDFs remain separate immutable artifacts.
- **Reason:** Make the six configuration tables implementable and historically safe while aligning LUT behavior with the current without-payment rule, preventing reuse/mutation of issued numbering context, reusing the approved provider-neutral file identity, and keeping unresolved rule-engine/template-selection choices explicitly open.
- **Supersedes:** Current blanket all-four Export/SEZ LUT wording in affected requirement/database sections and raw branding-reference placeholders for these tables. Historical changelog entries remain unchanged.
- **Affected documents:** `requirements/database.md`; `requirements/COMPANY_CONFIGURATION.md`; `requirements/tax_satutory_rules.md`; `requirements/billing_and_invoicing.md`; `CHANGELOG.md`.
- **Implementation impact:** Documentation and database design only. No migration, model, SQL, seed data, API, frontend, test, storage adapter, renderer, or infrastructure work is authorized or completed.
- **Open follow-ups:** Exact first-release numbering condition-type allow-list, operator vocabulary, multi-condition combination semantics, sequence priority semantics, current-template selection rule, and whether Stamp visibility needs its own `show_stamp` toggle versus template-controlled rendering remain OPEN. Advanced template-builder customization/version-management remains deferred.

