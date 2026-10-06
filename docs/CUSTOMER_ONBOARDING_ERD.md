# Customer Onboarding and Customer Master Database Design

## 1. Status, authority, and scope

**Document status:** `CURRENT WORKING DESIGN / PROPOSED FOR FREEZE` — documentation and design only.

This is the canonical Customer Onboarding database-design review artifact. It uses the [Customer Onboarding Architecture and Decision Baseline](architecture/customer_onboarding_decision_baseline.md), [Customer Onboarding Requirements](requirements/customer_onboarding.md), [Approval and Audit Requirements](requirements/approval_and_audit), [Module Boundaries](architecture/moduleboundaries.md), and shared-table contracts in [database.md](requirements/database.md).

It does not authorize SQL, migrations, ORM models, APIs, services, routes, frontend work, tests, or physical database changes. Exact data types, constraint syntax, indexes, and reference-key names remain part of the freeze/implementation-design review.

The design deliberately keeps two persistence concerns separate:

1. **Operational Customer Master** — only approved/current data used by Sales Order, Billing, Receipts, Collections, and reporting.
2. **Customer Request / Approval / History** — editable pending proposals, immutable submitted payloads, and append-only workflow evidence.

Pending request data must never overwrite operational Customer rows before approval. Approval/publication must atomically validate and publish the approved payload.

## 2. Architectural boundary

- A Customer belongs to one seller Company.
- Common/Party-like identity, statutory, Location, Contact, and Contact-detail data remains physically Customer-owned for MVP.
- No Party Master, Vendor model, shared Contact master, or generic Counterparty architecture is introduced.
- Customer default Payment Term, Customer Code lifecycle, approval, and communication purposes remain Customer/AR-specific.
- Bill-To and Ship-To are transaction selections from eligible approved Locations, not permanent Customer Location flags.
- Finalized financial documents preserve transaction-time snapshots in their own design; this document does not redesign Billing snapshots.
- Credit Limit is outside the current Customer MVP.

## 3. Current 14-table working set

### 3.1 Operational / approved Customer Master

| # | Table | Responsibility | Status |
|---:|---|---|---|
| 1 | `customer_organisations` | Optional external grouping of Customer legal entities | `CURRENT WORKING DESIGN` |
| 2 | `customers` | Current approved Company-specific Customer root | `CURRENT WORKING DESIGN` |
| 3 | `customer_identifiers` | Current non-GST legal/statutory identifiers | `CURRENT WORKING DESIGN` |
| 4 | `customer_gst_registrations` | Current Customer GST registrations | `CURRENT WORKING DESIGN` |
| 5 | `customer_locations` | Stable Customer Location identity | `CURRENT WORKING DESIGN` |
| 6 | `customer_location_versions` | Effective-dated Location name/address/GST context | `CURRENT WORKING DESIGN` |
| 7 | `customer_documents` | Current Customer supporting-file associations | `CURRENT WORKING DESIGN` |
| 8 | `customer_contacts` | Person, department, or general Contact identity | `CURRENT WORKING DESIGN`; post-approval control `REVIEW` |
| 9 | `customer_contact_details` | Email/phone/mobile/WhatsApp reachability | `CURRENT WORKING DESIGN`; verification `REVIEW` |
| 10 | `customer_contact_roles` | Organisational/business roles of Contacts | `CURRENT WORKING DESIGN` |
| 11 | `customer_contact_purposes` | Why a Contact Detail may be used | `CURRENT WORKING DESIGN`; delivery resolution `REVIEW` |

### 3.2 Request / approval / history

| # | Table | Responsibility | Status |
|---:|---|---|---|
| 12 | `customer_requests` | Current Customer onboarding/amendment case and authoritative editable Draft | `CURRENT WORKING DESIGN` |
| 13 | `customer_request_snapshots` | Immutable exact payload at Submit/Resubmit or Authority approval-with-changes | `CURRENT WORKING DESIGN` |
| 14 | `customer_request_actions` | Append-only workflow/action journey | `CURRENT WORKING DESIGN` |

No `customer_request_drafts`, `customer_identifier_claims`, typed revision-child tables, approval-submission/decision pair, or field-level review-findings table belongs to this working set.

## 4. Logical ERD

~~~mermaid
erDiagram
    tenants ||--o{ customer_organisations : scopes
    companies ||--o{ customer_organisations : owns
    companies ||--o{ customers : owns
    customer_organisations o|--o{ customers : optionally_groups
    customers ||--o{ customer_identifiers : has
    customers ||--o{ customer_gst_registrations : has
    customers ||--o{ customer_locations : has
    customer_locations ||--o{ customer_location_versions : versions
    customer_gst_registrations o|--o{ customer_location_versions : may_contextualize
    customers ||--o{ customer_documents : supports
    stored_files ||--o{ customer_documents : stores
    customer_identifiers o|--o{ customer_documents : may_evidence
    customer_gst_registrations o|--o{ customer_documents : may_evidence
    customers ||--o{ customer_contacts : has
    customer_gst_registrations o|--o{ customer_contacts : may_contextualize
    customer_locations o|--o{ customer_contacts : may_contextualize
    customer_contacts ||--o{ customer_contact_details : reachable_by
    customer_contacts ||--o{ customer_contact_roles : represents
    customer_contact_details ||--o{ customer_contact_purposes : used_for
    customers o|--o{ customer_requests : target_of
    companies ||--o{ customer_requests : owns
    customer_requests ||--o{ customer_request_snapshots : captures
    customer_request_snapshots o|--o{ customer_request_snapshots : derived_from
    customer_requests ||--o{ customer_request_actions : records
    customer_request_snapshots o|--o{ customer_request_actions : evidenced_by
    payment_terms o|--o{ customers : defaults_for
    entity_types o|--o{ customers : classifies
    legal_identifier_types ||--o{ customer_identifiers : classifies
~~~

The editable Mermaid source is [customer_onboarding_erd.mmd](customer_onboarding_erd.mmd).

## 5. Shared-reference alignment

The logical `country_id`, `state_id`, and `identifier_type_id` names below express references to shared geography/legal-identifier concepts. Physical FK names and targets must align with the repository's existing `countries`, `country_subdivisions`, and currently Company-named identifier-type references during freeze. The possible reusable legal-identifier-type rename/alignment remains `REVIEW`; it does not add a fifteenth Customer table.

`document_type_id` must reference an approved reusable document-type identity. The exact existing target/name remains a reference-alignment `REVIEW`; no Customer-specific document-rule or document-type table is introduced by this design.

Other reused identities include `tenants`, `companies`, `entity_types`, `gst_registration_types`, `payment_terms`, `stored_files`, IAM actor identities, and the separately reviewed audit capability.

## 6. Detailed operational tables

All IDs are proposed UUID primary keys unless repository conventions select another existing standard. Actor columns reference the authenticated IAM subject contract. Historically referenced operational rows are normally inactivated rather than hard-deleted.

### 6.1 `customer_organisations`

**Purpose:** Optional external grouping of separately billable Customer legal entities, for example ABC Group containing ABC India Pvt Ltd and ABC Technologies Pvt Ltd. It is not the ERP's internal Organisation/Company hierarchy and is not Party Master.

| Column | Null? | Meaning / relationship |
|---|---:|---|
| `id` | No | PK |
| `tenant_id` | No | FK to owning Tenant/isolation context |
| `company_id` | No | FK to owning seller Company |
| `organisation_name` | No | Legal/business group name |
| `display_name` | Yes | Optional search/display label |
| `status` | No | `ACTIVE` or `INACTIVE` |
| `created_at`, `created_by` | No | Creation evidence |
| `updated_at`, `updated_by` | No | Current-row update evidence |

**Relationships and rules:** One Company may have many Customer Organisations; one Customer Organisation may group many Customers; a Customer may remain standalone. The group and every associated Customer must share the same Company/Tenant scope.

**Lifecycle:** Inactive groups cannot receive new associations; historical associations remain. Current state plus audit is sufficient.

### 6.2 `customers`

**Purpose:** Current approved operational Customer root. Pending onboarding/amendment values never live here before approval.

| Column | Null? | Meaning / relationship |
|---|---:|---|
| `id` | No | PK and stable Customer identity |
| `tenant_id` | No | FK to Tenant/isolation context |
| `company_id` | No | FK to owning seller Company |
| `customer_organisation_id` | Yes | FK to optional same-Company Customer Organisation |
| `customer_code` | No after publication | System-generated stable Company-scoped code |
| `legal_name` | No | Current approved legal name |
| `display_name` | Yes | Optional display/search name |
| `entity_type_id` | Yes | FK to shared Entity Type; Customer applicability remains `REVIEW` |
| `country_id` | No | FK to shared Country reference; physical key alignment at freeze |
| `is_gst_registered` | No | Current GST-registration declaration |
| `default_payment_term_id` | Yes | FK to active same-Company Payment Term; null uses Company default |
| `status` | No | `ACTIVE` or `INACTIVE` |
| `created_at`, `created_by` | No | Publication/creation evidence |
| `updated_at`, `updated_by` | No | Current-row update evidence |

**Rules:** Company-specific ownership is mandatory. Customer Code is allocated only during successful `NEW_CUSTOMER` approval/publication and remains stable. Credit Limit, Receivable GL, direct PAN/CIN/LLPIN, draft status, revision pointers, and Bill-To/Ship-To flags are absent.

**Lifecycle:** Publication creates an `ACTIVE` Customer. Inactivation is Authority-level and blocks new commercial use while preserving historical settlement and evidence. Reactivation policy remains `OPEN`.

### 6.3 `customer_identifiers`

**Purpose:** Current approved jurisdiction-specific legal/statutory identifiers other than GSTIN.

| Column | Null? | Meaning / relationship |
|---|---:|---|
| `id` | No | PK |
| `customer_id` | No | FK to Customer |
| `company_id` | No | FK/denormalized duplicate-control scope; must match Customer |
| `identifier_type_id` | No | FK to reusable legal-identifier type |
| `identifier_value` | No | Business/display value |
| `normalized_value` | No | Canonical comparison/search value |
| `status` | No | `ACTIVE` or `INACTIVE` |
| `created_at`, `created_by`, `updated_at`, `updated_by` | No | Current-row evidence |

**Rules:** No direct PAN/CIN/LLPIN columns belong on `customers`; GSTIN does not belong here. Approved/current uniqueness is Company-scoped by identifier type and normalized value. India-MVP PAN and applicable supporting evidence remain governed by onboarding readiness; no worldwide identifier-rule engine is introduced.

**Lifecycle:** Corrections/inactivation preserve audit/history; finalized transactions preserve the identity actually used.

### 6.4 `customer_gst_registrations`

**Purpose:** Current approved Customer GST registrations, separate from generic identifiers and physical Locations.

| Column | Null? | Meaning / relationship |
|---|---:|---|
| `id` | No | PK |
| `customer_id` | No | FK to Customer |
| `company_id` | No | FK/duplicate-control scope; must match Customer |
| `gstin` | No | Business/display GSTIN |
| `normalized_gstin` | No | Canonical comparison value |
| `registered_legal_name` | No | Name registered for this GSTIN |
| `gst_registration_type_id` | No | FK to shared GST Registration Type |
| `state_id` | No | FK to shared State/subdivision reference; physical key alignment at freeze |
| `status` | No | `ACTIVE` or `INACTIVE` |
| `created_at`, `created_by`, `updated_at`, `updated_by` | No | Current-row evidence |

**Rules:** A Customer may have zero registrations when unregistered, or one/many distinct registrations when registered. Approved/current normalized GSTIN uniqueness is Company-scoped. A Location version may associate with an applicable same-Customer registration.

**Lifecycle:** Incorrect/obsolete registrations are inactivated and replacement is introduced through the controlled change path. Final transactions snapshot the selected GST identity.

### 6.5 `customer_locations`

**Purpose:** Stable identity of a Customer Location across address/version changes.

| Column | Null? | Meaning / relationship |
|---|---:|---|
| `id` | No | PK |
| `customer_id` | No | FK to Customer |
| `company_id` | No | FK/scope; must match Customer |
| `location_code` | No | Stable Customer-local Location code, for example `LOC-001` |
| `status` | No | `ACTIVE` or `INACTIVE` |
| `created_at`, `created_by` | No | Stable identity creation evidence |

**Rules:** Physical address, Location name, GST association, and registered-address designation are not duplicated here. There are no permanent Billing/Shipping flags.

**Lifecycle:** Stable identity survives version changes. Historically used Locations are inactivated rather than deleted; address history remains in versions.

### 6.6 `customer_location_versions`

**Purpose:** Effective-dated versions of actual Customer Location information.

| Column | Null? | Meaning / relationship |
|---|---:|---|
| `id` | No | PK |
| `customer_location_id` | No | FK to stable Customer Location |
| `version_no` | No | Monotonic sequence within Location |
| `location_name` | No | Effective site name/label |
| `address_line_1` | No | Effective address |
| `address_line_2` | Yes | Effective address continuation |
| `city` | No | City/locality |
| `district` | Yes | District |
| `state_province` | No | Effective subdivision value/reference alignment at freeze |
| `postal_code` | No | Effective postal code |
| `country_id` | No | FK to shared Country reference |
| `customer_gst_registration_id` | Yes | FK to applicable same-Customer GST registration |
| `is_registered_address` | No | Effective registered-address designation |
| `valid_from` | No | Inclusive effective start |
| `valid_to` | Yes | Inclusive/contract-defined end; null is current open version |
| `created_at`, `created_by` | No | Immutable version creation evidence |

**Rules:** Address-bearing fields exist only here. Versions for one Location must not overlap, version numbers must be unique per Location, and at most one open/current version is allowed. An approved effective change creates a new version instead of rewriting historical versions. GST mapping and registered-address designation currently belong to the effective version.

**Lifecycle:** Versions are historical and queryable, not hard-deleted. Future scheduling/backdating is not introduced by this design. Whether GST-to-Location mapping changes require approval remains `REVIEW`.

### 6.7 `customer_documents`

**Purpose:** Associates Customer evidence with immutable file metadata in the existing `stored_files` infrastructure.

| Column | Null? | Meaning / relationship |
|---|---:|---|
| `id` | No | PK |
| `customer_id` | No | FK to Customer |
| `document_type_id` | No | FK to approved reusable document-type identity; target alignment `REVIEW` |
| `stored_file_id` | No | FK to `stored_files`; no file bytes here |
| `customer_identifier_id` | Yes | FK to evidenced same-Customer identifier |
| `customer_gst_registration_id` | Yes | FK to evidenced same-Customer GST registration |
| `status` | No | Current link lifecycle |
| `created_at`, `created_by`, `updated_at`, `updated_by` | No | Link evidence |

**Rules:** PAN/GST supporting evidence is required where applicable to the onboarding flow. JSON request payloads contain file references, never file binaries. No configurable document-rule engine or new storage framework is introduced.

**Lifecycle:** Replaced/inactive links remain historically traceable. Immutable request snapshots preserve the exact submitted file references.

### 6.8 `customer_contacts`

**Purpose:** Customer-owned Contact identity for a person, department, or general/shared contact.

| Column | Null? | Meaning / relationship |
|---|---:|---|
| `id` | No | PK |
| `customer_id` | No | FK to Customer |
| `contact_type` | No | `PERSON`, `DEPARTMENT`, or `GENERAL` |
| `display_name` | No | Human-readable Contact label |
| `customer_gst_registration_id` | Yes | Optional same-Customer GST context |
| `customer_location_id` | Yes | Optional same-Customer Location context |
| `status` | No | `ACTIVE` or `INACTIVE` |
| `created_at`, `created_by`, `updated_at`, `updated_by` | No | Current-row evidence |

**Rules:** Contact identity remains separate from reachability, role, and purpose. Contact may optionally be scoped to a Customer GST registration and/or Location.

**Lifecycle:** Initial-onboarding Contacts may be carried in the request payload and published with the Customer. Post-approval Contact change approval versus direct authorized edit plus audit remains `REVIEW`.

### 6.9 `customer_contact_details`

**Purpose:** Stores how a Contact can be reached; this friendly name supersedes `customer_communication_endpoints`.

| Column | Null? | Meaning / relationship |
|---|---:|---|
| `id` | No | PK |
| `customer_contact_id` | No | FK to Customer Contact |
| `detail_type` | No | Initial values include `EMAIL`, `PHONE`, `MOBILE`, `WHATSAPP` |
| `detail_value` | No | Entered/display address or number |
| `normalized_value` | No | Canonical validation/comparison value |
| `status` | No | `ACTIVE` or `INACTIVE` |
| `created_at`, `created_by`, `updated_at`, `updated_by` | No | Current-row evidence |

**Rules:** Backend format validation/normalization remains required. Endpoint verification/provider rules are not part of the database freeze.

**Lifecycle:** Prior details are inactivated rather than silently overwritten where historical communication evidence exists. Delivery/reminder requests later snapshot resolved values.

### 6.10 `customer_contact_roles`

**Purpose:** Organisational/business role of a Contact, separate from communication purpose.

| Column | Null? | Meaning / relationship |
|---|---:|---|
| `id` | No | PK |
| `customer_contact_id` | No | FK to Customer Contact |
| `role_code` | No | Initial examples: `PRIMARY`, `BILLING`, `FINANCE`, `ESCALATION` |
| `created_at`, `created_by` | No | Assignment evidence |

**Rules/lifecycle:** A Contact may have multiple distinct roles. Role does not automatically authorize use of any Contact Detail; particularly, `PRIMARY` does not automatically mean invoice recipient. Removal/history mechanics follow the later audit/authorization design without adding a speculative role-history table.

### 6.11 `customer_contact_purposes`

**Purpose:** Records why a particular Contact Detail may be used; this friendly name supersedes `customer_ar_communication_purpose_assignments`.

| Column | Null? | Meaning / relationship |
|---|---:|---|
| `id` | No | PK |
| `customer_contact_detail_id` | No | FK to Contact Detail |
| `purpose_code` | No | Initial examples: `BILLING`, `PAYMENT`, `PAYMENT_REMINDER` |
| `created_at`, `created_by` | No | Assignment evidence |

**Rules/lifecycle:** Contact Role and Contact Purpose remain separate. TO/CC/BCC, fallback, priority, recipient resolution, verification, and delivery/reminder override rules remain outside this table and under `REVIEW` in Delivery/Reminder design.

## 7. Request, approval, and immutable history tables

### 7.1 `customer_requests`

**Purpose:** Complete Customer approval/change case and its one current authoritative editable server-side Draft.

| Column | Null? | Meaning / relationship |
|---|---:|---|
| `id` | No | PK |
| `tenant_id` | No | FK to Tenant/isolation context |
| `company_id` | No | FK to owning seller Company |
| `request_type` | No | Controlled Customer request type |
| `target_customer_id` | Yes | FK to existing Customer for amendments; null for `NEW_CUSTOMER` |
| `status` | No | `DRAFT`, `SUBMITTED`, `RETURNED`, `APPROVED`, `REJECTED`, or `CANCELLED` |
| `draft_data JSONB` | No | Current editable authoritative request payload |
| `created_by`, `created_at` | No | `created_by` is the Maker for this request |
| `updated_by`, `updated_at` | No | Current Draft/control-row update evidence |

**Request shapes:** `NEW_CUSTOMER` normally contains a complete onboarding payload. Material amendments such as `ADD_GST`, `ADD_LOCATION`, or `UPDATE_CUSTOMER` may contain only the proposed change and relevant context/evidence. `ADD_CONTACT` is used only if the unresolved post-approval Contact policy ultimately requires approval.

**Maker ownership:** Only the request Maker normally edits it while editable. `DRAFT` is editable; after Return the same Maker corrects the `RETURNED` request and resubmits. Other ordinary Makers do not edit it. PostgreSQL `draft_data` is authoritative; optional browser IndexedDB is only local recovery/cache.

**Lifecycle:** `SUBMITTED` is locked against Maker edits. `APPROVED`, `REJECTED`, and `CANCELLED` are terminal. Only one open request (`DRAFT`, `SUBMITTED`, `RETURNED`) may exist per non-null `target_customer_id` in MVP.

### 7.2 `customer_request_snapshots`

**Purpose:** Immutable exact request payload captured at each formal Submit/Resubmit point and, when applicable, the exact Authority-approved result.

| Column | Null? | Meaning / relationship |
|---|---:|---|
| `id` | No | PK |
| `request_id` | No | FK to Customer Request |
| `snapshot_no` | No | Monotonic number within request |
| `snapshot_type` | No | `MAKER_SUBMISSION` or `AUTHORITY_APPROVED` |
| `submitted_data JSONB` | No | Exact immutable submitted/approved request payload |
| `source_snapshot_id` | Yes | Self-FK to source Maker snapshot for Authority-approved changes |
| `created_by`, `created_at` | No | Snapshot actor/time evidence |

**Rules:** (`request_id`, `snapshot_no`) is unique. Snapshot content is append-only/immutable. Submit and Resubmit create `MAKER_SUBMISSION` snapshots. Return never changes an existing snapshot. `APPROVE_WITH_CHANGES` may create `AUTHORITY_APPROVED` sourced from the reviewed Maker snapshot.

For `NEW_CUSTOMER`, the snapshot may be the complete form. An amendment snapshot preserves the exact requested delta and supporting/context data; it does not duplicate the complete Customer aggregate unless a later requirement demands it. No `payload_schema_version` is introduced at this stage.

### 7.3 `customer_request_actions`

**Purpose:** Append-only state/action evidence for one Customer Request.

| Column | Null? | Meaning / relationship |
|---|---:|---|
| `id` | No | PK |
| `request_id` | No | FK to Customer Request |
| `snapshot_id` | Yes | FK to relevant Request Snapshot |
| `action_code` | No | `SUBMIT`, `RETURN`, `RESUBMIT`, `APPROVE`, `APPROVE_WITH_CHANGES`, `REJECT`, or `CANCEL` |
| `action_by`, `action_at` | No | Actor/time |
| `from_status`, `to_status` | No | State transition evidence |
| `remarks` | Yes | Action remarks; mandatory for Return under current flow |

**Rules:** Actions are never updated/deleted as ordinary workflow operations. Autosave does not create `SAVE_DRAFT` actions. Every Return carries its own remarks; no field-level `customer_request_review_findings` table is required.

## 8. Request state machine

| Current state | Action | Next state | Snapshot/evidence |
|---|---|---|---|
| New | Create | `DRAFT` | Request row; no workflow action required |
| `DRAFT` | `SUBMIT` | `SUBMITTED` | New `MAKER_SUBMISSION` snapshot and action |
| `DRAFT` | `CANCEL` | `CANCELLED` | Action; Maker only |
| `SUBMITTED` | `RETURN` | `RETURNED` | Action with remarks; submitted snapshot unchanged |
| `RETURNED` | `RESUBMIT` | `SUBMITTED` | New `MAKER_SUBMISSION` snapshot and action |
| `SUBMITTED` | `APPROVE` | `APPROVED` | Action references exact Maker snapshot; atomic publish |
| `SUBMITTED` | `APPROVE_WITH_CHANGES` | `APPROVED` | Derived `AUTHORITY_APPROVED` snapshot and action; atomic publish |
| `SUBMITTED` | `REJECT` | `REJECTED` | Action; terminal |

`RESUBMIT` and `APPROVE_WITH_CHANGES` are actions, not statuses. `UNDER_REVIEW` and `WITHDRAWN` are not used. Maker cannot cancel a `RETURNED` request. Rejected requests are not reopened or copy-resumed; later onboarding begins a new request.

### 8.1 Example journey

1. Maker creates `RQ-101`; status is `DRAFT`, and `draft_data` is editable.
2. Submit copies the exact Draft to Snapshot 1 (`MAKER_SUBMISSION`) and moves the request to `SUBMITTED`.
3. Authority returns it with remarks; status becomes `RETURNED`, while Snapshot 1 stays immutable.
4. Maker corrects the same Draft and resubmits; Snapshot 2 (`MAKER_SUBMISSION`) is created and status returns to `SUBMITTED`.
5. Authority either approves Snapshot 2 exactly or creates Snapshot 3 (`AUTHORITY_APPROVED`, `source_snapshot_id = Snapshot 2`) for an authorized approve-with-changes outcome.
6. The approved snapshot is published atomically to the operational Customer tables and the request becomes `APPROVED`.

## 9. JSONB rationale

`draft_data` and `submitted_data` are bounded Customer-request payloads, not generic settings bags or substitutes for operational relational tables.

- One request has one current editable Draft, so a separate Draft table adds no independent identity or lifecycle.
- Request types have heterogeneous shapes; `NEW_CUSTOMER` may be complete while amendments are narrow deltas.
- Immutable JSONB snapshots preserve exactly what the Maker submitted and what Authority approved without maintaining parallel typed history tables for every child collection.
- Historical workflow evidence is normally retrieved per request, while operational reporting uses typed approved Customer tables.
- Final financial transaction truth remains typed/snapshotted by the owning Sales Order/Billing design, not by these JSONB request tables.

Application/backend validation must validate the request-type payload before Submit and again before publish. Database constraints continue to protect approved/current relational invariants.

## 10. Approval and publication

- Maker and approver must differ for the submitted request.
- Authority may edit business-entered data only with the required permission and may not edit system-controlled fields or transform the request into an unrelated legal Customer.
- `APPROVE_WITH_CHANGES` preserves the original Maker snapshot, the exact Authority-approved snapshot, actor, action, and remarks/reason evidence.
- Publication revalidates Company/Tenant scope, request status, authority, readiness, current target, identifiers/GSTINs, and Customer Code allocation where applicable.
- Approved outcome, action evidence, operational writes, and `NEW_CUSTOMER` code allocation must commit atomically.
- Idempotency for Submit, approval, publication, and code allocation is a later API/backend integrity requirement, not an unresolved business rule; exact mechanisms are not designed here.

## 11. Duplicate control and concurrent amendments

- Temporary duplicate `DRAFT` requests may exist.
- Submit performs hard validation against approved/live Customers and applicable pending submitted Customer onboarding requests using normalized identifiers such as PAN/GSTIN.
- Approval/publication performs the validation again inside the publication transaction.
- Approved/current Company-scoped identifier and normalized GSTIN uniqueness remains database-enforced.
- `customer_identifier_claims` is not part of MVP. Race-condition handling is an implementation invariant for transactional backend/database design, not a new business table in this design.
- For an existing Customer, at most one request in `DRAFT`, `SUBMITTED`, or `RETURNED` may exist at a time. Parallel amendment handling is outside MVP.

## 12. Customer Code configuration direction

Customer Code is a Company Configuration responsibility:

~~~text
Customer Code = Company-configured prefix + Company-scoped sequential number
~~~

- Company chooses the prefix and numeric padding/digit length.
- Sequence starts at 1, is scoped per Company, and does not reset automatically.
- Code is allocated only when a `NEW_CUSTOMER` is successfully approved/published.
- Existing Customer amendments never generate a new code.
- Allocated code remains stable.

Example: prefix `CUST-`, digits `5` produces `CUST-00001`, `CUST-00002`.

Allowed prefix validation, padding overflow behavior, and whether code setup blocks Company activation or only Customer approval remain physical/configuration review details; no annual/monthly/FY reset is introduced.

## 13. Historical integrity

| Concern | Owner |
|---|---|
| Current approved Customer state | Operational Customer tables |
| Current editable proposal | `customer_requests.draft_data` |
| Exact submitted/approved request payload | `customer_request_snapshots` |
| Workflow actor/state/remarks evidence | `customer_request_actions` |
| Effective Customer address history | `customer_location_versions` |
| General actor/before-after evidence | Shared audit capability |
| Final invoice/address/statutory/term/recipient truth | Owning finalized transaction/delivery snapshot |

Snapshots do not replace audit, Location versions, or financial transaction snapshots. Customer name does not require a separate name-version table in this MVP.

## 14. REVIEW, OPEN, and deferred items

| Item | Status | Boundary |
|---|---|---|
| Class A/B/C change-control model | `REVIEW` | Do not create configuration tables yet |
| Approval-required vs direct-edit-allowed Class B fields | `REVIEW` | Authorization/business-policy decision |
| Post-approval Contact change approval | `REVIEW` | `ADD_CONTACT` request applies only if later required |
| GST-to-Location mapping change approval | `REVIEW` | Physical mapping stays on Location version |
| Contact recipient precedence, TO/CC/BCC, fallback, and priority | `REVIEW` | Delivery/Reminder design |
| Contact Detail verification and WhatsApp/provider behavior | `REVIEW` | Not in database freeze |
| Shared identifier-type naming/applicability | `REVIEW` | Reuse existing concept; no duplicate table |
| Geography physical FK naming (`country_id`/`state_id`) | `REVIEW` | Align with existing shared reference keys |
| `document_type_id` reference target | `REVIEW` | Reuse approved reference; no new engine/table now |
| Supporting-document matrix and non-India rules | `REVIEW` | No large rule engine |
| Customer reactivation | `OPEN` | Same identity/code vs controlled replacement unresolved |
| Credit Limit/group exposure | `DEFERRED` | Outside MVP |
| Shared Party/Vendor/Contact master | `DEFERRED` | Future architecture only |

## 15. Superseded design elements

The following are no longer active design alternatives:

- fixed 15-table typed relational revision/publish architecture;
- three mutually exclusive workflow persistence options;
- `customer_revisions` / `customer_request_revisions` and typed revision children;
- `customer_approval_submissions` / `customer_approval_decisions` for this Customer flow;
- `customer_identifier_claims`;
- `customer_request_drafts`;
- `customer_request_review_findings`;
- `customer_communication_endpoints` name, replaced by `customer_contact_details`;
- `customer_ar_communication_purpose_assignments` name, replaced by `customer_contact_purposes`;
- physical address columns on `customer_locations` when `customer_location_versions` is used;
- direct PAN/CIN/LLPIN columns on `customers`;
- Customer Code as an unresolved manual-versus-generated policy;
- automatic direct-edit treatment for all post-approval Contact changes.

[Customer Onboarding Workflow Persistence Options](CUSTOMER_ONBOARDING_WORKFLOW_OPTIONS.md) is retained only as a historical alternatives record. Earlier changelog entries remain intact for traceability and are superseded by the dated change entry adopting this current working design.

## 16. Freeze gate

Before implementation, reviewers must approve this working design, resolve the reference-alignment items needed by physical FKs, define exact constraints/indexes/data types, and retain all explicitly `REVIEW`, `OPEN`, and `DEFERRED` boundaries. No API contract, migration, or model should be derived as approved merely because this document now supplies a coherent 14-table candidate.
