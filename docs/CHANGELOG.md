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

### CHG-2026-10-06-003 — Company Configuration Module Documentation Consolidation

- **Change ID:** CHG-2026-10-06-003
- **Date:** 2026-10-06
- **Status:** PROPOSED
- **Area:** Company Configuration / Documentation Governance
- **Source / discussion context:** Documentation-only consolidation requested for Phase 3C of the documentation folder architecture reorganization.
- **Previous design/assumption:** Company Configuration requirements, data-model inventory, workflow journey, business rules, and open decisions were maintained across separate requirement, architecture, database monolith, and reference ERD documents. `requirements/COMPANY_CONFIGURATION.md` and `skmc_company_config_erd.mmd` remained potential competing canonical sources.
- **New proposed decision:** Establish `docs/modules/company_configuration/` as the canonical Company Configuration documentation set containing `README.md`, `requirements.md`, `workflows.md`, `data_model.md`, `data_model.mmd`, `business_rules.md`, and `open_decisions.md`. Convert `requirements/COMPANY_CONFIGURATION.md` and `skmc_company_config_erd.mmd` to compatibility redirects, update module links in shared documentation, and preserve all current table structures and confirmed business rules.
- **Decision:** Consolidate documentation authority and navigation without changing Company Configuration business behavior, table count, proposed columns, lifecycle, or physical-design status.
- **Reason:** Provide one canonical reading order for Company Configuration, eliminate duplicate active authority, and keep confirmed, open, review, deferred, and historical material visibly separated.
- **Supersedes:** Independent canonical status of `requirements/COMPANY_CONFIGURATION.md` and `skmc_company_config_erd.mmd`. No earlier business or database-design decision is superseded by this documentation-only reorganization.
- **Affected documents:** `modules/company_configuration/README.md`; `modules/company_configuration/requirements.md`; `modules/company_configuration/workflows.md`; `modules/company_configuration/data_model.md`; `modules/company_configuration/data_model.mmd`; `modules/company_configuration/business_rules.md`; `modules/company_configuration/open_decisions.md`; `requirements/COMPANY_CONFIGURATION.md`; `skmc_company_config_erd.mmd`; `README.md`; `AR_MVP_ARCHITECTURE.md`; `CHANGELOG.md`.
- **Implementation impact:** Documentation/design only. No application code, migration, SQL, ORM model, API, service, route, frontend, test, or physical database change is authorized or performed.
- **Remaining open decisions:** Controlled tax-reference maintenance authority & foreign jurisdiction generalization; FX policy values & conversion selection rules; Team IAM membership enforcement; document numbering condition exact first-release condition/operator/combination/priority semantics; document output template selection rule & stamp visibility governance; stored-file retention/orphan-cleanup/legal-hold policy & canonical hash algorithm; Customer Code prefix validation, padding overflow behavior, and activation/approval gate; Service Catalogue platform suggestions vs Company adoption ownership boundary; incomplete draft Cost Center settings saved without a selected basis; `company_profile_versions` & `company_gst_registration_versions` necessity vs current projection.

### CHG-2026-10-06-002 — Customer Module Documentation Consolidation

- **Change ID:** CHG-2026-10-06-002
- **Date:** 2026-10-06
- **Status:** PROPOSED
- **Area:** Customer Onboarding / Documentation Governance
- **Source / discussion context:** Documentation-only consolidation requested after the Customer 14-table working design and request-history direction were reconciled.
- **Previous design/assumption:** Current Customer requirements, decision baseline, workflow rules, persistence design, and unresolved questions were distributed across separate requirement, architecture, shared approval/audit, database, and AR documents. The old requirement and architecture-baseline paths could still appear to be competing canonical Customer sources.
- **New proposed decision:** Establish `docs/modules/customer/` as the canonical Customer documentation set with a module overview, requirements, workflows, unchanged 14-table data model and Mermaid source, business rules, and open-decisions register. Convert the former requirement and architecture-baseline paths to compatibility redirects, retain the workflow-options document as prominently superseded history, and update only Customer-related links in shared consumers.
- **Decision:** Consolidate documentation authority and navigation without changing Customer business behavior, workflow states/actions, table count, proposed columns, lifecycle, or physical-design status.
- **Reason:** Give reviewers and future implementers one clear Customer reading path, eliminate duplicate active authority, and keep confirmed, open, review, deferred, and historical material visibly separated.
- **Supersedes:** Independent canonical status of `requirements/customer_onboarding.md` and `architecture/customer_onboarding_decision_baseline.md`; their current content is consolidated under `modules/customer/`. No earlier product or database-design decision is superseded by this documentation-only reorganization.
- **Affected documents:** `modules/customer/README.md`; `modules/customer/requirements.md`; `modules/customer/workflows.md`; `modules/customer/data_model.md`; `modules/customer/business_rules.md`; `modules/customer/open_decisions.md`; `requirements/customer_onboarding.md`; `architecture/customer_onboarding_decision_baseline.md`; `history/superseded/customer/customer_onboarding_workflow_options.md`; `README.md`; `architecture/module_boundaries.md`; `requirements/approval_and_audit`; `requirements/database.md`; `AR_MVP_ARCHITECTURE.md`; `CHANGELOG.md`.
- **Implementation impact:** Documentation/design only. No application code, migration, SQL, ORM model, API, service, route, frontend, test, or physical database change is authorized or performed.
- **Remaining open decisions:** Class A/B/C Customer-change control adoption and Class B classification; post-approval Contact change control; GST-to-Location mapping change control; Customer reactivation; and non-India statutory applicability. Credit Limit remains `DEFERRED`, not open.

### CHG-2026-10-06-001 — Customer 14-Table Master and JSONB Request-History Working Design

- **Change ID:** CHG-2026-10-06-001
- **Date:** 2026-10-06
- **Status:** PROPOSED
- **Area:** Customer Onboarding / Customer Master / Database Design / Approval / Company Configuration
- **Source / discussion context:** Explicit documentation-only request to record the latest agreed Customer Onboarding/Customer Master working design, reconcile older options, and keep the result proposed for freeze rather than implementation-final.
- **Previous design/assumption:** CHG-2026-10-03-004 retained a ten-table operational Customer proposal while leaving three mutually exclusive workflow persistence approaches, open-draft identifier claims versus revalidation, Customer Location versions, and Customer Code policy unresolved. It used the technical names `customer_communication_endpoints` and `customer_ar_communication_purpose_assignments` and stored the complete physical address on `customer_locations`.
- **New proposed decision:** Use one 14-table working design: eleven operational tables (`customer_organisations`, `customers`, `customer_identifiers`, `customer_gst_registrations`, stable `customer_locations`, effective-dated `customer_location_versions`, `customer_documents`, `customer_contacts`, friendly-named `customer_contact_details`, `customer_contact_roles`, and `customer_contact_purposes`) plus `customer_requests`, immutable JSONB `customer_request_snapshots`, and append-only `customer_request_actions`. Keep one authoritative server-side JSONB Draft on the Request; preserve exact request payloads at Submit/Resubmit and any Authority-approved changed result; do not use typed revision children, separate Drafts, identifier claims, or field-level review findings. Allow Draft overlap, validate duplicates on Submit and publish, and allow one open request per existing Customer. System-generate Customer Code during successful new-Customer publication from Company prefix plus a Company-scoped, start-at-1, non-resetting padded sequence.
- **Decision:** Adopt `CUSTOMER_ONBOARDING_ERD.md` as the canonical `CURRENT WORKING DESIGN / PROPOSED FOR FREEZE` documentation artifact. Mark the former workflow-options document and conflicting physical assumptions as superseded while retaining historical records. Do not treat this proposed freeze candidate as implementation approval.
- **Reason:** Preserve exact Maker/Authority request evidence with a simpler aggregate-specific JSONB history boundary, keep approved operational Customer data relational, align Customer Location history with stable identity/effective versions, and remove unselected workflow/claims complexity without introducing Party/Vendor/counterparty or generic workflow architecture.
- **Supersedes:** CHG-2026-10-03-004's active ten-table/workflow-alternatives/open-code/open-location design; CHG-2026-10-03-003's typed 15-table revision/claims design remains historical. It also supersedes CHG-2026-10-03-002 only where that entry assumed all post-approval Contact changes were direct operational edits; that policy is now `REVIEW`. Earlier ownership, Party boundary, Payment Term, Receivable GL, Bill-To/Ship-To, and transaction-snapshot decisions remain intact.
- **Affected documents:** `CUSTOMER_ONBOARDING_ERD.md`; `customer_onboarding_erd.mmd`; `CUSTOMER_ONBOARDING_WORKFLOW_OPTIONS.md`; `architecture/customer_onboarding_decision_baseline.md`; `architecture/moduleboundaries.md`; `requirements/customer_onboarding.md`; `requirements/approval_and_audit`; `requirements/COMPANY_CONFIGURATION.md`; `requirements/database.md`; `PRODUCT_OVERVIEW.md`; `AR_MVP_ARCHITECTURE.md`; `README.md`; `CHANGELOG.md`.
- **Implementation impact:** Documentation/design only. No migration, SQL, ORM model, API, route, service, frontend, test, worker, or physical database change is authorized or performed.
- **Remaining open decisions:** Customer reactivation; Class A/B/C adoption and Class B approval/direct-edit classification; post-approval Contact change control; GST-to-Location mapping change control; Contact recipient precedence/TO-CC-BCC/fallback/priority and verification/provider behavior; Customer Code prefix validation, padding overflow, readiness gate, and physical counter/locking/idempotency; shared identifier/geography/document-type reference alignment; supporting-document matrix and non-India rules; exact physical data types, constraints, and indexes.

### CHG-2026-10-03-001 — Customer Identity, Party Boundary, Organisation, and Location Baseline

- **Change ID:** CHG-2026-10-03-001
- **Date:** 2026-10-03
- **Status:** PROPOSED
- **Area:** Customer Onboarding / Domain / Architecture / Database Design
- **Source / discussion context:** Customer Onboarding pre-ERD decision reconciliation requested on 2026-10-03. This entry records planning decisions for review and does not mark them approved for implementation.
- **Previous design/assumption:** Customer identity and PAN/GSTIN uniqueness scope were TBD between Tenant and Company. Customer Organisation's meaning remained reviewable. Customer common/legal data had no explicit future Party boundary. Customer Locations mixed reusable physical sites with permanent Billing/Shipping flags, while Customer Location history was DEFER. Customer Code was described as assigned on approval without a frozen allocation policy.
- **New proposed decision:** Use Company-specific Customer ownership and Company-scoped PAN/GSTIN duplicate control across drafts and pending amendments. Keep optional external Customer Organisation distinct from seller-side `core.organisations`. Keep common/Party-like legal identity, statutory identity, Locations, Contacts, and endpoints physically Customer-owned for MVP without introducing shared Party/Vendor/Contact masters; preserve a future Party extraction/linking boundary. Treat Bill-To/Ship-To as transaction selections. Move Customer Location effective dating to `REVIEW` for alignment with the Company Location history model. Keep Customer Code policy `OPEN` / `DEFERRED` until format/allocation decisions are made.
- **Decision:** Establish the proposed Customer identity/Party/location baseline above; do not translate it into schema or APIs in this change.
- **Reason:** Remove conflicting ownership and address-role assumptions before ERD work while preserving a practical MVP and a clean future Party migration path without premature shared-domain abstractions.
- **Supersedes:** The unresolved Customer scope/uniqueness direction in `AR_MVP_ARCHITECTURE.md` and `requirements/database.md`; the permanent Customer Billing/Shipping Location-role assumption; and the blanket DEFER disposition for Customer Location history. Historical entries remain traceability records.
- **Affected documents:** `architecture/customer_onboarding_decision_baseline.md`; `architecture/moduleboundaries.md`; `requirements/customer_onboarding.md`; `requirements/database.md`; `PRODUCT_OVERVIEW.md`; `AR_MVP_ARCHITECTURE.md`; `README.md`; `CHANGELOG.md`.
- **Implementation impact:** Documentation/design only. Code, migrations, models, APIs, database constraints, and ERD work are explicitly prohibited in this change. Existing Customer `ADD` table sketches remain unapproved candidates.
- **Remaining open decisions:** Customer Code generation/manual-entry, format/prefix, Company configurability, counter scope, concurrency, and allocation timing; inactive Customer reactivation versus re-onboarding/replacement; Customer Location version-table need and physical contract; exact PAN/GSTIN normalization/reservation/concurrency mechanics; supporting-document matrix; non-India statutory rules; whether a DDR is required if the future Party boundary is later formally approved.

### CHG-2026-10-03-002 — Customer Communication, Credit-Period, Approval, and History Baseline

- **Change ID:** CHG-2026-10-03-002
- **Date:** 2026-10-03
- **Status:** PROPOSED
- **Area:** Customer Onboarding / AR Commercial / Approval / Audit / Delivery Boundary
- **Source / discussion context:** Customer Onboarding pre-ERD decision reconciliation requested on 2026-10-03. This entry records planning decisions for review and does not mark them approved for implementation.
- **Previous design/assumption:** Customer Contacts were person-shaped with inline email/phone, and Contact roles could implicitly drive invoice/reminder recipients. Customer default credit period was not clearly connected to Company Payment Terms. Customer approval allowed an ambiguous `Edit` action, with self-approval/materiality unresolved. Revision, effective version, transaction snapshot, and audit evidence were not consistently distinguished. Contact/email readiness was at risk of becoming a universal approval gate. Customer-level Receivable GL and Credit Limit boundaries were not consolidated in the Customer requirement.
- **New proposed decision:** Separate Customer-owned Contact identity (`PERSON`/`DEPARTMENT`/`GENERAL`), communication endpoints, Contact roles, and explicit AR communication-purpose assignments. Keep communication readiness separate from Customer approval and snapshot resolved recipients on delivery/reminder requests. Give Customer at most one optional same-Company Payment Term as Default Credit Period, fall back to the Company default, allow authorized transaction-specific term override with reason/audit, and snapshot finalized credit days/due date. Defer Credit Limit and keep Receivable GL Company-level. Use one Customer onboarding/amendment workflow with immutable submissions, maker/checker separation, material/non-material classification, and elevated audited successor-revision edit-and-approve. Use current master + audit + approval revisions + transaction snapshots, with selective effective dating only where justified.
- **Decision:** Establish the proposed Customer communication/commercial/approval/history baseline above; physical Contact endpoint/purpose structures and authorization contracts remain for the next design phase.
- **Reason:** Avoid conflating people, addresses, business roles, send authorization, reusable credit-period options, approval evidence, and historical truth while keeping the MVP simple and extensible.
- **Supersedes:** Person-only inline Contact assumptions; implicit role-to-recipient resolution; duplicate Customer credit-days direction; ambiguous Customer reviewer edit/self-approval behavior; and any interpretation that audit diffs replace approval revisions, effective versions, or transaction snapshots.
- **Affected documents:** `architecture/customer_onboarding_decision_baseline.md`; `architecture/moduleboundaries.md`; `requirements/customer_onboarding.md`; `requirements/approval_and_audit`; `requirements/COMPANY_CONFIGURATION.md`; `requirements/database.md`; `PRODUCT_OVERVIEW.md`; `AR_MVP_ARCHITECTURE.md`; `README.md`; `CHANGELOG.md`.
- **Implementation impact:** Documentation/design only. No code, migration, model, API, database, delivery worker, reminder engine, or authorization change is approved. The Customer ERD and API-contract phase remains a separate reviewed task.
- **Remaining open decisions:** Physical endpoint and purpose-assignment tables/cardinality/constraints; endpoint verification and WhatsApp-provider behavior; Customer delivery/reminder override precedence and merge/replace semantics; exact elevated Finance permission contract; Customer Code; inactive reactivation; Customer Location effective dating; supporting-document readiness matrix; Sales Order/AR Document edit-and-approve behavior.

### CHG-2026-10-03-004 — Customer Operational Master and Workflow Alternatives Reconciliation

- **Change ID:** CHG-2026-10-03-004
- **Date:** 2026-10-03
- **Status:** PROPOSED
- **Area:** Customer Onboarding / Database Design / Workflow / Legal Identity / History
- **Source / discussion context:** Latest Customer database/workflow reconciliation requested after review of the proposed 15-table Customer design. The request explicitly reopens workflow persistence, revisions, and identifier claims while retaining the agreed operational Customer concepts.
- **Previous design/assumption:** CHG-2026-10-03-003 proposed one 15-table core with direct `customers.pan`, immutable `customer_revisions` and typed revision children, revision-specific documents, `customer_identifier_claims`, approval submissions/decisions, `customers.published_revision_id`, and `latest_revision_no`. It hard-reserved PAN/GSTIN across drafts and treated that complete model as the current physical proposal.
- **New proposed decision:** Use a ten-table operational/live Customer proposal: `customer_organisations`, `customers`, generic `customer_identifiers`, `customer_gst_registrations`, complete-address `customer_locations`, `customer_documents` referencing `stored_files`, `customer_contacts`, `customer_communication_endpoints`, `customer_contact_roles`, and `customer_ar_communication_purpose_assignments`. Remove direct Customer PAN and unselected revision-pointer/counter columns from the operational core. Clarify that `default_payment_term_id` is the Customer default credit period between Company fallback and transaction prefill, not an “override” record.
- **Decision:** Move Customer workflow persistence back to `REVIEW` with three mutually exclusive alternatives: Request + Actions; Request + Submissions + Decisions; or Request + Actions + immutable Revisions and typed revision children. Move `customer_identifier_claims` to `REVIEW` against a simpler submit/approval revalidation option. Keep `customer_location_versions` under `REVIEW`. Review the existing Company-named legal-identifier type reference for generic Company/Customer use without authorizing a rename.
- **Reason:** The required workflow journey does not by itself prove a need for permanent complete-form revisions, formal submission/decision pairs, or hard reservation of every open draft. Separating the approved/current operational master from unresolved workflow/history choices prevents optional complexity from becoming an accidental requirement while still preserving the stronger options.
- **Supersedes:** The physical selection and fixed table count in CHG-2026-10-03-003; the hard-block-open-drafts implication in CHG-2026-10-03-001; and the mandatory approval-revision/successor-revision history mechanism in CHG-2026-10-03-002. It does not erase those historical proposals or supersede their Company ownership, Party boundary, Location-use, Contact-separation, Payment-Term, readiness, or lifecycle decisions.
- **Affected documents:** `CUSTOMER_ONBOARDING_ERD.md`; `CUSTOMER_ONBOARDING_WORKFLOW_OPTIONS.md`; `customer_onboarding_erd.mmd`; `requirements/database.md`; `requirements/customer_onboarding.md`; `architecture/customer_onboarding_decision_baseline.md`; `requirements/approval_and_audit`; `architecture/moduleboundaries.md`; `AR_MVP_ARCHITECTURE.md`; `PRODUCT_OVERVIEW.md`; `README.md`; `CHANGELOG.md`.
- **Implementation impact:** Documentation/design only. No SQL, migration, ORM model, API, route, service, frontend, test, or physical database change is authorized. API design remains deferred until the Customer database/workflow model is reviewed and frozen.
- **Remaining open decisions:** Customer Code generation/format/sequence/allocation; inactive Customer reactivation versus re-onboarding; selection of one workflow persistence approach; exact submitted-form reproduction requirement; open-draft identifier reservation versus submit/publish validation; Customer Location effective dating; shared legal-identifier type naming/applicability; recipient precedence and overrides; endpoint verification/WhatsApp behavior; supporting-document matrix and non-India statutory rules; Credit Limit.

### CHG-2026-10-03-003 — Customer Onboarding Logical ERD and Detailed Database Design

- **Change ID:** CHG-2026-10-03-003
- **Date:** 2026-10-03
- **Status:** PROPOSED
- **Area:** Customer Onboarding / Database Design / Approval / Historical Integrity
- **Source / discussion context:** Explicit request to proceed from the reconciled Customer baseline to logical ERD and detailed database design documentation only, while preserving all stated OPEN/REVIEW/DEFERRED boundaries and deferring APIs.
- **Previous design/assumption:** `requirements/database.md` contained nine pre-ERD Customer `ADD` sketches. They mixed stable/current state with onboarding drafts, had no typed Customer revision aggregate or revision child collections, used raw Customer document storage placeholders, lacked Company-scoped cross-draft identifier reservations, embedded Contact email/phone, and had no separate AR communication-purpose persistence.
- **New proposed decision:** Use a 15-table Customer core: stable/current Customer projections; immutable typed root/GST/Location/document revisions; Company-scoped PAN/GSTIN claims; Customer-owned typed Contacts, endpoints, roles, and separate AR purpose assignments; and revision-specific approval submissions/decisions. Approval publishes a submitted revision atomically without changing live values beforehand. Reuse Company, geography, GST Registration Type, Payment Term, stored-file, IAM-subject, and shared-audit contracts. Keep `customer_location_versions` as an explicit REVIEW alternative rather than part of the core.
- **Decision:** Adopt `CUSTOMER_ONBOARDING_ERD.md` and `customer_onboarding_erd.mmd` as the proposed Customer database-design review artifacts. Existing Section 15 Customer sketches in `requirements/database.md` become legacy comparison material and are classified `MODIFY`, `REPLACE`, `REVIEW`, or `DEFER` as applicable.
- **Reason:** Provide enforceable current-versus-pending isolation, immutable approval evidence, race-safe duplicate protection, typed relational history, and clean communication semantics without a shared Party master, generic workflow/version engine, generic attachment table, or authoritative JSON payload.
- **Supersedes:** The physical assumptions of the nine legacy Customer `ADD` sketches and their 9-table count. It does not supersede the business-status boundaries recorded by CHG-2026-10-03-001/002.
- **Affected documents:** `CUSTOMER_ONBOARDING_ERD.md`; `customer_onboarding_erd.mmd`; `requirements/database.md`; `architecture/customer_onboarding_decision_baseline.md`; `AR_MVP_ARCHITECTURE.md`; `README.md`; `CHANGELOG.md`.
- **Implementation impact:** Documentation/design only. No migration, SQL, ORM model, API, route, service, test, worker, frontend, or infrastructure work is authorized. API-contract design remains explicitly deferred until the database design is reviewed/frozen.
- **Remaining open decisions:** Customer Code allocation/format/uniqueness/counter; inactive Customer reactivation versus replacement; Customer Location version table alternative; delivery recipient precedence and Customer/document overrides; endpoint verification; supporting-document matrix; draft-abandonment claim-release authority; Customer inactivation approval route; GST checksum/PAN relationship; persistence enforcement mechanism for submitted-revision immutability; shared-audit approval/implementation.

### CHG-2026-09-29-002 — Company Activation Readiness and Legal Identifier Foundation

- **Change ID:** CHG-2026-09-29-002
- **Date:** 2026-09-29
- **Status:** IMPLEMENTED
- **Area:** Company Configuration / Legal Identity / AR Operational Readiness
- **Source / discussion context:** Explicit approval of the MVP Company Activation blocker set and the final `company_identifier_types.country_code` database decision.
- **Decision:** Company `ACTIVE` means operationally ready for the supported MVP AR/Billing workflow. Derive readiness from authoritative configuration and require Company identity, universal India-MVP PAN, REQUIRED Entity-Type identifier rules, a usable Registered Office, fiscal settings/current OPEN FY, usable active GST Registration/Location mapping, business-nature catalogue readiness, usable default Payment Term and billing Bank Account, current PI/TI/CN/DN numbering, and a usable active Company-wide document presentation. Implement the three approved generic identifier tables with `company_identifier_types.country_code` referencing `core.countries.code`; do not add PAN/CIN/LLPIN Company columns or seed an unapproved statutory matrix.
- **Reason:** Prevent activation before the normal MVP billing path is operational while retaining dynamic jurisdiction/entity applicability and avoiding stale readiness flags.
- **Supersedes:** The activation-minimum TBD in Company Configuration and proposed activation gate in `AR_MVP_ARCHITECTURE.md`; it finalizes the identifier-jurisdiction representation left open by CHG-2026-09-17-008. It does not supersede transaction-specific Billing finalization checks.
- **Affected documents:** `requirements/COMPANY_CONFIGURATION.md`; `requirements/database.md`; `requirements/billing_and_invoicing.md`; `PRODUCT_OVERVIEW.md`; `AR_MVP_ARCHITECTURE.md`; `CHANGELOG.md`.
- **Implementation impact:** Migration 0034 adds only `company_identifier_types`, `company_identifiers`, and `entity_type_identifier_rules`. A shared AR-owned evaluator serves readiness preview and locked activation; no readiness table or flag is stored. Accounting/CoA and GL mappings, Cost Centers, email, reminders, Team membership, LUT, and FX remain outside the universal activation gate.
- **Open follow-ups:** Platform provisioning of PAN/CIN/LLPIN reference rows and the approved Entity-Type rule matrix remains an operational reference-data decision; none is guessed or seeded here. Audit Trail is intentionally deferred for separate design after the Twenty study. Accounting readiness, LUT runtime enforcement, foreign-currency FX resolution, document number consumption, rendering, and Billing finalization remain separate slices.

### CHG-2026-09-29-001 — Catalogue Base GST Nature and Conditional GST Rate

- **Change ID:** CHG-2026-09-29-001
- **Date:** 2026-09-29
- **Status:** IMPLEMENTED
- **Area:** Company Configuration / Tax / AR Catalogue / Billing Direction
- **Source / discussion context:** Explicitly approved GST catalogue business decision for Service Types and SKUs.
- **Decision:** Rename catalogue `tax_treatment_id` to `base_tax_treatment_id` and restrict current Service Type/SKU use to active GST `TAXABLE`, `NIL_RATED`, `EXEMPT`, and `NON_GST` treatments in the matching jurisdiction. Make `selected_tax_rate_id` nullable: TAXABLE requires an active eligible GST rate, NIL_RATED requires an active eligible 0% GST rate, and EXEMPT/NON_GST require NULL. Base GST Nature is an item fact; `ZERO_RATED` is a transaction-context result that a future Billing resolver may derive from Supply Type and other transaction facts.
- **Reason:** Prevent catalogue configuration from representing a transaction's complete GST result, preserve the distinction between statutory nature and numeric rate, and avoid artificial 0% rates for exempt or non-GST items.
- **Supersedes:** CHG-2026-09-17-015 and CHG-2026-09-19-001 only where their catalogue Tax Treatment wording implied the final GST outcome or required a selected rate for every item. Their catalogue ownership, lifecycle, HSN/SAC, isolation, and other validation decisions remain unchanged.
- **Affected documents:** `requirements/tax_satutory_rules.md`; `requirements/COMPANY_CONFIGURATION.md`; `requirements/billing_and_invoicing.md`; `requirements/database.md`; `CHANGELOG.md`.
- **Implementation impact:** Migration 0033 preserves and renames existing treatment references, makes selected rates nullable, rejects unsafe existing data, and retains Tax Treatment/Tax Rate FKs under semantic constraint names. Catalogue models, schemas, services, responses, and focused tests use `base_tax_treatment_id` and validate the final nature/rate state. No Billing resolver, Supply Type redesign, or generic tax-rule engine is introduced.
- **Open follow-ups:** Implement the centralized Billing GST resolver and finalized invoice-line tax snapshots in a separately approved Billing slice. Future Service Type/SKU Excel sheets should use `Base GST Nature Code`, allow only the four approved catalogue values, and make Selected GST Rate conditional; this change does not expand the current Company import.

### CHG-2026-09-28-001 — Company Configuration GST Excel Import

- **Change ID:** CHG-2026-09-28-001
- **Date:** 2026-09-28
- **Status:** IMPLEMENTED
- **Area:** Company Configuration / GST Registration / Excel Import
- **Source / discussion context:** Approved Company Configuration Excel Import GST Registrations and GST Location Mappings implementation request.
- **Decision:** Extend the signed atomic Company Configuration import with `GST Registrations` and normalized `GST Location Mappings`. GSTIN is the create-or-compare import identity: duplicate workbook GSTINs are invalid, equivalent existing rows are unchanged, and differing existing rows conflict rather than update. Location mapping uses GSTIN plus immutable Company-scoped Location Code, is additive-only, never unmaps or reassigns by omission, and requires matching Company/State jurisdiction. `DRAFT` and `ACTIVE` registrations may receive new assignments; `INACTIVE` registrations may retain existing associations but cannot receive new ones. Same-workbook new Locations must supply a Location Code when referenced by mappings.
- **Reason:** Support tenant-safe bulk GST onboarding and normalized Location association without exposing UUIDs, turning Excel into a GST maintenance interface, or weakening lifecycle and jurisdiction controls.
- **Supersedes:** The GST-import and Location-association follow-up in CHG-2026-09-27-001; it does not change GST Registration history, activation, default Location, LUT, Billing, or statutory-validation scope.
- **Affected documents:** `requirements/COMPANY_CONFIGURATION.md`; `requirements/database.md`; `CHANGELOG.md`.
- **Implementation impact:** Extends the existing workbook parser, signed preview state, stale-state fingerprint, and caller-owned atomic apply; adds transaction-aware GST creation, central inactive-GST Location-assignment protection, and focused unit/PostgreSQL tests. No migration is added and Alembic head remains 0032.
- **Open follow-ups:** GST Registration history/versioning, checksum/portal/PAN validation, Registration Type reference provisioning, default/principal/additional-place concepts, mapping history/unmapping/reassignment, LUT import, and later tax/Billing imports remain separate work.

### CHG-2026-09-27-001 — Company Configuration Financial Year and Location Excel Import

- **Change ID:** CHG-2026-09-27-001
- **Date:** 2026-09-27
- **Status:** IMPLEMENTED
- **Area:** Company Configuration / Location Identity / Excel Import
- **Source / discussion context:** Approved Company Configuration Excel Import V1 Financial Years and Locations implementation request.
- **Decision:** Add immutable, Company-scoped `location_code` as the stable Location business/reference identity while retaining UUID relational identity and mutable, non-unique Location Name. Normalize supplied codes to uppercase with the approved 1-50 character format; generate omitted codes through a concurrency-safe Company counter as `LOC-0001`, `LOC-0002`, and so on; retain codes after inactivation and prohibit reuse. Extend the signed Company Configuration workbook preview/apply flow to `Financial Years` and `Locations`, with deterministic matching, Location address-history service reuse, and one atomic apply transaction.
- **Reason:** Enable rename-safe and idempotent Location import without exposing UUIDs, while importing deterministic normal Financial Years and preserving existing lifecycle, overlap, geography, history, and Tenant boundaries.
- **Supersedes:** CHG-2026-09-17-010 only for its deferred/no-Location-Code direction. Its stable UUID, narrow address-history, and finalized-document snapshot decisions remain unchanged.
- **Affected documents:** `requirements/COMPANY_CONFIGURATION.md`; `requirements/database.md`; `CHANGELOG.md`.
- **Implementation impact:** Adds Migration 0032, Location Code model/API behavior, Company-scoped generation and backfill, multi-sheet import parsing and preview classifications, signed normalized state, caller-owned atomic apply, and focused unit/PostgreSQL tests.
- **Open follow-ups:** Transition Financial Year import, GST Registration import and Location association, and workbook export/template retention of generated Location Codes remain separate work.

### CHG-2026-09-25-002 — Company Configuration Validation Hardening Batch 2 (UOM & Bank Accounts)

- **Change ID:** CHG-2026-09-25-002
- **Date:** 2026-09-25
- **Status:** IMPLEMENTED
- **Area:** Company Configuration / Validation Hardening / UOM Master & Bank Account Validation
- **Source / discussion context:** TASK: COMPANY CONFIGURATION — VALIDATION HARDENING BATCH 2 (UOM Master + Bank Account Validation).
- **Decision:** Implement a global shared UOM master (`core.uoms`) serving both Goods and Services. SKUs require a mandatory controlled UOM reference; Service Types support an optional controlled UOM reference. Service Types and SKUs reference stable UOM codes (e.g. `NOS`, `KGS`, `MTR`, `HRS`, `DAY`, `SET`, `JOB`). Upgrade Company Bank Accounts to store explicit `bank_country_code` referencing `core.countries.code`. Enforce structural India IFSC validation (`^[A-Z]{4}0[A-Z0-9]{6}$`) when `bank_country_code == 'IN'`. Add structural validation for optional SWIFT/BIC (ISO 9362) and optional IBAN (ISO 7064 Modulo 97 checksum via `python-stdnum`). Restrict `account_type` to controlled vocabulary (`CURRENT`, `SAVINGS`, `OVERDRAFT`, `CASH_CREDIT`, `MONEY_MARKET`, `OTHER`).
- **Reason:** Standardize UOM references across SKUs and Service Types, enforce country-aware bank account jurisdiction, restrict account types to approved vocabulary, and validate international SWIFT/IBAN structure without live network lookups or over-engineering.
- **Supersedes:** CHG-2026-09-25-001 for deferred UOM and Bank Account validation follow-ups.
- **Affected documents:** `requirements/COMPANY_CONFIGURATION.md`; `CHANGELOG.md`.
- **Implementation impact:** Adds `python-stdnum` dependency, `core.uom` model/schema/service, Migration 0031, UOM master seed data, ServiceType/SKU UOM foreign keys and service validation, `bank_country_code` column, bank account structural validators, and updated tests.
- **Open follow-ups:** Reminder range policies and advanced document numbering remain deferred.

### CHG-2026-09-25-001 — Company Configuration Validation Hardening Batch 1

- **Change ID:** CHG-2026-09-25-001
- **Date:** 2026-09-25
- **Status:** IMPLEMENTED
- **Area:** Company Configuration / Validation Hardening / Core Geography & Compliance
- **Source / discussion context:** TASK: COMPANY CONFIGURATION — VALIDATION HARDENING BATCH 1 (Email, Website, International Phone, LUT Clarification, Deferred Decisions).
- **Decision:** Apply real email syntax validation to Company Create/Update using a shared `core.email.validator` module (reused in AR invoice delivery). Apply URL structure validation requiring `http` or `https` schemes to Company website Create/Update. Implement international phone parsing and E.164 canonical normalization using `phonenumbers` for Company phone Create/Update, utilizing Company `country_code` as default region context when unambiguous. Add nullable `calling_code` metadata to `core.countries` reference master with migration 0031 without unique constraints. Clarify LUT reference validation to enforce non-blank whitespace-trimmed string up to 100 characters while preserving non-ARN business references. Record deferred validation decisions for UOM and Bank Account validation.
- **Reason:** Prevent invalid contact/website formatting, normalize international phone numbers to E.164 standard, support country calling code metadata, and align LUT validation with governing product specs without over-constraining references or adding premature module complexity.
- **Supersedes:** None.
- **Affected documents:** `requirements/COMPANY_CONFIGURATION.md`; `CHANGELOG.md`.
- **Implementation impact:** Adds `phonenumbers` dependency, `core.email.validator`, Migration 0031, Country `calling_code` field/constraint, Company email/website/phone schema validators, LUT reference whitespace/non-blank validation, and updated documentation.
- **Open follow-ups:** UOM master vocabulary design, country-aware Bank Account validation, and reminder range policies remain deferred.

### CHG-2026-09-24-002 — Final Goods Hierarchy Lifecycle and Company Legal-Name History

- **Change ID:** CHG-2026-09-24-002
- **Date:** 2026-09-24
- **Status:** IMPLEMENTED
- **Area:** Company Configuration / Goods Catalogue Lifecycle / Company Identity History
- **Source / discussion context:** Company Configuration Final Closure 2 before Excel Bulk Import.
- **Decision:** Product Category → Product → SKU uses terminal inactivation and replacement rather than re-parenting. A Product Category cannot be inactivated while active Products reference it, and a Product cannot be inactivated while active SKUs reference it; inactive children remain readable and do not block later parent inactivation. Numbering condition and runtime-selection semantics remain deferred to Billing. Company legal-name changes preserve the stable Company identity and current `companies.legal_name` projection while a dedicated effective-dated `company_legal_name_versions` structure preserves non-overlapping chronological history.
- **Reason:** Close the remaining goods-hierarchy lifecycle decisions without rewriting historical references, and preserve Company legal-name history with the narrowest approved persistence structure while keeping unresolved Billing numbering behavior outside Company Configuration.
- **Supersedes:** CHG-2026-09-24-001 only for its open Product/Product Category lifecycle, Product/SKU parent-reassignment, and Company legal-name-history follow-ups. It does not change G1 Location versioning, G2 document presentation, or G3 Revenue GL behavior.
- **Affected documents:** `requirements/COMPANY_CONFIGURATION.md`; `requirements/database.md`; `CHANGELOG.md`.
- **Implementation impact:** Adds Migration 0030, the Company legal-name-version ORM and tenant-scoped history read API, atomic create/change history maintenance, terminal Product Category/Product lifecycle operations, inactive mutation guards, and focused tests.
- **Open follow-ups:** Final-number allocation, numbering-condition vocabulary/operators/combination/priority/conflict resolution, and runtime counter concurrency remain deferred to Billing/finalization. Future-dated or backdated Company legal-name scheduling/correction and generic Company profile versioning are not implemented.

### CHG-2026-09-24-001 — Company Configuration Closure and Document Numbering Persistence

- **Change ID:** CHG-2026-09-24-001
- **Date:** 2026-09-24
- **Status:** IMPLEMENTED
- **Area:** Company Configuration / Lifecycle Closure / AR Document Numbering
- **Source / discussion context:** Final Company Configuration closure before Excel Bulk Import.
- **Decision:** Permit current Company legal-name maintenance while preserving stable Company identity; add controlled terminal Company inactivation from `ACTIVE`; make HSN/SAC replacement inactivation terminal; add guarded Service Category inactivation after active Service Types are retired; add terminal inactivation and inactive-mutation guards for the approved Cost Center masters and actual Teams; and prevent mutation/reassignment of inactive GST Registrations, Service Types, SKUs, GL Accounts, and Account Groups. Cost Center master codes remain immutable stable business-reference/import keys. Implement the already-frozen `document_sequences` and `document_sequence_conditions` persistence contract plus a narrow series create/read/inactivate API.
- **Reason:** Close inconsistent mutable-inactive behavior, preserve historical master references without cascades or automatic remapping, and persist approved numbering configuration before bulk-import work without implementing Billing-time allocation.
- **Supersedes:** CHG-2026-09-22-003 only for Company legal-name mutation and `ACTIVE` to `INACTIVE` lifecycle; CHG-2026-09-22-004 only for Service Category lifecycle and terminal inactive leaf mutation guards; CHG-2026-09-22-005 only for Cost Center master lifecycle and code-mutability follow-ups. G1, G2, and G3 behavior is unchanged.
- **Affected documents:** `requirements/COMPANY_CONFIGURATION.md`; `CHANGELOG.md`.
- **Implementation impact:** Adds Migration 0029, AR numbering models and series configuration API, controlled Company/HSN-SAC/Service Category/Cost Center lifecycle operations, inactive-master guards, and focused model/API/migration tests.
- **Open follow-ups:** `company_profile_versions` remains REVIEW, so this batch does not invent legal-name version persistence. Product/Product Category lifecycle and Product/SKU parent reassignment remain unresolved and unchanged. Numbering condition type/operator/combination/priority semantics and runtime allocation remain OPEN; therefore no condition-write API or PI/TI/CN/DN allocation is implemented.

### CHG-2026-09-22-008 — Revenue GL Mapping Enhancement and Deterministic Resolution (Batch G3)

- **Change ID:** CHG-2026-09-22-008
- **Date:** 2026-09-22
- **Status:** IMPLEMENTED
- **Area:** Company Configuration / Revenue GL Mapping / Database and Application Layer
- **Source / discussion context:** Revenue GL Mapping Enhancement and Deterministic Resolution Batch G3 prompt request.
- **Decision:** Revenue GL determination is item-based. Each mapping specifies exactly one of Service Type or SKU (enforced via CHECK constraint `ck_revenue_gl_mappings_exactly_one_item`), optional Supply Type (`supply_type_code`), optional Company Location (`company_location_id`, referencing stable Location ID), GL Account (`gl_account_id`), effective date range (`valid_from` / `valid_to`), and status (`ACTIVE` / `INACTIVE`). HSN/SAC is dropped from Revenue GL mappings (`company_hsn_sac_code_id` removed). Deterministic resolution uses fixed precedence: `Item + Supply + Location` > `Item + Supply` > `Item + Location` > `Item only`. Supply Type beats Location. No cross-item fallback occurs between Service Type and SKU. Overlapping identical criteria tuples are prohibited via GIST exclusion constraints. Equivocal matches at the same tier raise `RevenueGlMappingAmbiguityError`. End and inactivate operations preserve history; no DELETE or generic criteria PATCH endpoints exist.
- **Reason:** Complete the item-based Revenue GL configuration and deterministic resolution engine required for Company Configuration without altering Tax GL behavior, introducing arbitrary priority columns, or implementing invoice creation/journal posting runtime.
- **Supersedes:** The older HSN/SAC-based Revenue GL wording in `requirements/database.md` and `requirements/COMPANY_CONFIGURATION.md`, and resolves the deferred Revenue GL WRITE follow-up in CHG-2026-09-21-003.
- **Affected documents:** `requirements/COMPANY_CONFIGURATION.md`; `requirements/database.md`; `CHANGELOG.md`.
- **Implementation impact:** Adds Migration 0028 (`0028_revenue_gl_mapping_enhancement`), updates ORM model, schema, service, router, resolver, and comprehensive migration/API/resolver tests. Alembic head advances to `0028_revenue_gl_mapping_enhancement`.
- **Open follow-ups:** Transaction billing runtime, invoice creation, proforma/tax invoice generation, tax engine integration, and journal posting remain deferred for future batches.

### CHG-2026-09-22-001 — Company Operational Configuration Application Layer (Batch D)

- **Change ID:** CHG-2026-09-22-001
- **Date:** 2026-09-22
- **Status:** IMPLEMENTED
- **Area:** Company Configuration / Application Layer
- **Source / discussion context:** Company Operational Configuration and Policy Defaults Batch D implementation request.
- **Decision:** Implement tenant-scoped application operations for invoice-delivery settings, exchange-rate facts, Company FX policies, reminder policies and reminder schedule rules, plus the unambiguous Company document-template history list. Do not implement public Email Provider Configuration CRUD, runtime delivery/reminder/FX behavior, or document rendering. Do not implement current-branding upsert or current-template selection/activation while the governing selection multiplicity remains OPEN.
- **Reason:** Deliver the approved configuration application layer while preserving effective history, Company isolation, provider-secret boundaries, and explicit unresolved document-presentation decisions.
- **Supersedes:** None.
- **Affected documents:** `requirements/COMPANY_CONFIGURATION.md`; `requirements/database.md`; `CHANGELOG.md`.
- **Implementation impact:** Adds schemas, services, routers, and tests only. No migration or persistence-contract change is introduced; Alembic head remains `0025_company_access_foundation`.
- **Open follow-ups:** Approve whether branding has one current row and whether each Company/document type has exactly one current template or multiple active choices, then separately approve the corresponding controlled mutation and current-selection APIs.

### CHG-2026-09-22-002 — Statutory and Tax Configuration Application Layer (Batch E)

- **Change ID:** CHG-2026-09-22-002
- **Date:** 2026-09-22
- **Status:** IMPLEMENTED
- **Area:** Company Configuration / Statutory and Tax Application Layer
- **Source / discussion context:** Statutory and Tax Configuration Batch E implementation request.
- **Decision:** Implement tenant-scoped HSN/SAC code maintenance, effective HSN/SAC-to-GST-rate history, Financial Year reads and forward-only lifecycle, and GST Registration reads, approved mutable-field maintenance, and forward-only lifecycle. Stable HSN/SAC identity, GSTIN, and GST subdivision remain immutable through these APIs; effective history is ended or inactivated rather than deleted.
- **Reason:** Complete the approved application operations over existing migrations 0006–0008 without changing persistence or introducing tax calculation, tax determination, transaction, or posting behavior.
- **Supersedes:** None.
- **Affected documents:** `requirements/COMPANY_CONFIGURATION.md`; `requirements/database.md`; `requirements/tax_satutory_rules.md`; `CHANGELOG.md`.
- **Implementation impact:** Adds and extends schemas, services, routers, and PostgreSQL integration tests. No migration or model change is introduced; Alembic head remains `0025_company_access_foundation`.
- **Open follow-ups:** GST checksum/portal verification, tax calculation/determination, statutory publication authority, Company activation, transaction snapshots, and all Batch F work remain separately governed or deferred.

### CHG-2026-09-22-003 — Company and Location Maintenance Application Layer (Batch F1)

- **Change ID:** CHG-2026-09-22-003
- **Date:** 2026-09-22
- **Status:** IMPLEMENTED
- **Area:** Company Configuration / Company and Location Application Layer
- **Source / discussion context:** Company and Company Location Maintenance Batch F1 implementation request.
- **Decision:** Implement Tenant-scoped Company list/get and narrow ordinary-profile maintenance, plus Company-scoped Location list/get, current-row maintenance, nullable same-Company/same-jurisdiction GST Registration assignment, and controlled inactivation. Company legal name, controlled identity fields, Company lifecycle, Location reactivation, and Location Cost Center assignment remain unavailable through these maintenance APIs.
- **Reason:** Deliver approved Company and Location maintenance over the existing persistence contract while preserving concealed Tenant/Company boundaries, fixed-purpose validation, Registered Office uniqueness without automatic switching, restrictive lifecycle behavior, and explicit unresolved transition/history decisions.
- **Supersedes:** None.
- **Affected documents:** `requirements/COMPANY_CONFIGURATION.md`; `requirements/database.md`; `CHANGELOG.md`.
- **Implementation impact:** Extends existing Company and Company Location schemas, services, routers, and tests only. No migration or ORM model change is introduced; Alembic head remains `0025_company_access_foundation`.
- **Open follow-ups:** Approve Company activation/reactivation/inactivation consequences, Company legal-profile history persistence, Location reactivation, Location address-version persistence/synchronization, and any direct Location Cost Center maintenance before implementing those operations.

### CHG-2026-09-22-004 — Service and Product Catalogue Maintenance Application Layer (Batch F2)

- **Change ID:** CHG-2026-09-22-004
- **Date:** 2026-09-22
- **Status:** IMPLEMENTED
- **Area:** Company Configuration / AR Catalogue Application Layer
- **Source / discussion context:** Service and Product Catalogue Maintenance Batch F2 implementation request.
- **Decision:** Implement Tenant- and Company-scoped list/get operations for Service Categories, Service Types, Product Categories, Products, and SKUs; narrowly allow current business-facing name/description/UOM maintenance; allow Service Type SAC and SKU HSN plus selected eligible GST Rate, Tax Treatment, and TCS-check maintenance through the established complete tax-validation contract; and allow controlled inactivation only for leaf Service Types and SKUs. Business codes, parent reassignment, Business Segment assignment, parent lifecycle, reactivation, and generic status PATCH remain unavailable.
- **Reason:** Complete safe catalogue maintenance over the existing Migration 0009/0010 persistence while preserving stable operational identities, Company ownership, HSN/SAC kind rules, eligible-rate integrity, historical references, and unresolved hierarchy lifecycle semantics.
- **Supersedes:** None.
- **Affected documents:** `requirements/COMPANY_CONFIGURATION.md`; `requirements/database.md`; `CHANGELOG.md`.
- **Implementation impact:** Extends existing AR catalogue schemas, services, routers, and tests only. No migration or ORM model change is introduced; Alembic head remains `0025_company_access_foundation`.
- **Open follow-ups:** Catalogue code-change policy, Service Type/Product/SKU parent reassignment, parent inactivation consequences, all catalogue reactivation behavior, and direct Business Segment assignment/reassignment remain separately governed; Business Segment maintenance belongs to Batch F3.

### CHG-2026-09-22-005 — Cost Center Configuration Application Layer (Batch F3)

- **Change ID:** CHG-2026-09-22-005
- **Date:** 2026-09-22
- **Status:** IMPLEMENTED
- **Area:** Company Configuration / Cost Center Application Layer
- **Source / discussion context:** Cost Center Configuration and Dimension Assignments Batch F3 implementation request.
- **Decision:** Implement Tenant- and Company-scoped settings reads; list/get and name-only maintenance for Business Segments, Cost Center Team reporting buckets, and Location Cost Centers; and explicit current-state assign/reassign/unassign operations for Service Type/SKU to Business Segment, actual Team to Cost Center Team, and Company Location to Location Cost Center. Assignments use the existing nullable same-Company FKs and require an active target without creating mapping or history tables.
- **Reason:** Complete the approved management-reporting configuration application layer while preserving independent reporting bases, optional coverage, direct one-to-many cardinality, Company ownership, and separation from Account Determination.
- **Supersedes:** None.
- **Affected documents:** `requirements/COMPANY_CONFIGURATION.md`; `requirements/database.md`; `CHANGELOG.md`.
- **Implementation impact:** Extends existing schemas, services, routers, and tests only. No migration or ORM model change is introduced; Alembic head remains `0025_company_access_foundation`.
- **Open follow-ups:** Code mutability, master lifecycle-transition consequences, assignment history/effective dating, and the enabled-but-incomplete settings draft rule remain unresolved. Those behaviors are not exposed; existing settings disablement changes flags only and does not clear assignments or delete masters.

### CHG-2026-09-22-006 — Location Address Versioning and Terminal Lifecycle (Batch G1)

- **Change ID:** CHG-2026-09-22-006
- **Date:** 2026-09-22
- **Status:** IMPLEMENTED
- **Area:** Company Configuration / Company Location / Database and Application Layer
- **Source / discussion context:** Location Address Versioning and Terminal Location Lifecycle Batch G1 implementation request.
- **Decision:** Implement effective-dated address/jurisdiction versions for each stable Company Location while retaining the current address columns as the operational projection. New Locations atomically receive an initial version from the application business date; real address changes atomically close the current version on the preceding date, create the new open version, and update the projection. Existing Locations are technically backfilled from their creation timestamp date. Future-dated scheduling and backdated correction workflows are not part of MVP. Location lifecycle is terminal `ACTIVE` -> `INACTIVE`, and inactive Locations cannot be reactivated, edited, or reassigned.
- **Reason:** Preserve master-data address history without changing Location identity or reconstructing finalized-document truth from mutable current configuration.
- **Supersedes:** The future-dated-version direction and synchronization follow-up in CHG-2026-09-17-010, and the Location address-version/reactivation follow-ups in CHG-2026-09-22-003, only for this explicitly approved MVP scope.
- **Affected documents:** `requirements/COMPANY_CONFIGURATION.md`; `requirements/database.md`; `CHANGELOG.md`.
- **Implementation impact:** Adds Migration 0026, the Core Location Version ORM model, atomic create/update integration, tenant/company-scoped address-history reads, terminal-inactive mutation guards, and focused PostgreSQL/model/API tests.
- **Open follow-ups:** No pre-versioning address history can be reconstructed. Finalized-document address snapshots, Audit attribution, and any future scheduling/backdated-correction capability remain separate work.

### CHG-2026-09-22-007 — Company-Wide Billing Document Template and Branding History (Batch G2)

- **Change ID:** CHG-2026-09-22-007
- **Date:** 2026-09-22
- **Status:** IMPLEMENTED
- **Area:** Company Configuration / Document Presentation / Database and Application Layer
- **Source / discussion context:** Company-Wide Billing Document Template and Branding Alignment Batch G2 implementation request.
- **Decision:** A Company selects one current code-owned billing-document template for PI, TI, CN, and DN, rather than selecting by document type or on every document. Template and branding changes create immutable history rows; at most one selection and one branding row are current per Company. Branding stays separate from layout and references same-Company `stored_files`. Legacy `document_type` and `show_*` columns remain nullable, non-governing persistence only and are not exposed through the MVP API.
- **Reason:** Align the existing Migration 0022 structure with the clarified MVP cardinality while retaining useful historical identities and avoiding invented migration winners or destructive rewrites.
- **Supersedes:** The Company/document-type selection direction and OPEN current-selection multiplicity in CHG-2026-09-17-018, plus the document-presentation follow-up in CHG-2026-09-22-001, only for the explicitly approved Batch G2 scope.
- **Affected documents:** `requirements/COMPANY_CONFIGURATION.md`; `requirements/database.md`; `CHANGELOG.md`.
- **Implementation impact:** Adds Migration 0027, a small code-owned template registry, Company-wide current/history template APIs, immutable current/history branding APIs, same-Company stored-file validation, ORM alignment, and focused model/schema/PostgreSQL tests. Existing conflicting active rows are retired without selecting a winner.
- **Open follow-ups:** PDF rendering, PI/TI/CN/DN persistence and generation, finalized-document snapshots/artifacts, object-storage upload integration, and any future presentation customization remain separate work.

### CHG-2026-09-21-003 — AR Accounting Mappings & Company LUT Application Layer (Batch C)

- **Change ID:** CHG-2026-09-21-003
- **Date:** 2026-09-21
- **Status:** IMPLEMENTED
- **Area:** Architecture / Product
- **Source / discussion context:** Company Configuration Application Layer - Batch C Implementation Request.
- **Decision:** Implemented controlled business operations for Revenue GL Mapping, Tax GL Mapping, and Company LUT. Revenue GL Mapping WRITE operations were explicitly blocked/deferred because the `supply_type_code` allowed-value source is unresolved. Tax GL Mapping allows both `COMPONENT` and `SECTION` codes with guaranteed overlap prevention using GIST rules and `valid_from / valid_to` continuity. Company LUT creation enforces uniqueness constraints across GST Registration and Financial Year; inactivation and activation operations support lifecycle toggles without generic updates. Multi-tenant access controls pass `Tenant` object downwards, replacing manual contextual resolution.
- **Reason:** Fulfilled missing application layer requirements for Batch C configuration areas, strictly avoiding inference of unresolved business rules.
- **Supersedes:** None
- **Affected documents:** docs/requirements/COMPANY_CONFIGURATION.md, docs/requirements/tax_statutory_rules.md, docs/requirements/database.md
- **Implementation impact:** Implemented schemas, services, routers, and tests. Post-Batch-C test baseline verified and successful.
- **Open follow-ups:** Revenue GL Mapping WRITE operations remain deferred pending the approved `supply_type_code` vocabulary and storage decision.

### CHG-2026-09-21-002 — Accounting Structure Application Layer (Batch B)

- **Change ID:** CHG-2026-09-21-002
- **Date:** 2026-09-21
- **Status:** IMPLEMENTED
- **Area:** Architecture
- **Source / discussion context:** Company Configuration Application Layer - Batch B Implementation Request.
- **Decision:** Implemented controlled business operations for primary accounting hierarchies, group reparenting, and GL mapping. Explicitly rejected generic CRUD endpoints. Deferred deep-cycle prevention as it requires an unapproved design; fallback to `ck_account_group_relationships_not_self_parent` constraint. Implemented `old.valid_to = new.valid_from - 1 day` effective-date logic. Protected inactivation of account groups containing active child groups or GL account placements.
- **Reason:** Fulfilled missing application layer requirements for Batch B configuration areas following the strict DB constraints and architecture rules.
- **Supersedes:** None
- **Affected documents:** docs/requirements/COMPANY_CONFIGURATION.md, docs/requirements/database.md
- **Implementation impact:** Implemented schemas, services, routers, and tests. Post-Batch-B test baseline verified.
- **Open follow-ups:** Deep-cycle prevention logic is explicitly deferred for FUTURE.

## Baseline Established — 2026-09-17

All product, architecture, requirement, database-design, reference, and historical documentation that existed before this governance setup is treated as the imported documentation baseline. Importing the baseline does not promote every statement to approval: each document and statement retains its own FINAL, CONFIRMED, MVP, PROPOSED, KEEP, ADD, REVIEW, TBD, CONFIGURE, DIRECTION, DEFERRED, POST-MVP, FUTURE, or historical status.

This log does not attempt to reconstruct every prior discussion or Git event. Future meaningful proposed or approved product/design changes must receive a new change ID and must identify any superseded direction.

### CHG-2026-09-21-003 — Freeze Tax Statutory Code persistence details

- **Change ID:** CHG-2026-09-21-003
- **Date:** 2026-09-21
- **Status:** APPROVED
- **Area:** Company Configuration / Tax Reference / Database Design
- **Source / discussion context:** Explicit approval resolving the final physical-contract questions identified by the proposed Migration 0019 readiness audit.
- **Decision:** Tax Statutory Code code and name require database nonblank checks, and a supplied nullable rate `case_code` requires the same check without automatic trimming or case normalization. `country_code` is `VARCHAR(2) NOT NULL`, must match exactly two uppercase ASCII letters, and has no Country-master FK. Rate rows reference only the parent Tax Statutory Code ID: SECTION is the primary current use, but persistence does not restrict the parent kind or prohibit COMPONENT-linked rates. Active inclusive named-case and default-case periods use separate partial GiST exclusion constraints, with null representing the default logical case and no sentinel value.
- **Reason:** Freeze deterministic, database-enforced input and effective-period invariants while avoiding an unapproved Country relationship, parent-kind restriction, or runtime tax policy.
- **Supersedes:** The open Countries-table FK wording and unresolved overlap-mechanics wording in `requirements/database.md`, and the canonical-Country-FK follow-up in CHG-2026-09-17-014 for these tables. It clarifies, without changing, the approved ordinary-rate/statutory-rate separation.
- **Affected documents:** `requirements/COMPANY_CONFIGURATION.md`; `requirements/database.md`; `CHANGELOG.md`.
- **Implementation impact:** Documentation/business and physical-contract freeze only. A separately requested Migration 0019 may create only `core.tax_statutory_codes` and `core.tax_statutory_code_rates` after Migration 0018. No migration, ORM model, test, seed, service, API, provider integration, transaction calculation, GL posting, or existing-table change is included here.
- **Open follow-ups:** Tax publication/correction workflow, advanced TDS/TCS thresholds and cumulative behavior, exemptions/certificates, override authorization, runtime rate selection, transaction-date/rate-date behavior, and transaction calculation remain separately governed or deferred. None blocks the approved persistence-only two-table slice.

### CHG-2026-09-21-002 — Freeze GL hierarchy-placement and Group-inactivation contracts

- **Change ID:** CHG-2026-09-21-002
- **Date:** 2026-09-21
- **Status:** APPROVED
- **Area:** Company Configuration / Core Accounting Structure / Database Design
- **Source / discussion context:** Explicit approval resolving the direct-root GL-placement and Group-inactivation questions left open by the GL Account-to-Account Group placement audit.
- **Decision:** A GL may be unplaced (no effective mapping row), placed in a Group (row with Group UUID), or intentionally placed at hierarchy root (row with null Group). Group and root placements share one inclusive effective-dated history and cannot overlap for the same GL and hierarchy. A Group cannot become inactive while it has current/future GL placements or is the parent of current/future child-Group relationships; users must explicitly relocate or date-end them, historical ended rows do not block, and inactivation never restructures automatically. The exact future `core.gl_account_group_mappings` physical contract is frozen with nullable `account_group_id`, same-scope composite FKs, restrictive deletion, inclusive dates, GL-plus-hierarchy GiST exclusion, and one inverse Group/root loading index. Account Determination remains separate.
- **Reason:** Distinguish intentional root placement from incomplete configuration, preserve deterministic and historical hierarchy placement, and prevent Group inactivation from silently orphaning or rewriting current/future structure.
- **Supersedes:** The GL-placement physical-contract follow-up and at-most-one-Accounting-Group wording in CHG-2026-09-21-001, plus the not-frozen candidate wording in `requirements/database.md`. It does not change Group-root semantics for `account_group_relationships`, where root remains absence of a parent row.
- **Affected documents:** `requirements/COMPANY_CONFIGURATION.md`; `requirements/database.md`; `CHANGELOG.md`.
- **Implementation impact:** Documentation/business and physical-contract freeze only. A separately requested Migration 0018 may implement only `core.gl_account_group_mappings` against Migration 0017. No migration, ORM, API, service, inactivation workflow, Account Determination, restatement, posting, journal, or test implementation is included here.
- **Open follow-ups:** Implement and verify Migration 0018 in a separate slice; later implement transactional placement and Group-inactivation services/UI and any readiness validation. Account Determination, Management hierarchy behavior, reporting restatement, reclassification, posting, and journals remain separately governed or deferred.

### CHG-2026-09-21-001 — Freeze Accounting hierarchy history and future Account Determination direction

- **Change ID:** CHG-2026-09-21-001
- **Date:** 2026-09-21
- **Status:** APPROVED
- **Area:** Company Configuration / Core Accounting Structure / Future Account Determination
- **Source / discussion context:** Explicit approval of Company Configuration behavior following the verified Migration 0016 Account Hierarchy and Account Group foundation.
- **Decision:** In the `ACCOUNTING` hierarchy, an Account Group has zero or one effective parent on a date; root is represented by absence of an effective parent row; same-Company/same-hierarchy scope, no self-parenting, no cycles, effective-dated history, gap-safe normal reparenting, explicit Move to Root, alphabetical MVP sibling display, and unrestricted conceptual depth are required. GL Account remains a stable posting identity distinct from structural/non-posting Account Group, and its at-most-one Accounting Group placement per date is a separate effective relationship. Finalized posting identity remains distinct from hierarchy/reporting history. Future effective-dated Account Determination uses controlled, combinable Goods, Services, Supply, Company Location, and GST-context criteria with optional HSN/SAC and an applicable Company-default fallback; specificity precedes explicit priority and unresolved ambiguity blocks. Cost Centre is excluded.
- **Reason:** Freeze the agreed business behavior before designing relationship persistence, while protecting posting history from hierarchy restructuring and avoiding rigid catalogue-to-GL columns or an uncontrolled generic dimension engine.
- **Supersedes:** The candidate `account_group_relationships.parent_group_id = NULL` root-row direction in `requirements/database.md`. It does not supersede Migration 0016, current `revenue_gl_mappings`, `tax_gl_account_mappings`, the one default Receivable GL contract, or direct Bank Account GL references.
- **Affected documents:** `requirements/COMPANY_CONFIGURATION.md`; `requirements/database.md`; `CHANGELOG.md`.
- **Implementation impact:** Documentation/business-contract freeze only. No Migration 0017, ORM model, table, API, service, test, resolver, restatement, reclassification, or journal implementation is approved by this change. Account Group relationships, GL-to-Group mappings, and Account Determination persistence require separate physical-contract audits.
- **Open follow-ups:** Exact relationship columns and interval bounds; keys/indexes and overlap enforcement; database/service split for cycle, gap, and root validation; GL-placement physical contract; Account Determination table shape, account-purpose/default semantics, specificity/priority representation and conflict enforcement; transition/coexistence with current AR mappings; reporting restatement; accounting reclassification/journals; and transaction-level GL override authorization/workflow remain OPEN or DEFERRED as stated in the owning requirement.

### CHG-2026-09-19-007 — Finalize Account Hierarchy and Account Group persistence

- **Change ID:** CHG-2026-09-19-007
- **Date:** 2026-09-19
- **Status:** APPROVED
- **Area:** Core / Accounting Configuration / Database Design
- **Source / discussion context:** Explicit approval resolving the physical-contract gaps identified by the Migration 0016 Accounting Setup audit.
- **Decision:** For the current MVP, persist only `ACCOUNTING` hierarchies; use explicit `ACTIVE`/`INACTIVE` lifecycle values without status defaults; allow at most one active primary Accounting hierarchy per Company; enforce non-blank, case-sensitive Company/hierarchy-scoped names and optional Group codes; and enforce Group-to-Hierarchy Company ownership through a composite foreign key. IDs and timestamps use the established database-default conventions. Account Groups remain non-posting structural nodes without permanent parent, placement, or balance fields.
- **Reason:** Freeze the minimum relational contract needed for Company-owned CoA structure without introducing Management hierarchy behavior, permanent parentage, posting behavior, or speculative indexes.
- **Supersedes:** The unresolved physical details in CHG-2026-09-17-001 and the vague hierarchy/group uniqueness wording in `requirements/database.md`. It preserves CHG-2026-09-17-019's removal of the unapproved `DEFAULT 'ACTIVE'`.
- **Affected documents:** `requirements/COMPANY_CONFIGURATION.md`; `requirements/database.md`; `CHANGELOG.md`; Core Accounting ORM metadata; Alembic Migration 0016; focused model and PostgreSQL migration tests.
- **Implementation impact:** A separately executed Migration 0016 implementation in this approved slice may add only `core.account_hierarchies` and `core.account_groups` with the specified checks, uniqueness, same-Company composite FK, restrictive deletion, and approved partial unique index. No Accounting API is approved.
- **Open follow-ups:** Effective-dated Group relationships, stable-GL placement, Management hierarchy behavior, Accounting classifications, import/export, journals, posting, ledger, balances, reconciliation, closing, and reclassification remain separate or deferred work.

### CHG-2026-09-19-006 — Implement Exchange Rate and FX Policy persistence

- **Change ID:** CHG-2026-09-19-006
- **Date:** 2026-09-19
- **Status:** IMPLEMENTED
- **Area:** Core / Shared Company Configuration / AR FX Configuration / Database Design
- **Source / discussion context:** Approved Exchange Rate and FX Policy contract in CHG-2026-09-17-013 and the dependency-aware Company Configuration foundation sequence.
- **Decision:** Implement `core.exchange_rates` as Company-owned directional `CORPORATE`/`SPOT` rate facts with inclusive effective periods and active-period non-overlap, and implement `ar.fx_policies` as one controlled policy per Company and Billing/Receipt/Reporting purpose.
- **Reason:** Complete the approved FX persistence foundation while keeping reusable rate facts separate from AR process policy and transaction-time applied-rate snapshots.
- **Supersedes:** None. This implements the already-approved physical contract and does not resolve D04 or any runtime rate-selection, rate-date, precedence, stale-rate, conversion, authorization, or accounting behavior.
- **Affected documents:** `CHANGELOG.md`; Core Exchange Rate and AR FX Policy ORM metadata; Alembic Migration 0015; focused model and PostgreSQL migration tests.
- **Implementation impact:** Adds persistence/model/migration only. Database constraints enforce Company/Currency ownership, positive directional rates, controlled rate types and lifecycle, valid inclusive date ranges, no overlapping active periods for the same Company/direction/rate type, one policy per Company/purpose, controlled policy values, and override-reason consistency. No API, resolver, external provider, transaction conversion, or posting implementation is included.
- **Open follow-ups:** D04 remains open for rate/date/precedence, missing/stale-rate behavior, User-Fixed authorization, and purpose-specific runtime conversion. Rate-pair relevance to enabled Company currencies remains future write-service validation; no trigger is introduced.

### CHG-2026-09-19-005 — Implement Company currency permissions

- **Change ID:** CHG-2026-09-19-005
- **Date:** 2026-09-19
- **Status:** IMPLEMENTED
- **Area:** Core / Shared Company Configuration / AR Currency Configuration / Database Design
- **Source / discussion context:** Approved Currency configuration contract in CHG-2026-09-17-012 and the dependency-aware Company Configuration foundation sequence.
- **Decision:** Implement `core.company_reporting_currencies` for additional management-reporting choices and `ar.company_ar_currencies` for explicit Billing/Receipt permissions and active defaults. Reporting and AR permissions remain independent; Company Base Currency is not implicitly AR-enabled.
- **Reason:** Complete the Company currency-permission layer required before Exchange Rate facts and FX policies without merging management presentation choices into AR transaction permissions.
- **Supersedes:** None. This implements the already-approved contract and does not resolve open FX selection, rate-date, stale-rate, conversion, or override-authorization behavior.
- **Affected documents:** `CHANGELOG.md`; Core Reporting Currency and AR Currency ORM metadata; Alembic Migration 0014; focused model and PostgreSQL migration tests.
- **Implementation impact:** Adds persistence/model/migration only. Database constraints enforce row ownership, controlled lifecycle, useful active AR rows, enabled defaults, one Company/Currency row, and at most one active default per AR operation. The approved Base-Currency-versus-additional-Reporting-Currency rule remains backend/domain validation because the approved design explicitly excludes a database trigger; no CRUD API is included in this slice.
- **Open follow-ups:** Currency configuration API/lifecycle administration, active-reference validation, Base Currency exclusion in the future Reporting Currency write service, authenticated authorization, and detailed FX runtime behavior remain separate work.

### CHG-2026-09-19-004 — Confirm and implement Core Company Bank Accounts

- **Change ID:** CHG-2026-09-19-004
- **Date:** 2026-09-19
- **Status:** IMPLEMENTED
- **Area:** Core / Shared Company Configuration / Bank Accounts / Database Design
- **Source / discussion context:** Explicit approval that Company Bank Accounts physically belong to Core/Shared, followed by the approved Migration 0013 persistence slice.
- **Decision:** `core.company_bank_accounts` is the reusable Company-owned Bank Account master. Each account has one Currency, may reference one same-Company GL Account, and may be the single active Billing default for its Company/Currency. AR owns later invoice-selection behavior but does not own or duplicate the Bank Account identity.
- **Reason:** Resolve the prior Core-versus-AR boundary while preserving reusable banking identity, Company isolation, Currency-specific settlement meaning, and direct Bank-to-GL integrity.
- **Supersedes:** The Bank Account `Boundary TBD` wording in Company Configuration. It does not supersede CHG-2026-09-17-013's approved physical Bank contract.
- **Affected documents:** `requirements/COMPANY_CONFIGURATION.md`; `requirements/database.md`; `CHANGELOG.md`; Core Bank Account ORM metadata; Alembic Migration 0013; focused tests.
- **Implementation impact:** Adds persistence/model/migration only. No CRUD or Billing-selection API, routing, posting, journal, reconciliation, encryption/masking policy, account-number duplicate policy, identifier-format validation, or account-type vocabulary is introduced.
- **Open follow-ups:** Account-type vocabulary, duplicate-detection policy, exact IFSC/SWIFT/IBAN normalization and validation, bank-data encryption/masking/redaction policy, authenticated administration, Billing selection, Receipt/Reporting FX behavior, and full Accounting posting remain separately owned decisions.

### CHG-2026-09-19-003 — Implement Company Cost Center configuration foundation

- **Change ID:** CHG-2026-09-19-003
- **Date:** 2026-09-19
- **Status:** IMPLEMENTED
- **Area:** Company Configuration / Cost Center Reporting / Database Design
- **Source / discussion context:** Approved Cost Center contracts, including the Team separation recorded in [DDR-0001](decisions/DDR-0001-cost-center-team-buckets.md) and CHG-2026-09-19-002.
- **Decision:** Implement Company-owned Location Cost Center, Business Segment, and Cost Center Team reporting buckets; separate Company-owned actual Teams with optional Cost Center Team grouping; and one Company Cost Center Settings row controlling the three supported reporting bases. Add nullable same-Company Business Segment relationships to Service Types and SKUs, and a nullable same-Company Location Cost Center relationship to Company Locations.
- **Reason:** Establish the approved direct reporting dimensions without a generic Cost Center, accounting-dimension, or assignment framework, while preserving actual Team identity separately from reporting buckets.
- **Supersedes:** None. This implements the approved Cost Center foundation and Team split; it does not supersede the deferred IAM membership or authorization decisions.
- **Affected documents:** `requirements/COMPANY_CONFIGURATION.md`; `requirements/database.md`; `decisions/DDR-0001-cost-center-team-buckets.md`; `CHANGELOG.md`; Core Cost Center ORM/API; AR catalogue and Company Location metadata; Alembic Migration 0010; focused tests.
- **Implementation impact:** Adds Migration 0010 and configuration/create APIs for settings, Business Segments, Cost Center Team buckets, actual Teams, and Location Cost Centers. Creation is Tenant-safe, rejects inactive Companies, creates active master rows, and uses explicit service-owned commits. Database constraints enforce same-Company relationships and Company-scoped uniqueness.
- **Open follow-ups:** IAM subject persistence, `team_memberships`, effective-dated membership enforcement, assignment/update APIs for the nullable direct relationships, lifecycle-transition APIs, authenticated authorization, and downstream transaction posting/reporting remain separate work.

### CHG-2026-09-19-002 — Separate Cost Center Team reporting buckets from actual Teams

- **Change ID:** CHG-2026-09-19-002
- **Date:** 2026-09-19
- **Status:** APPROVED
- **Area:** Company Configuration / Cost Center Reporting / Database Design
- **Source / discussion context:** Explicit approved product decision recorded in [DDR-0001](decisions/DDR-0001-cost-center-team-buckets.md).
- **Decision:** `cost_center_teams` is a Company-owned reporting bucket, not the operational Team master. A separate Company-owned `teams` identity is retained. One Cost Center Team may group multiple actual Teams; each actual Team may reference zero or one Cost Center Team through a nullable direct relationship. `team_memberships` attaches users/IAM subjects to actual Teams and preserves effective-dated membership history.
- **Reason:** Management reporting may combine several operational Teams, such as BIS, AEO, and FEMA, under one reporting bucket without collapsing Team identity or attaching users directly to a cost-center grouping.
- **Supersedes:** Only the Team-model portion of CHG-2026-09-17-016 and the prior direction that Team itself was the reporting/cost-center bucket. Business Segment and Location Cost Center behavior remains unchanged.
- **Affected documents:** `PRODUCT_OVERVIEW.md`; `AR_MVP_ARCHITECTURE.md`; `requirements/COMPANY_CONFIGURATION.md`; `requirements/database.md`; `decisions/DDR-0001-cost-center-team-buckets.md`; `CHANGELOG.md`.
- **Implementation impact:** Documentation only. A future separately approved implementation must add actual `teams`, use nullable `teams.cost_center_team_id` with same-Company protection, and point `team_memberships.team_id` and downstream actual-Team references to `teams`. No model, migration, API, or test change is included here.
- **Open follow-ups:** Exact IAM subject persistence and database enforcement of one active actual-Team membership remain OPEN. Actual Teams may remain outside a Cost Center Team; any future activation/readiness requirement for complete coverage remains OPEN.

### CHG-2026-09-19-001 — Implement tax prerequisites and Company catalogue foundation

- **Change ID:** CHG-2026-09-19-001
- **Date:** 2026-09-19
- **Status:** IMPLEMENTED
- **Area:** Company Configuration / Tax Reference / AR Catalogue
- **Source / discussion context:** Approved implementation decisions resolving the catalogue lifecycle, tax prerequisites, Country FKs, active-reference validation, effective-date boundary, and Business Segment deferral.
- **Decision:** Implement the approved Tax Type, Company HSN/SAC, Tax Rate, eligible-rate mapping, and Tax Treatment prerequisites in Migration 008, followed by the Company-owned Service and Goods catalogue in Migration 009. Catalogue lifecycle is `ACTIVE` / `INACTIVE`; current create APIs create complete `ACTIVE` records. Tax Rate and Tax Treatment jurisdictions reference `core.countries.code`. Catalogue creation requires active parents and active GST references, but does not treat the setup date as the tax effective date. Business Segment relationships are deferred without placeholder columns.
- **Reason:** Mandatory statutory references must exist before Service Type and SKU can preserve controlled selections, while catalogue ownership and tenant isolation continue to flow through Company.
- **Supersedes:** The direct `business_segment_id` requirement for Service Type and SKU in this implementation phase, and the open Country-FK target for Tax Rate and Tax Treatment.
- **Affected documents:** `requirements/COMPANY_CONFIGURATION.md`; `requirements/database.md`; `CHANGELOG.md`.
- **Implementation impact:** Adds Core tax-reference ORM/migration objects, AR catalogue ORM/migration/API objects, focused tests, and application/Alembic registration. No seed data, tax calculation, Billing, inventory, Cost Center, or lifecycle-transition API is included.
- **Open follow-ups:** Reference-data provisioning and administration APIs, Business Segment/Cost Center relationships, lifecycle-transition APIs, and transaction-date tax applicability remain later work.

### CHG-2026-09-18-007 — Finalize and implement Company GST Registration foundation

- **Change ID:** CHG-2026-09-18-007
- **Date:** 2026-09-18
- **Status:** IMPLEMENTED
- **Area:** Core / Shared Company Configuration / GST Registration
- **Source / discussion context:** Explicit approval of GST Registration lifecycle, shared State/UT representation, India Company eligibility, structural GSTIN validation, Draft nullability, validity dates, and Location ownership/jurisdiction rules.
- **Decision:** Implement platform-managed `core.gst_registration_types` without seed values and Company-owned `core.company_gst_registrations` with globally unique structurally valid GSTINs, mandatory shared Indian Subdivision jurisdiction, optional Draft Registration Type/legal name/validity dates, and `DRAFT`/`ACTIVE`/`INACTIVE` lifecycle. Extend Country Subdivision with a nullable country-scoped two-digit GST State code and add the direct nullable Location relationship protected by same-Company and same-Subdivision composite integrity.
- **Reason:** Establish a stable seller GST identity that later LUT, Billing, numbering, and statutory features can reference without duplicating GSTIN on Company or Location or creating a second State master.
- **Supersedes:** The open lifecycle, jurisdiction representation, Draft Registration-Type nullability, and GSTIN-validation decisions in CHG-2026-09-17-009 and CHG-2026-09-17-014; it activates only the direct Location FK portion deferred by CHG-2026-09-18-005.
- **Affected documents:** `requirements/COMPANY_CONFIGURATION.md`, `requirements/database.md`; geographic and Company Location ORM metadata; Company GST Registration ORM/API; Alembic Migration 007; focused schema, model, API, and PostgreSQL migration tests.
- **Implementation impact:** Adds `POST /companies/{company_id}/gst-registrations`, using Tenant-safe Company lookup and explicit service-owned commit. New rows start as `DRAFT`; Company must be Indian, and the active Indian Subdivision's provisioned GST State code must match the GSTIN prefix.
- **Open follow-ups:** GST checksum and portal verification, exact Registration Type reference values/loader, activation/readiness and lifecycle-transition APIs, default-GSTIN/default-Location behavior, registration version history, LUT, numbering, Billing, place of supply, returns, e-Invoice/e-Way Bill, and tax calculation remain separate work.

### CHG-2026-09-18-006 — Finalize and implement Company Financial Year configuration

- **Change ID:** CHG-2026-09-18-006
- **Date:** 2026-09-18
- **Status:** IMPLEMENTED
- **Area:** Core / Shared Company Configuration / Database Design
- **Source / discussion context:** Explicit approval of typed fiscal patterns, configurable CUSTOM month/day, universally valid recurring dates, Financial Year lifecycle, transition representation, and normal generation behavior.
- **Decision:** Implement one `core.company_fiscal_settings` row per Company with `APR_MAR`, `JAN_DEC`, or `CUSTOM` plus explicit start month/day, rejecting recurring dates unavailable in non-leap years. Implement authoritative `core.financial_years` instances with Company-scoped display codes, explicit dates, transition intent, `DRAFT`/`OPEN`/`CLOSED`, and race-safe same-Company non-overlap. Normal generation accepts only a start year, calculates dates/code from settings, and creates `DRAFT` non-transition rows.
- **Reason:** Preserve authoritative historical Financial Year identities and exceptional transition representation while making ordinary annual setup deterministic and distinct from reporting ranges, Accounting locks, and receivable settlement.
- **Supersedes:** The OPEN lifecycle values in CHG-2026-09-17-011 and its unresolved physical overlap implementation details. It retains configurable start day/month and explicit transition Financial Years.
- **Affected documents:** `requirements/COMPANY_CONFIGURATION.md`, `requirements/database.md`; Core Financial Year ORM models and APIs; Alembic Migration 006; focused model, schema, generation, API, and PostgreSQL migration tests.
- **Implementation impact:** Adds `PUT /companies/{company_id}/financial-year-settings` and `POST /companies/{company_id}/financial-years`, using Tenant-safe Company lookup and explicit service-owned commits. Migration 006 uses `btree_gist` for the Company/date exclusion constraint.
- **Open follow-ups:** Transition-year creation, Financial Year lifecycle transition endpoints, reopening policy, automated next-year proposal timing, authenticated authorization, accounting periods/locks, transaction-date FY resolution, and downstream LUT/numbering references remain separate work.

### CHG-2026-09-18-005 — Finalize and implement the Core Company Location foundation

- **Change ID:** CHG-2026-09-18-005
- **Date:** 2026-09-18
- **Status:** IMPLEMENTED
- **Area:** Core / Shared Company Configuration / Database Design
- **Source / discussion context:** Explicit approval of the multi-purpose Company Location model and its previously OPEN Country/Subdivision physical contract.
- **Decision:** Implement `core.company_locations` with required Company ownership, required non-blank Location identity/address fields, five combinable fixed-purpose flags plus optional `other_purpose`, mandatory Country, optional compatible first-level Subdivision, `ACTIVE`/`INACTIVE` lifecycle, timestamps, and at most one active Registered Office per Company. Enforce Country/Subdivision compatibility through a composite FK supported by `country_subdivisions(country_code, code)` uniqueness, while retaining globally unique complete Subdivision codes.
- **Reason:** Establish the first usable multi-location configuration flow without duplicating physical Locations by purpose or weakening Tenant, jurisdiction, and Registered Office integrity.
- **Supersedes:** The OPEN Company Location Country/State physical representation in CHG-2026-09-17-010 and the imported database baseline. It retains the approved fixed multi-purpose model and required Location Name.
- **Affected documents:** `requirements/COMPANY_CONFIGURATION.md`, `requirements/database.md`; Core Company Location ORM model and API; geographic ORM metadata; Alembic Migration 005; focused model, schema, API, and PostgreSQL migration tests.
- **Implementation impact:** Adds Migration 005 and `POST /companies/{company_id}/locations`. Creation is Tenant-safe, starts Locations as `ACTIVE`, validates active Country/optional Subdivision, permits Draft and Active Companies, rejects Inactive Companies, and owns its successful transaction commit.
- **Open follow-ups:** GST Registration/default-Location relationships, Location Cost Center relationship, effective address versions, Registered Office replacement, Company activation-readiness, authenticated Company authorization, and Country-specific subdivision requirements remain separate work.

### CHG-2026-09-18-004 — Finalize and implement Core geographic reference masters

- **Change ID:** CHG-2026-09-18-004
- **Date:** 2026-09-18
- **Status:** IMPLEMENTED
- **Area:** Core / Shared Geographic Reference / Database Design
- **Source / discussion context:** Explicit approval of the minimum global Country and first-level Country Subdivision contracts for Migration 004.
- **Decision:** Implement global platform-managed `core.countries` using uppercase two-letter Country code identity and `core.country_subdivisions` using stable UUID identity plus unique complete ISO-compatible subdivision codes, canonical subdivision-type syntax, lifecycle checks, timestamps, restrictive Country ownership, and one Country lookup index. Exclude Country alpha-3/numeric columns, City/District/postal/address hierarchies, seed data, and automatic reference loading.
- **Reason:** Supply shared controlled Country and first-level jurisdiction identities for Company and future Location configuration without creating a broad address framework.
- **Supersedes:** The deferred Country and State-master direction in the imported database baseline and the Country-master deferral noted by CHG-2026-09-18-002. It does not change the physical contracts of Migrations 002 or 003.
- **Affected documents:** `requirements/COMPANY_CONFIGURATION.md`, `requirements/database.md`; Core geographic ORM models; Alembic Migration 004; focused model and PostgreSQL migration tests.
- **Implementation impact:** Adds only `core.countries` and `core.country_subdivisions` after Migration 003. Existing `entity_types.country_code` and `companies.country_code` receive no FK yet, and Company receives no subdivision column.
- **Open follow-ups:** A separate version-controlled reference-data loader must provision Countries and Subdivisions. Existing Entity Type and Company Country values must then be audited before later restrictive Country FKs are added. Company Location subdivision persistence remains separately governed.

### CHG-2026-09-18-003 — Finalize and implement the Core Company identity foundation

- **Change ID:** CHG-2026-09-18-003
- **Date:** 2026-09-18
- **Status:** IMPLEMENTED
- **Area:** Core / Shared Company Identity / Database Design
- **Source / discussion context:** Explicit approval of the Currency, Organisation, Company Code, and Draft Company physical contracts as one production migration batch.
- **Decision:** Implement global `core.currencies`; code-free Tenant-owned `core.organisations`; a concurrency-safe global `COM` Company Code sequence/function; and Draft-capable `core.companies`. Enforce direct Tenant ownership, same-Tenant Organisation assignment through a composite FK, restrictive reference deletion, generated UUIDs, timestamp insert defaults, named lifecycle/format/nonblank checks, and only the approved supporting indexes. Keep Entity Type/country compatibility and activation completeness in future transactional Company business logic.
- **Reason:** Establish the minimum coherent Company identity and Base Currency foundation while preserving Tenant isolation and allowing incomplete onboarding drafts without encoding evolving activation rules in one table constraint.
- **Supersedes:** The open Company-Code nullability/scope, Organisation-code, Company status/nullability, jurisdiction representation, and same-Tenant Organisation physical-design details in the imported Company-configuration/database baseline. It does not promote any REVIEW/DEFERRED Company profile, legal-identifier, Location, fiscal, access, or AR design.
- **Affected documents:** `requirements/COMPANY_CONFIGURATION.md`, `requirements/database.md`, `AR_MVP_ARCHITECTURE.md`; Core Currency, Organisation, and Company ORM models; Alembic Migration 003; focused model and PostgreSQL migration tests.
- **Implementation impact:** Adds one logical migration after Migration 002. It creates only the three approved tables plus the Company Code sequence/function and leaves `core.tenants` and `core.entity_types` unchanged.
- **Open follow-ups:** Currency reference-data provisioning, Company activation service/API, IANA and Entity Type/country validation, Company Code immutability in application services, profile/legal-name history, access authorization, Locations, fiscal setup, and AR configuration remain separate work.

### CHG-2026-09-18-002 — Finalize and implement the Core Entity Type master contract

- **Change ID:** CHG-2026-09-18-002
- **Date:** 2026-09-18
- **Status:** IMPLEMENTED
- **Area:** Core / Shared Reference / Database Design
- **Source / discussion context:** Explicit approval of the minimum Entity Type physical contract for the second production database migration.
- **Decision:** Implement `core.entity_types` with PostgreSQL-generated UUIDs, direct uppercase two-letter `country_code` jurisdiction without a Countries FK, jurisdiction-scoped canonical code uniqueness and format checks, required but non-unique display names, and `VARCHAR(20)` lifecycle status plus CHECK and no default. Exclude timestamps, seed data, speculative indexes, delete automation, cascade, RLS, Company, and legal-identifier rules.
- **Reason:** Establish the controlled global legal-form reference needed by future Company configuration without creating an unapproved Countries master or broader master-data framework.
- **Supersedes:** The unresolved physical jurisdiction, UUID, code-constraint, name-uniqueness, and status details in CHG-2026-09-17-007 and the imported Entity Type database-design baseline; it does not supersede the approved business definition or platform-ownership boundary.
- **Affected documents:** `requirements/database.md`; Core Entity Type ORM model; Alembic Migration 002; focused Entity Type tests.
- **Implementation impact:** Adds only the Core/Shared Entity Type model and Migration 002 after the existing Tenant migration. It does not add Countries, Company, Organisation, authentication, APIs, seed data, or AR behavior.
- **Open follow-ups:** Company-to-Entity-Type jurisdiction compatibility and future restrictive/no-action Company FK behavior remain for the separate Company contract. Countries and import aliases remain deferred, and the legal-form/identifier-rule catalogue remains separately governed.

### CHG-2026-09-18-001 — Finalize and implement the Core Tenant master contract

- **Change ID:** CHG-2026-09-18-001
- **Date:** 2026-09-18
- **Status:** IMPLEMENTED
- **Area:** Core / Shared / Database Design
- **Source / discussion context:** Explicit approval of the minimum Tenant physical contract for the first production database slice.
- **Decision:** Implement `core.tenants` with PostgreSQL-generated UUIDs, concurrency-safe sequential `TEN` codes, `VARCHAR(20)` lifecycle status plus CHECK and no default, insert-time timestamp defaults, nonblank checks, and no speculative indexes. Exclude an update trigger, hard-delete workflow, cascade, RLS, authentication, memberships, and downstream business tables.
- **Reason:** Establish the authoritative SaaS ownership root without resolving or importing any unapproved Company, access, or AR behavior.
- **Supersedes:** The unresolved physical details in the imported Tenant database-design baseline; it does not supersede the existing Tenant ownership or lifecycle semantics.
- **Affected documents:** `requirements/database.md`; Core Tenant ORM model; Alembic Migration 001; focused Tenant tests.
- **Implementation impact:** Adds the first Core/Shared ORM model and migration. No Company, Organisation, Entity Type, Currency, AR, authentication, membership, or RLS implementation is included.
- **Open follow-ups:** Automatic `updated_at` maintenance awaits the application update path. Tenant/User membership, exceptional deletion/retention, downstream Tenant FKs, and authorization remain separately governed.

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
