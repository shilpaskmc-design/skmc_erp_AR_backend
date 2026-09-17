# Company Configuration Requirements

## 1. Purpose

This document defines the business and functional requirements for configuring a Company in SKMC ERP SaaS. It refines the baseline in `docs/PRODUCT_OVERVIEW.md` so that a Company Configuration domain model can be prepared next. It does not define a physical data model, APIs, implementation, or detailed requirements for downstream transaction modules.

Documentation sequence:

`PRODUCT_OVERVIEW.md` → Company Configuration Requirements → Company Configuration Domain Model → Database Design → API / Implementation Design

## 2. Scope

**Requirement — MVP**

Company Configuration establishes reusable Company masters, defaults, and policies needed before normal AR operations.

| In scope | Outside this document |
|---|---|
| Tenant and optional Organisation context; Company identity and lifecycle | Physical data structures, persistence, APIs, and implementation |
| Locations, GST registrations, LUTs, and fiscal configuration | Full statutory tax interpretation or tax-calculation engine |
| AR document numbering and business nature | Detailed Billing, Credit Note, Payment, or Reminder Engine rules |
| Service and Product/SKU catalogue setup | Customer-specific pricing and commercial terms |
| Management-reporting dimensions | Generic or arbitrary cost-centre framework |
| Currencies, FX configuration, and Company Bank Accounts | Sales-Order recurrence schedules and scheduler behaviour |
| Company-created Account Hierarchies/Groups, stable GL Accounts, effective Revenue/Tax mappings, default Receivable GL, and Bank-to-GL association | Full General Ledger posting, classifications, reconciliation, accounting correction/reclassification, and inter-unit clearing design |
| Reusable tax, document-presentation, email, and reminder defaults | Full template builder or advanced approval workflow builder |
| Review, activation, historical integrity, and audit expectations | Organisation-level configuration inheritance |

Tenant remains the data-isolation boundary; Company Configuration is Company-wise. An optional Organisation groups Companies but does not supply inherited configuration in the MVP.

## 3. Core vs AR-Specific Configuration Boundary

**Requirement — SYSTEM RULE**

Company Configuration must not be treated as one AR-only settings area. Shared facts about the Company must be reusable by future modules, while AR-only policies stay within the AR configuration boundary.

| Area | Conceptual ownership | Rationale |
|---|---|---|
| Tenant and optional Organisation relationship | Core / Shared | Establishes SaaS isolation and business grouping. |
| Company identity, legal details, lifecycle, and locations | Core / Shared | Describes the legal/business entity across modules. |
| GST registrations and LUTs | Core / Shared | Reusable legal and statutory Company information. |
| Fiscal pattern and financial periods | Core / Shared | Shared financial time context. |
| Business nature | Core / Shared | Describes whether the Company provides Services, Goods, or Both. |
| AR document numbering | AR-Specific | Controls PI, TI, DN, and CN numbering. |
| Billing, receipt, and reporting currency enablement | AR-Specific usage | Enables currencies for AR transaction purposes. |
| AR FX purposes and policies | AR-Specific | Controls Billing, Reporting, and potentially Receipt FX use. |
| Invoice bank-account selection behaviour | AR-Specific usage | Uses configured Company Bank Accounts during billing. |
| Billing tax configuration | AR-Specific usage | Supplies reusable inputs to Billing without defining the full tax engine. |
| Financial-document presentation and email delivery | AR-Specific | Controls AR document output and delivery. |
| AR reminder defaults | AR-Specific | Supplies defaults to the separate Reminder Engine. |
| Service catalogue platform suggestions vs Company adoption | **Boundary TBD** | Business behaviour is confirmed; exact ownership awaits domain modelling. |
| Company Bank Accounts | **Boundary TBD** | Accounts may be shared Company masters while invoice selection is AR-specific. |
| Tax families, HSN/SAC, rates, treatments and statutory codes | **Confirmed boundary** | Controlled Tax Types identify GST/TDS/TCS/VAT/CESS families; Company HSN/SAC, numeric rates, eligible mappings, Tax Treatments, COMPONENT codes, SECTION codes, and code rates remain distinct. |
| Company CoA and shared accounting structure | Core / Shared accounting configuration | Owns stable Company GL identities, hierarchy/Group structure, default Receivable GL configuration, direct Bank GL association, and shared accounting/statutory identities. |
| AR Revenue and Tax GL mapping/resolution | AR accounting configuration | Owns effective Revenue and Tax GL mappings, invoice-context Revenue/Tax resolution, and preservation of resolved GL references in finalized AR transactions. |
| Teams and management-reporting setup | **Boundary TBD** | Team references may be shared, while current reporting use is AR-oriented. |

Changing the conceptual boundary later must not expose one Tenant's private data to another Tenant.

## 4. Company Configuration Journey

**Requirement — MVP**

The setup journey must cover the following conceptual sequence. Presentation may group steps, but it must not omit applicable configuration.

```mermaid
flowchart TD
    A[Company Identity] --> B[Locations / GST / LUT]
    B --> C[Fiscal Configuration]
    C --> D[AR Document Numbering]
    D --> E[Business Nature]
    E --> F[Service / Product Catalogue]
    F --> G[Cost-Centre / Management Reporting]
    G --> H[Currency and Exchange Rates]
    H --> I[Bank Accounts and Tax]
    I --> J[Accounting Setup / Chart of Accounts]
    J --> K[Document Presentation]
    K --> L[Email and Reminder Defaults]
    L --> M[Review / Activation]
```

Company Configuration supplies reusable setup to the downstream flow: Customer → Sales Order → Billing → Approval → Invoice Delivery → Payment → Receivables → Reminders → Reporting.

## 5. Company Identity

**Requirement — CONFIGURABLE**

Company administrators can maintain the identity and contact information of the legal/billing entity.

| Information | Requirement | Classification |
|---|---|---|
| Legal Company Name | Identifies the legal entity. | MVP |
| Display / Short Name | Provides a shorter business-facing name. | CONFIGURABLE |
| Company Code | Optional business-facing identifier; it is not a database primary key. | CONFIGURABLE |
| Entity Type | Selects the Company's primary legal form from jurisdiction-scoped, platform-managed reference data; it is not Company-entered free text. | CONFIGURABLE |
| Company Legal Identifiers | The system shows jurisdiction- and Entity-Type-applicable identifier inputs such as PAN, CIN, or LLPIN; values are stored as Company identifier records rather than permanent identifier-specific Company columns. | CONDITIONAL |
| MSME applicability/details | Captured where applicable. | CONDITIONAL |
| Country | Establishes Company country context. | MVP |
| Base Time Zone | Supplies Company-local time for scheduled behaviour. | MVP |
| Company Email, Phone, Website | Maintains Company contact channels; exact activation requirements remain TBD. | CONFIGURABLE |
| Company Logo | Reusable Company identity asset. | CONFIGURABLE |
| Company Status | Supports Active and Inactive lifecycle states. | MVP |

**Requirement — SYSTEM RULE**

- Company is the legal, billing, tax, and accounting entity and retains direct authoritative ownership by exactly one Tenant.
- Organisation is an optional non-legal grouping layer within that Tenant and provides no current configuration inheritance.
- Company saves the selected `entity_type_id` from the controlled options applicable to its country/jurisdiction. Normal Company users cannot create arbitrary Entity Types through typed or search text.
- Entity Type selection determines which controlled legal Identifier Types are shown and whether each is REQUIRED or OPTIONAL. No rule means the identifier is normally hidden/not applicable for that Entity Type.
- The system and UI consume the same platform-managed applicability rules. Normal Company users enter identifier values but cannot create Identifier Types or change applicability rules.
- The complete statutory applicability matrix and identifier-specific format/normalization rules remain OPEN; illustrative PAN/CIN/LLPIN examples are not the full authoritative India matrix.
- Platform reference-data administration may add supported foreign-jurisdiction legal forms later without changing the Company schema.
- Company legal name is the current Company-level legal name. Legal-name history must remain recoverable through separate Company profile history; current-row timestamps and generic Audit are not substitutes for effective profile versioning.
- Making a Company inactive must not remove or hide its historical transactions.

**Acceptance Criteria**

- An administrator can capture the applicable identity information and Company-local time zone.
- Entity Type is selected from canonical jurisdiction-compatible options, and only its stable reference is saved.
- Company Code may be omitted and is treated only as a business identifier.
- Company can move through Active/Inactive lifecycle without loss of historical access.
- Private Company data remains within its Tenant boundary.

Company Identity follows this flow:

```text
Country
→ Entity Type
→ resolve applicable legal identifiers
→ show only applicable inputs
→ require REQUIRED values and allow OPTIONAL values
→ store the Company's identifier values in company_identifiers
```

Entity Type describes what legal form the Company is. Identifier Type describes what kind of legal registration/identity number is being collected. Company Identifier is the actual value belonging to that Company. GSTIN remains part of GST Registration architecture rather than this generic Company legal-identifier flow.

## 6. Company Locations

**Requirement — CONFIGURABLE**

A Company can maintain multiple stable physical/business Locations, such as a Noida Registered Office, Mumbai Branch, or Bangalore Warehouse. A Location stores its current usable address and configuration and belongs directly to the Company; Organisation grouping is unrelated to Location configuration.

One Company Location represents one physical/business place. The same Location may serve more than one applicable fixed purpose. For example:

```text
Noida Office
├── Registered Office
├── Corporate Office
└── Billing Office
```

This is one Location with several purposes, not three duplicate Location records. The current model uses the defined fixed purposes and does not introduce a generic Location-purpose framework or mapping table.

**Requirement — SYSTEM RULE**

- Exactly one active Registered Office exists per Company.
- The at-least-one Registered Office rule applies when Company setup is completed/usable; an incomplete draft need not be forced into completed-state behavior.
- One Company Location may carry more than one applicable fixed purpose.
- Non-Registered-Office purposes may repeat across different Locations where applicable; they are not implicitly unique per Company.
- A billing or operational address may differ from the Registered Office.
- A Company Location may exist without a GST registration.
- A Location belongs to zero or one GST Registration through its nullable direct association.
- A GST-linked Location's State/UT jurisdiction must be compatible with the GST Registration, and this rule must be protected beyond frontend filtering.
- At most one active Location mapped to a GST Registration is marked as that GSTIN's default. Where the product flow requires a default, setup validation ensures one exists. The default is only a preselection aid; transactions may still select another eligible Location explicitly.
- A Location may optionally belong to one Location Cost Center. The Location and Cost Center must belong to the same Company, and a Location does not automatically become a Cost Center.
- A historically used location is deactivated rather than deleted.
- Location address and jurisdiction history is effective-dated for the same stable Location. The version history is deliberately narrow: it does not imply historical GST Registration, Cost Center, purpose, name, default, or status mapping.
- Changing a current Location or address must not rewrite historical financial documents. Finalized documents retain their own transaction-time address snapshots rather than being reconstructed from current or versioned Location masters.
- Company Location represents a legal/business location, not a logged-in user's physical work location.

**Acceptance Criteria**

- A Company can maintain more than one location.
- One physical Location can be assigned several applicable fixed purposes without duplicating its address into separate Location records.
- More than one Location can carry the same non-Registered-Office purpose where applicable.
- The system prevents a Company from having zero or more than one active Registered Office once the applicable setup is active.
- A location can be saved without a GST registration.
- Historically referenced locations cannot be hard-deleted through normal configuration.
- The system prevents more than one active default Location for the same GST Registration.
- A mapped Location's state/jurisdiction must be compatible with its GST Registration.
- The system can resolve the address/jurisdiction effective for a Location on a date without treating Location versions as full configuration history.

## 7. GST Registrations

**Requirement — CONDITIONAL**

A Company can maintain multiple GST registrations when GST registration is applicable.

The Company legal name and GST-registration legal name are distinct current facts. A Company-name change and amendment of each GST Registration may take effect on different dates. The registration-specific legal name therefore must not be treated as redundant or automatically overwritten from the Company master.

**Requirement — SYSTEM RULE**

- Each GST registration belongs to one state/jurisdiction.
- GSTIN is stored in trimmed canonical uppercase form, is subject to statutory validation, and is unique across the ERP.
- Each usable registration retains its controlled GST-specific Registration Type reference and explicit State/UT jurisdiction. GST Registration Type is separate from the generic Tax Type/family master; exact supported Registration Type values, statutory status values, and physical State reference remain open for dedicated review.
- One GST registration may be associated with multiple Company Locations.
- A Company Location need not have a GST registration.
- Where applicable, one and only one active mapped Location is the default for that GST Registration.
- The seller GSTIN used by Billing is selected or derived from the billing workflow, never from the logged-in user's physical location.
- The MVP does not support multiple active GST registrations for the same Company in the same state. This is an MVP product constraint, not a general legal claim.
- GSTIN-wise Bank Account routing is not required in the MVP.
- Company profile history and GST Registration history are preserved separately. Finalized invoices retain the seller legal name, GSTIN, address, and registration context actually used at finalization rather than rebuilding them from current masters.

**Acceptance Criteria**

- A Company can configure GST registrations for different states/jurisdictions.
- Multiple Company Locations can be associated with one GST registration.
- A GST Registration can have one active default mapped Location without requiring a bridge table.
- The system prevents a second active same-state GST registration for the Company in the MVP.
- Billing can consume seller-GSTIN context without using the user's physical location.
- A Company legal-name update does not erase earlier Company or GST-registration states and does not rewrite seller identity on finalized invoices.

## 8. LUT

**Requirement — CONDITIONAL**

LUT configuration applies to the current without-payment Export/SEZ routes under the current product rule.

| Information | Requirement |
|---|---|
| LUT ARN / Reference | Identifies the LUT. |
| Fiscal period | Establishes the relevant financial period. |
| Status | Identifies whether the LUT is active for use. |
| Validity/context | Captured where applicable. |

**Requirement — SYSTEM RULE**

- At most one active LUT exists for a GSTIN and fiscal period.
- Historical LUT records are preserved.
- LUT document upload is not required in the MVP.
- If LUT document upload is enabled later, the binary is stored through shared `ObjectStorage`, PostgreSQL retains its `stored_files` metadata, and `company_luts` references that stable file identity through a typed FK. LUT bytes and temporary/signed URLs do not belong in the LUT configuration row.
- EXPWOP and SEZWOP require the applicable valid LUT for the seller GST Registration and fiscal period before final billing.
- EXPWP and SEZWP do not require LUT merely because the transaction is Export or SEZ.
- Missing required LUT blocks finalization. Management/legal policy may relax this product rule later.

**Acceptance Criteria**

- An administrator can configure the applicable LUT reference against a GST registration and fiscal period.
- The system does not allow two active LUTs for the same GSTIN and fiscal period.
- Required LUT absence blocks final billing for EXPWOP and SEZWOP.
- EXPWP and SEZWP are not blocked solely for missing LUT.
- Prior-period LUT history remains available.

## 9. Fiscal / Financial Period Configuration

**Requirement — CONFIGURABLE**

A Company defines one normal recurring fiscal-year start pattern using a start day and month. This pattern is separate from the actual dated Financial Year records created for the Company.

Example: a start of 1 April can derive 1 April 2026 through 31 March 2027, followed by 1 April 2027 through 31 March 2028.

**Requirement — SYSTEM RULE**

- Actual period dates are authoritative.
- Each Financial Year has a required human-readable display code such as `2026`, `2026-27`, or `FY 2026-27`; the actual dates remain the source of truth.
- Short or transition Financial Years are supported explicitly rather than inferred later from the current normal pattern.
- The system can calculate and propose/create the next expected Financial Year from the recurring pattern, including when a future transaction date lacks an applicable configured FY.
- Creating the next Financial Year does not close or lock the previous Financial Year, prevent transactions in it, or change accounting-period state.
- Only authorized users may adjust future fiscal setup.
- Changing the recurring fiscal pattern affects future proposals only and must not rewrite existing Financial Years or their transaction associations.
- Financial Years for the same Company must not overlap. Gaps are handled as configuration/workflow issues rather than being unconditionally forbidden in storage.
- A transaction date must resolve to exactly one configured Financial Year; otherwise the applicable workflow proposes/creates the expected FY or blocks until setup is completed.
- Financial Year, accounting close, and accounting lock remain separate concepts. Accounting close/lock belongs to future Accounting design.

**Acceptance Criteria**

- An administrator can define the fiscal start day and month.
- The system can derive consecutive annual periods from the pattern.
- The normal pattern need not be re-entered every year.
- An administrator can record an explicit short/transition Financial Year.
- The system prevents overlapping Financial Years for the same Company.
- Creating a future Financial Year leaves the prior Financial Year's close/lock state unchanged.
- An authorized user can make a controlled change to future fiscal setup.
- Historical periods and transaction associations remain unchanged after a pattern change.

## 10. AR Document Numbering

**Requirement — CONFIGURABLE**

The Company can configure numbering/series for Proforma Invoice (PI), Tax Invoice (TI), Debit Note (DN), and Credit Note (CN).

Numbering may vary by Company, fiscal period, seller GST registration, and parallel series where required. Prefix, format, sequence behaviour, and fiscal rollover are configurable; suffix is not required currently.

**Requirement — SYSTEM RULE**

- All four AR document types require numbering.
- A final financial document number is assigned only after approval/finalisation.
- A consumed final number is never reused after cancellation.
- Parallel series retain independent counters, and final allocation must atomically consume the selected series so retries cannot allocate a second number.
- Current eligible-series behavior remains: one eligible series is auto-selected, multiple eligible series require user selection, and no eligible series blocks finalization.
- Eligibility conditions use a controlled condition model rather than executable rules. Exact operator vocabulary, multiple-condition AND/OR behavior and current priority semantics remain OPEN.
- At year-end, the system can propose the next series/prefix/format for authorized confirmation or change.

**Acceptance Criteria**

- Authorized users can configure applicable PI, TI, DN, and CN series.
- More than one parallel series can be configured where required.
- Draft documents do not consume final numbers before approval/finalisation.    
- A cancelled final number cannot be reassigned.
- Fiscal rollover can propose new numbering configuration without silently changing historical numbering.

## 10A. Payment Terms

**Requirement — CONFIGURABLE**

A Company can maintain reusable `IMMEDIATE` and `NET_DAYS` Payment Terms, including at most one active default. Immediate terms use zero credit days; Net Days terms use a positive number of credit days.

**Requirement — SYSTEM RULE**

- A selected Payment Term, credit-days value and derived due date are preserved by the owning Sales Order/invoice according to its snapshot rules.
- A Payment Term marked as the Company default must be ACTIVE. Inactivating the current default must clear its default flag or move the default to another ACTIVE term; the product does not require that a default always exist.
- Changing or inactivating current Payment Term configuration must not recalculate previously approved or finalized transactions.
- Historically used terms are retained rather than hard-deleted.
- Installment schedules are outside the current Payment Term configuration.

## 11. Business Nature

**Requirement — CONFIGURABLE**

During Company Configuration, the Company identifies what it sells or provides:

| Selection | Required catalogue setup |
|---|---|
| Services | Service Catalogue |
| Goods | Product Catalogue |
| Both | Service Catalogue and Product Catalogue |

**Acceptance Criteria**

- An administrator can select Services, Goods, or Both.
- The setup journey requires only the catalogue paths applicable to that choice.
- A later change does not rewrite historical document lines or descriptions.

## 12. Service Catalogue

**Requirement — MVP**

Services use the conceptual structure **Service Category → Service Type**. Service Type is the actual billable service.

Possible Service Type information includes Service Name, optional internal code, Service Category, description, optional UOM, Company-configured SAC, current/default selected eligible GST rate, GST/Tax Treatment, optional Business Segment, TCS applicability-check requirement, and Active/Inactive status.

**Requirement — CONFIGURABLE**

- A Company can select/adopt services it sells from platform suggestions.
- A Company can create its own custom services.
- A Company can apply its own internal code, description, SAC/configuration, and lifecycle state.

**Requirement — SYSTEM RULE**

- A Tenant or Company's private custom service must not automatically become visible to another Tenant.
- Historically used Service Types are deactivated rather than treated as if they never existed.
- Service Type directly references a Company-configured SAC and one current/default selected eligible rate. The selected rate is stored on the Service Type and must be valid through the Company SAC-to-rate relationship; no separate service-tax assignment history is required for MVP.
- The Service Category, SAC, and optional Business Segment must belong to the same Company as the Service Type. A Service Type has at most one current Business Segment through its nullable direct reference.
- `tcs_check_required` requires Billing to make/perform the applicable TCS decision; it does not automatically charge TCS.

The platform may offer canonical/suggested Service Categories and Service Types. Exact ownership between platform definitions, Company adoption, and Company-specific configuration is **Boundary TBD** for domain modelling.

**Acceptance Criteria**

- A Services or Both Company can configure its billable Service Types by adoption or custom creation.
- Company-specific configuration does not alter the platform suggestion for other Companies.
- Private custom services stay within their Tenant boundary.
- Inactive services remain identifiable in historical transactions.

## 13. Product / SKU Catalogue

**Requirement — MVP**

Goods use the conceptual structure **Product Category → Product → SKU**. SKU is the actual sellable variation.

SKU information may include SKU Code, Product, Company-configured HSN, current/default selected eligible GST rate, GST/Tax Treatment, UOM, description, optional Business Segment, TCS applicability-check requirement, and Active/Inactive status.

**Requirement — CONFIGURABLE**

- Platform-level Product Category suggestions may be offered.
- Actual Products and SKUs are generally Company-owned.
- A Goods or Both Company can configure the Products and SKUs it sells.

**Requirement — SYSTEM RULE**

- Customer-specific pricing belongs to Sales Order/commercial setup, not permanent Company Catalogue setup.
- Historical transactions retain the relevant sold-item information even if catalogue data changes or becomes inactive.
- SKU directly references a Company-configured HSN and one current/default selected eligible rate. The selected rate is stored on the SKU and must be valid through the Company HSN-to-rate relationship; no separate SKU-tax assignment history is required for MVP.
- The Product, HSN, and optional Business Segment must belong to the same Company as the SKU. A SKU has at most one current Business Segment through its nullable direct reference.
- `tcs_check_required` requires Billing to make/perform the applicable TCS decision; it does not automatically levy TCS.

**Acceptance Criteria**

- Applicable Companies can maintain Product, SKU, HSN, UOM, description, and lifecycle information.
- Company-owned Products/SKUs are not exposed across Tenant boundaries.
- Company Catalogue setup does not become the source of customer-specific pricing.

## 14. HSN / SAC Classification

**Requirement — CONFIGURABLE**

A Company configures the HSN/SAC codes relevant to its business. The MVP does not require copying a global catalogue of thousands of unrelated codes into each Company. This Company-owned concept is `company_hsn_sac_codes`; it is separate from the controlled `tax_types` family master.

**Requirement — SYSTEM RULE**

- HSN/SAC is an item classification, not a Tax Type, Tax Treatment, or permanent tax-rate assignment.
- A Company-configured HSN/SAC may map to multiple eligible controlled GST rates through effective-dated Company HSN/SAC-to-rate relationships.
- Service Type references a Company-configured SAC; SKU references a Company-configured HSN. Neither stores an uncontrolled percentage as text.
- Service Type/SKU stores its one current/default selected eligible rate directly; Billing revalidates that selection against the dated eligible mapping.
- GST, TDS, and TCS applicability/rules remain conceptually separate from HSN/SAC. TDS/TCS stay section-based and do not use the GST HSN/SAC-rate mapping.
- The same classification may receive different tax treatment by effective date or transaction context.
- Historical approved financial documents preserve the classification and tax treatment actually used.

Platform suggestions may assist entry, but each selected classification used by the catalogue is Company-configured. Detailed transaction applicability and calculation belong to Billing/Tax specifications.

The current `company_hsn_sac_codes` design is India-first. Generalizing it to foreign item-tax classification schemes remains DEFERRED until foreign-seller requirements are approved; current Company setup does not introduce a generic classification engine.

**Acceptance Criteria**

- A Company can configure a relevant HSN/SAC directly, with controlled suggestions assisting entry where available.
- Changing a tax rule does not change the meaning/history of an approved document's stored treatment.
- Configuration does not force one permanent GST, TDS, or TCS rate onto an HSN/SAC.
- Service Type rejects HSN and SKU rejects SAC.

## 15. Cost-Centre / Management Reporting

**Requirement — CONFIGURABLE**

A Company chooses whether Cost Center reporting is enabled. If enabled, a completed usable configuration selects one or more of the three current supported bases: Business Segment, Team, and Location. Different Companies may enable different combinations, or disable Cost Center reporting completely.

The configuration flow is:

1. Enable or disable Cost Center reporting.
2. If enabled, choose Business Segment, Team, Location, or any combination of them.
3. Show only the selected setup sections.

The UI is driven by `company_cost_center_settings`: `business_segment_enabled = true` shows Business Segment setup, `team_enabled = false` hides Team setup, and `location_enabled = true` shows Location Cost Center setup. Existing inactive or previously configured master rows do not enable a basis; the settings row is authoritative. Whether an enabled but incomplete draft may temporarily be saved without a selected basis remains OPEN, but such a draft is not a completed usable configuration.

**Requirement — SYSTEM RULE**

Business Segment, Team, and Location are independent reporting choices. Business Segment is not assumed to be the parent of Team or Location.

The current Cost Center configuration is dynamic across the supported Business Segment, Team and Location bases. It is not a generic user-defined accounting-dimension engine.

The bases remain separate business entities because their behavior differs: Business Segments relate directly to Service Types and SKUs, Teams have effective-dated user membership history, and Location Cost Centers group physical Company Locations. No generic `cost_centers`, `cost_center_types`, polymorphic mapping, arbitrary dimension-value, or JSON-driven dimension model is introduced.

### 15.1 Business Segment

**Requirement — MVP**

Business Segment is a management-reporting bucket and is not the same as Service Category or Product Category.

- A Service Type or SKU may directly reference one Business Segment or no Business Segment.
- The same Service Type or SKU cannot belong to multiple current Business Segments.
- The referenced Business Segment must belong to the same Company as the Service Type or SKU.
- Historically used Business Segments are inactivated rather than deleted.

**Acceptance Criteria**

- An administrator can maintain Company-owned Business Segments and directly associate applicable Service Types/SKUs.
- The system prevents a Service Type/SKU from having more than one current Segment and rejects cross-Company references.
- Segment deactivation preserves historical references.

### 15.2 Team

**Requirement — CONFIGURABLE**

If Team reporting is enabled, Team itself acts as the reporting dimension; no duplicate cost-centre identity is created merely to repeat the Team.

**Requirement — SYSTEM RULE**

- A Team may contain multiple users.
- A user may belong to multiple Companies, but within the applicable Company scope the design intends one active Team membership.
- A Team may span multiple physical Company Locations.
- Team is currently a billing/header-level reporting dimension, not an invoice-line-level dimension.
- Authentication identities may come from an external IAM system such as Keycloak; ERP references business identity/team membership without owning passwords.
- Team is a Company business identity, not an IAM group. A Team may continue while its membership changes.
- Team changes preserve history by closing the prior effective-dated membership and creating a new membership row; historical membership is not overwritten.
- The physical user/IAM reference and exact database enforcement of the one-active-membership rule remain OPEN until the repository's Company/user membership identity and scope are frozen.
- Historically used Teams are inactivated rather than deleted.

### 15.3 Location Cost Center

**Requirement — CONFIGURABLE**

A Location Cost Center can group multiple Company Locations for reporting.

**Requirement — SYSTEM RULE**

- One Company Location belongs to at most one active Location Cost Center.
- A Location Cost Center may contain many physical Company Locations, and each mapped Location and Cost Center must belong to the same Company.
- A Location Cost Center is not a GST registration.
- During setup, selected GSTINs may be used as a convenience helper to preselect associated Company Locations.
- The user may remove individual preselected locations before saving.
- Final membership is determined by Company Locations, not GSTINs.

**Acceptance Criteria**

- An administrator can group multiple Company Locations into one Location Cost Center.
- The system prevents overlapping active Location Cost Center membership for a location.
- GSTIN selection preselects linked locations without making GSTIN the stored business meaning of the grouping.
- The user can refine the preselected list before saving.
- Historically used Location Cost Centers are inactivated rather than deleted.

### 15.4 Future Reporting Bases

**Requirement — DEFERRED**

The current supported Cost Center bases are Business Segment, Team, and Location. If later requirements introduce Department, Project, Region, or arbitrary Company-defined reporting dimensions, a broader accounting/reporting-dimension model may be reviewed then. Generic arbitrary dimensions, advanced custom parameters, and percentage allocation are not current requirements, and the current schema does not claim to support user-created dimensions.

## 16. Currency Configuration

**Requirement — CONFIGURABLE**

The platform maintains a shared Currency reference. A Company selects currencies for three distinct configuration purposes while retaining one primary Base Currency:

| Currency use | Meaning |
|---|---|
| Base / Accounting | Company's primary accounting currency, stored on the Company. |
| Reporting | Additional currencies allowed for management/MIS presentation. |
| AR Billing / Receipt | Currencies explicitly permitted for Billing, Receipt, or both. |

**Requirement — SYSTEM RULE**

- Reporting Currency and AR Currency are separate controls. A Currency may be Reporting-only, Billing-only, Receipt-only, or enabled independently for multiple purposes.
- The Base Currency is already available as the Company's primary reporting/book currency and is not duplicated as an additional Reporting Currency.
- Reporting conversion changes presentation only; it does not change original transaction or book values.
- AR always uses explicit AR Currency configuration. The Base Currency requires its own AR row when it is allowed for Billing or Receipt; setup may propose that row without creating a separate permission path.
- One active default Billing Currency and one active default Receipt Currency may be configured per Company.
- A default Billing Currency must be Billing-enabled, and a default Receipt Currency must be Receipt-enabled.
- An active AR Currency must enable Billing, Receipt, or both. A Currency no longer used for either operation is made inactive.
- Foreign-currency/EEFC Bank Account behavior remains Bank Account configuration; AR Currency configuration only controls operation permission.
- Exchange-rate facts and selection policies remain in their separate FX configuration.

**Acceptance Criteria**

- An administrator can distinguish base, billing, receipt, and reporting currency use.
- Transaction currency choices are restricted to the Company's applicable configured set.
- Currency purpose is preserved rather than treating every enabled currency as interchangeable.
- Reporting selections include Base Currency without requiring a duplicate additional-Reporting row.
- The system prevents an operation default unless that operation is enabled and prevents multiple active defaults for the same operation.
- Reporting conversion leaves original transaction/book values unchanged.

## 17. Exchange Rate Configuration

**Requirement — CONFIGURABLE**

A Company can configure effective-dated exchange-rate facts only for relevant Currency pairs. Reusable Exchange Rate Types are Corporate and Spot. User Fixed is a conditional, transaction-specific override and is not reusable Exchange Rate master data.

Exchange-rate purpose distinguishes Billing, Reporting, and potentially Receipt. Billing and Reporting may intentionally use different rates or policies.

An FX Policy controls the default Exchange Rate Type for each purpose and whether authorized User-Fixed override is supported. `default_rate_type` means the default **Exchange Rate Type** (`CORPORATE` or `SPOT`), not a default Currency, Billing Currency, or Company Base Currency. Currency selection answers which Currency the transaction uses; FX Rate Type selection answers which rate method/source applies.

**Requirement — SYSTEM RULE**

- Authorized Finance/Admin users may override a rate only where permitted.
- For Billing, the policy default is a preselection rather than a forced Rate Type. Corporate and Spot remain selectable, and changing the selection resolves the applicable rate for that selected type.
- User Fixed appears only when the FX Policy permits override and the permission system authorizes the current user. A required override reason must be supplied before Apply/Finalize.
- FX Policy does not store an override role. IAM/RBAC owns authorization.
- The configuration must not force a monthly-only FX model.
- Updating a current rate never rewrites the rate retained by an approved historical transaction.
- Historical approved transactions retain the transaction Currency, Base Currency, actual Rate Type and rate used, and applicable User-Fixed override context/reason.

Detailed Receipt FX policy, rate-date behavior, stale-rate behavior, and Reporting conversion behavior remain **OPEN**. The selectable Billing behavior below is not automatically imposed on Receipt or Reporting.

### FX Policy administration reference

```text
Currency & FX Configuration

Billing FX Policy
Default Rate Type:          [ Corporate ▼ ]
Allow Manual Override:      [ Yes ]
Override Reason Required:   [ Yes ]

Receipt FX Policy
Default Rate Type:          [ Spot ▼ ]
Allow Manual Override:      [ No ]

Reporting FX Policy
Default Rate Type:          [ Corporate ▼ ]
Allow Manual Override:      [ No ]
```

Default Rate Type refers to the default **Exchange Rate Type** (Corporate or Spot), not to a Currency. The configuration conceptually produces one FX Policy row per purpose: `BILLING`, `RECEIPT`, and `REPORTING`.

### Billing FX Details reference

```text
FX Details

Invoice Currency:       USD
Base Currency:          INR

FX Rate Type:           [ Corporate ▼ ]
                        Corporate
                        Spot
                        User Fixed*

Applicable FX Rate:     83.750000
Base Currency Value:    INR 83,750.00

* User Fixed appears only when allowed by FX Policy
  and authorized for the current user.
```

Corporate being the default does not remove Spot from the selector. Switching Rate Type resolves the applicable rate for the selected type. Default means preselection, not mandatory selection.

When User Fixed is available, the Billing reference becomes:

```text
FX Rate Type:           [ User Fixed ▼ ]
FX Rate:                [ 83.850000 ]
Override Reason *:      [ __________________ ]
```

### Billing FX flow reference

```text
Invoice Currency differs from Base Currency
        ↓
Load BILLING FX Policy
        ↓
Preselect default_rate_type
        ↓
Show FX Rate Type selector
        ↓
Corporate / Spot
        ↓
Resolve selected type from exchange_rates

OR

User Fixed
        ↓
Only if policy + user authorization allow
        ↓
Manual rate
        ↓
Reason if required
        ↓
Finalize
        ↓
Snapshot actual applied rate + type + override context
```

**Acceptance Criteria**

- The Company configures only pairs relevant to its allowed transaction/reporting currencies.
- Billing and Reporting rates can differ for the same currencies and effective context.
- Billing users can select Corporate or Spot even when one is preselected by policy.
- User Fixed remains unavailable unless both policy and user authorization permit it.
- Effective-dated rates can change without rewriting approved transaction values.
- Unauthorized users cannot apply an allowed manual override.

## 18. Company Bank Accounts

**Requirement — CONFIGURABLE**

A Company may maintain multiple Currency-specific Bank Accounts, including INR, foreign-currency, and EEFC accounts. Information may include Account Holder, Bank Name, Account Number, Branch, IFSC, SWIFT, IBAN, Account Currency, Account Type, Billing-default indicator, and Active/Inactive status.

For AR use, the ERP may preselect one configured default Bank Account for the applicable Company and Currency, and an authorized user may choose another eligible configured account.

**Requirement — SYSTEM RULE**

- GSTIN-wise Bank Account routing is not required in the MVP.
- At most one active default Billing Bank Account exists per Company + Currency. Separate INR and USD defaults can therefore coexist.
- A default is a preselection only and does not prevent explicit selection of another eligible account.
- A Bank Account may directly reference a same-Company GL Account. That reference may remain incomplete during setup, but an Accounting-integrated operation requiring a Bank GL must block until an active/applicable same-Company GL is assigned.
- Historical approved documents preserve the bank details actually presented.

Whether Bank Accounts are wholly Core/Shared masters or share a core identity with AR-specific usage is **Boundary TBD**.

**Acceptance Criteria**

- A Company can maintain multiple active or inactive configured Bank Accounts.
- Billing can preselect a configured default and permit authorized selection of another configured account.
- The system prevents multiple active Billing-default Bank Accounts for the same Company and Currency.
- The MVP does not require routing an account by GSTIN.
- Later account changes do not alter bank details shown on historical approved documents.

## 19. Tax Configuration

**Requirement — MVP**

Company Configuration establishes reusable inputs required by Billing for HSN, SAC, GST, TDS, and TCS while keeping each tax concept explicit.

**Requirement — CONFIGURABLE**

- Controlled Tax Types identify broad families such as GST, TDS, TCS, VAT and CESS; they do not store HSN/SAC, percentages, statutory components, or sections.
- The Company can maintain applicable Company HSN/SAC codes without receiving a full national catalogue.
- Applicable Company HSN/SAC-to-GST-rate relationships can vary by effective date and restrict catalogue/Billing choices.
- Ordinary reusable item/supply rates are separate from effective statutory SECTION/case rates. GST HSN/SAC eligibility uses ordinary Tax Rates; TDS/TCS section cases use Tax Statutory Code Rates and do not reference an ordinary Tax Rate merely because the percentage matches.
- Controlled GST/Tax Treatment uses `TAXABLE`, `NIL_RATED`, `EXEMPT`, or `NON_GST`; it is not a numeric Tax Rate Type. Numeric `0%` does not imply one of these treatments.
- Reusable TDS/TCS reference configuration may identify applicable sections/codes and rates without requiring advanced threshold or cumulative automation in Company Configuration.

**Requirement — SYSTEM RULE**

- Tax Type, Company HSN/SAC, numeric Tax Rate, Company HSN/SAC-to-rate eligibility, Tax Treatment, Tax Statutory Code (COMPONENT/SECTION), and Code Rate are distinct concepts.
- Selecting an item resolves its Company-configured SAC/HSN and eligible rate choices; Billing determines CGST + SGST or IGST from jurisdiction and snapshots the final line values.
- TDS/TCS SECTION codes and their effective rates resolve through the Tax Statutory Code model, never through the GST HSN/SAC-to-rate mapping.
- Active effective periods cannot overlap for the same HSN/SAC-rate relationship or for the same statutory SECTION/logical case.
- Approved financial documents preserve the actual tax treatment used.
- Company Configuration supplies reusable inputs; final transaction applicability and calculation belong to Billing/Tax specifications.

The complete tax-calculation engine and its detailed decision rules are **DEFERRED** to later specifications.

## 20. Accounting Setup / Chart of Accounts

**Requirement — MVP**

Each Company creates or imports its own Account Groups, GL Accounts, and hierarchy. The product does not predefine a Chart of Accounts, groups such as Revenue/Liability/Sale of Services, or GL Account names. A GL Account is a stable posting identity; an Account Group is a non-posting folder/reporting node; a hierarchy is one effective-dated way of arranging both.

### A. Account Hierarchies and Groups

UI flow:

```text
Company Configuration
→ Accounting Setup
→ Account Hierarchies
→ Create/select primary ACCOUNTING hierarchy
→ Create Account Groups
→ Arrange Groups with effective dates
```

- A Company has at most one primary `ACCOUNTING` hierarchy under the current rule.
- Group parentage is effective-dated and preserves old placement.
- A root Group has no effective parent.
- Groups are not posting accounts and store no balances.
- The same GL Account may later appear in a separate `MANAGEMENT` hierarchy without being duplicated.
- Cross-Company/cross-hierarchy relationships, parent cycles, and overlapping effective periods are rejected.

No `parent_group_id` is stored permanently on the Group.

### B. Stable GL Accounts

GL Account form:

- Account Name — required Company-defined display name
- Account Code — optional and unique within Company when supplied
- Valid From / Valid To
- Status — Active or Inactive

The GL Account does not store Account Type, parent, Group, `is_group`, or calculated balance in the current AR foundation. Rename/code changes preserve its stable ID. Used Accounts are never hard-deleted or converted into Groups.

### C. Effective GL Placement

The Company places a GL Account into a Group for an effective period. One GL has at most one Group within one hierarchy on a date, but may have a different placement in another hierarchy.

Example:

```text
ACCOUNTING hierarchy, FY 2026-27:
Sales Export → Sale of Services

ACCOUNTING hierarchy, from 01-Apr-2027:
Sales Export → International Services

Future MANAGEMENT hierarchy:
Sales Export → International Business
```

The stable `Sales Export` GL Account remains unchanged.

### D. Revenue GL Mapping

One effective-dated mapping row contains:

- Supply Type — B2B, B2C, EXPWOP, EXPWP, SEZWOP, or SEZWP
- optional Company HSN/SAC
- Company GL Account
- Valid From / Valid To
- Status

Resolution order:

1. Effective Supply Type + matching HSN/SAC.
2. Effective Supply-Type-only mapping.
3. If neither exists, block finalization rather than guess.

Overlapping periods for the same business condition are rejected. Account names remain Company-defined.

### E. Tax / Statutory GL Mapping

The Company maps a controlled Tax Statutory Code to a GL Account with effective dates:

- GST `COMPONENT`: CGST, SGST, IGST
- TDS/TCS `SECTION`: for example 194C or 194J where applicable

CGST/SGST/IGST are components, not statutory sections. Ordinary GST item rates such as 5%, 12%, or 18% remain separate in the Tax Rate model. The invoice/receipt user does not normally choose the mapped GL manually.

### F. Default Receivable and Bank GL

- Company Accounting Settings stores one current default Receivable GL Account.
- Each Company Bank Account may reference its same-Company GL Account directly.
- Current scope does not add receivable-routing or bank-mapping tables.
- Domestic/Export/customer-category Receivable routing is DEFERRED.

### Complete business flow

```text
COMPANY CONFIGURATION
→ Create ACCOUNTING hierarchy and Groups
→ Create stable GL Accounts
→ Place GL Accounts in Groups for effective periods
→ Configure effective Revenue and Tax/Statutory GL mappings
→ Select default Receivable GL and associate Bank Accounts with GLs
→ INVOICE / RECEIPT
  resolve mappings for transaction date and context
→ preserve resolved GL Account IDs on finalized transactions
```

Examples such as `Sales Domestic`, `Output CGST`, `Trade Receivables`, or `HDFC Bank GL` are illustrations only. Companies choose their own names.

### Split and merge behavior

- **Split:** Keep an old `Product Sales` GL for historical transactions; create `Product Sales Domestic` and `Product Sales Export`; date-end/inactivate the old account for future use as appropriate; change mappings from the approved date. Do not convert the old GL into a Group.
- **Merge:** Keep `Consulting Revenue` and `Advisory Revenue` historically referenceable; create/use `Professional Services Revenue` for future mappings; optionally inactivate the old GLs.
- Historical accounting amounts and resolved account IDs never change because hierarchy or mapping configuration changes.

**Requirement — FUTURE-FRIENDLY**

Future Company self-service import/export should support Account Groups, GL Accounts, Group relationships, and GL-to-Group placements. UUIDs remain internal; external files may use Account Code plus Company/template context after file, conflict, and idempotency rules are approved. Manual SQL/VPS maintenance is not the intended product flow. Import/export and starter-template implementation are DEFERRED.

**Open Accounting Design**

`account_types` and classifications such as ASSET, LIABILITY, EQUITY, INCOME, and EXPENSE are DEFERRED to the full Accounting design. `INTER_UNIT` clearing, posting journals, reconciliation, period closing, accounting correction/reclassification entries, and richer Receivable mapping also remain OPEN/DEFERRED.

**Acceptance Criteria**

- A Company can create its own Accounting hierarchy, Groups, and stable GL Accounts without predefined groups or Account Types.
- Group parentage and GL placement preserve effective history, reject overlaps/cycles, and never mutate GL identity.
- Account and mapping screens reference GL Account IDs rather than hardcoded names/codes.
- Revenue GL Mapping uses the invoice date, already-resolved Supply Type, and optional Company HSN/SAC condition.
- A specific Supply Type + HSN/SAC match takes precedence over a general Supply Type match.
- Missing or ambiguous mappings block validation/finalization instead of choosing a wrong account.
- Tax COMPONENT/SECTION codes resolve configured Company GL Accounts through FKs rather than free text.
- Eligible Customer-Sale documents preserve the resolved default Receivable GL; lines preserve resolved Revenue and Tax GL IDs.
- Bank Accounts reference same-Company GL Accounts directly without another mapping table.
- Hierarchy/mapping changes affect future dates only; historical correction requires a future explicit accounting entry.

## 21. Document Presentation / Branding

**Requirement — CONFIGURABLE**

A Company can configure reusable presentation for PI, TI, DN, and CN. Reusable assets may include Company Logo, Signature, and Stamp. Presentation may control the header, Bill-To/Ship-To, item table, tax section, bank details, terms, signature, and footer.

**Requirement — SYSTEM RULE**

Historical financial documents must remain reproducible and must not change unexpectedly when current assets or presentation settings change.

Logo, Signature, and Stamp binaries use shared object storage and stable `stored_files` identities. Company branding configuration later references those identities through typed FKs; it does not store binary content, arbitrary file paths, or temporary/signed URLs. Server-side template identity remains separate from a generated output PDF artifact.

Branding uses typed `logo_file_id`, `signature_file_id`, and `stamp_file_id` references to same-Company `stored_files` rows. Once branding is used by a published template version, a replacement asset or text configuration creates a new branding row for a new template version rather than changing historical output.

Document templates are versioned Company/document-type configuration over supported server-side `template_key` values. Display choices are explicitly selected during setup and have no assumed boolean defaults; mandatory legal/statutory information remains visible regardless of an optional presentation preference. Whether each Company/document type has exactly one current active template or multiple active choices remains OPEN. Branding may include a Stamp asset, but whether Stamp visibility needs an independent `show_stamp` toggle or is governed by the selected server-side template also remains OPEN. Final PDFs remain immutable stored artifacts outside the branding/template configuration tables.

**Requirement — DEFERRED**

A full drag-and-drop template builder is not part of the MVP. Basic Company/document-type template version identity is part of the current configuration design; advanced template-builder customization, richer version-management workflow, and deeper customization remain deferred to later design.

**Acceptance Criteria**

- An administrator can configure reusable presentation/assets for the current four document types.
- Current setting changes apply according to later document-generation rules without mutating historical approved output.
- MVP setup does not require a generic drag-and-drop builder.

## 22. Invoice Email Delivery Configuration

**Requirement — CONFIGURABLE**

Company-level delivery configuration defaults include automatic sending explicit ON/OFF (default is false), Default Sender Email, Default Reply-To, Default Invoice Email Template, and Default CC. PI, TI, DN, and CN may apply document-specific behaviour or override. Company Configuration stores only delivery defaults.

**Requirement — SYSTEM RULE**

- Automatic send is explicit ON/OFF (default false).
- Manual send can still occur when automatic sending is OFF.
- Actual recipients come from Customer/Contact/document context, not Company Configuration.
- Delivery is asynchronous after financial finalization.
- Provider secrets are external to PostgreSQL (stored in a secret manager, database stores reference only).

**Acceptance Criteria**

- An administrator can explicitly configure automatic sending and maintain delivery defaults.
- Authorized manual sending is allowed even if automatic delivery is off.
- Actual recipients are sourced contextually.
- Delivery intent is asynchronous and independent of the financial finalization transaction.
- Provider secrets are externalized.

## 23. AR Reminder Defaults

**Requirement — CONFIGURABLE**

Company Configuration defines one current default Reminder Policy. This includes an enabled flag (default false) and schedule offsets (signed days relative to due date).

The control hierarchy is **Company → Customer → Invoice**, with Invoice-level control taking highest priority for that invoice. Schedule rows are not copied to each Customer/Invoice.

**Requirement — SYSTEM RULE**

- Runtime stop conditions (e.g., fully paid, cancelled) are evaluated by the Reminder Engine and are not duplicated as Company settings.
- The default reminder policy is a singular Company baseline.

**Requirement — DEFERRED**

Detailed reminder scheduling, evaluation, recipient, and execution behaviour belongs to the separate AR Reminder Engine specification.

**Acceptance Criteria**

- The Company has one current default Reminder Policy with an enabled default of false.
- The reminder schedule uses signed offsets relative to due date.
- Reminder precedence follows Company → Customer → Invoice.
- Runtime stop conditions remain Reminder Engine behaviour.
- Schedule rows are inherited, not copied directly to Customer/Invoice records.

## 24. Recurring Billing Boundary

**Requirement — SYSTEM RULE**

Recurring Billing is a confirmed product capability, but actual recurrence belongs to Sales Order or contract configuration, not to a generic Company Configuration schedule.

Conceptual flow: **Sales Order → recurring terms/schedule → billing generation → approval → invoice delivery**.

Company Configuration may later contain only genuinely reusable prerequisites or defaults if separately confirmed. Detailed recurrence and scheduler rules are **DEFERRED** to the Sales Order/Recurring Billing specification.

## 25. Review / Activation

**Requirement — MVP**

The system allows authorized users to review applicable Company Configuration before activation. Activation readiness distinguishes required, conditional, optional, and unresolved setup without inventing field-level mandatory rules.

| Configuration Area | Required for Activation? | Notes |
|---|---|---|
| Tenant relationship | Required | Every Company operates inside one Tenant isolation context. |
| Organisation relationship | Optional | No MVP inheritance is provided. |
| Company identity minimum | TBD | Legal identity is required conceptually; the exact activation field set is not confirmed. |
| One active Registered Office | Required | Exactly one active Registered Office is the confirmed Company rule. |
| GST registration | Conditional | Applies where the Company is GST-registered/applicable. |
| LUT | Conditional | Required for current EXPWOP and SEZWOP final billing; EXPWP and SEZWP are not blocked solely for missing LUT. |
| Fiscal setup | TBD | Authoritative period context is required for financial activity; whether incomplete setup blocks Company activation itself is not confirmed. |
| AR document numbering | Conditional | Required before finalising each applicable AR document type; whether every series must exist at Company activation is TBD. |
| Business nature | Required | Determines required Service/Product catalogue path. |
| Service Catalogue | Conditional | Required for Services or Both. Exact minimum entries before activation are TBD. |
| Product/SKU Catalogue | Conditional | Required for Goods or Both. Exact minimum entries before activation are TBD. |
| Cost-centre reporting | Optional | Configured only when the Company enables it. |
| Currency setup | TBD | Relevant AR transactions must use allowed Company currencies; the activation gate and exact minimum currency set are not confirmed. |
| Exchange rates | Conditional | Needed only when relevant configured currency purposes require conversion. |
| Bank Accounts | TBD | Company may maintain accounts; activation dependency is not confirmed. |
| Tax setup | Conditional | Applies according to Company and transaction tax context. |
| Accounting setup | No for Company activation; required before applicable invoice finalization | Stable GL Accounts, one default Receivable GL for eligible Customer Sales, and unambiguous date-effective Revenue/Tax GL mappings must cover the resolved context. Hierarchy setup preserves reporting placement but does not change transaction amounts. |
| Document presentation/assets | Optional | Reusable presentation is configurable; full template builder is deferred. |
| Email delivery | Optional | May be OFF; document overrides operate only when applicable. |
| AR reminder defaults | Optional | Reminder is part of the product but Company defaults can be enabled/configured. |

**Acceptance Criteria**

- Authorized users can review readiness before activation.
- The review distinguishes blocking, conditional, optional, and TBD areas.
- Conditional checks are evaluated only when their stated condition applies.
- The system does not infer unconfirmed mandatory identity fields or configuration.

## 25A. Company Access

**Requirement — CONFIGURABLE**

Explicit Company membership is required for a user to access a Company.

**Requirement — SYSTEM RULE**

- Tenant membership alone is insufficient to grant access to every Company within the Tenant.
- `company_user_memberships` table maintains the authorization/data-isolation boundary for Company access.
- IAM/RBAC remains responsible for action permissions.
- There is no duplicate Tenant ID in the Company membership row.

**Acceptance Criteria**

- A user must have an active `company_user_memberships` row to operate within a specific Company context.
- IAM/RBAC controls what the user can do within that authorized Company.

## 26. Historical Integrity

**Requirement — SYSTEM RULE**

Changes to current Company Configuration must not silently change historical approved financial documents.

This applies to Company legal details, addresses, GST details, fiscal periods, document numbering, historically captured Service/Product descriptions, HSN/SAC, tax rates/treatment, resolved GL accounts, exchange rates, bank details, branding/presentation, and email history.

The later domain and database designs will decide what is referenced, versioned, or snapshotted. This document requires the business outcome without selecting a persistence mechanism.

**Acceptance Criteria**

- An approved document remains reproducible with the material values and presentation used at approval/delivery time.
- Current configuration changes do not rewrite historical periods, numbers, rates, classifications, bank details, or output.
- Inactivation of a Company or master does not remove historical transaction access.

## 27. Audit Requirements

**Requirement — SYSTEM RULE**

Configuration changes that affect financial behaviour are auditable. Audit information captures who changed the configuration, when it changed, and what changed.

Audit coverage includes GST, fiscal pattern/period, numbering, exchange rates, tax configuration, Chart of Accounts and account mappings, Bank Accounts, document/email configuration, and cost-centre assignments. The same expectation applies to other configuration changes that materially affect financial output or behaviour.

Audit storage design is outside this document.

**Acceptance Criteria**

- An authorized reviewer can identify actor, timestamp, and change for covered configuration.
- Audit history remains available when current configuration is changed or deactivated.
- Audit evidence does not depend solely on the current value.

## 28. MVP vs Deferred / Extensible Areas

| Classification | Area | Direction |
|---|---|---|
| MVP | Company/legal setup, locations, GST, LUT, fiscal setup, and lifecycle | Provide reusable Company setup with conditional statutory configuration. |
| MVP | PI/TI/DN/CN numbering | Support configurable, non-reusable final numbers and fiscal rollover. |
| MVP | Service and Product/SKU catalogues | Support Company adoption/configuration according to business nature. |
| MVP | Business Segment, Team, and Location Cost Center | Let each Company enable any supported combination through authoritative settings while retaining the bases as separate domain identities. |
| MVP | Currency, FX, Bank Accounts, tax inputs, presentation, email, and reminder defaults | Supply reusable Company/AR configuration within the stated boundaries. |
| MVP | Company-created Accounting hierarchy/Groups, stable GL Accounts, effective Revenue/Tax mappings, one default Receivable GL, and direct Bank-to-GL association | Resolve Company-defined accounts automatically while keeping hierarchy separate and preserving final references. |
| DEFERRED | Organisation-level configuration inheritance | Not part of the current MVP. |
| DEFERRED | Generic cost-centre framework, arbitrary dimensions, and percentage allocations | Preserve an extension path without implementing them now. |
| DEFERRED | Full template builder and detailed versioning | Retain historical reproducibility; specify advanced customization later. |
| DEFERRED | Detailed Tax, Reminder, Billing/Credit Note, Payment/write-off, and recurring scheduler rules | Define in their relevant module specifications. |
| DEFERRED | Full Accounting posting/reconciliation, starter CoA template engine, and inter-unit clearing rules | Keep approved account configuration/mapping while defining wider Accounting behavior separately. |
| Extensible | Platform catalogues and Company adoption | Support suggestions plus Tenant-private custom content while ownership is finalized later. |

## 29. Open Company-Configuration Decisions

Only the following unresolved decisions materially influence Company Configuration or its domain model:

1. What is the exact ownership boundary among platform Service Catalogue suggestions, Company adoption, and Company-specific service configuration?
2. Are Company Bank Accounts entirely Core/Shared masters, or is part of their definition AR-specific beyond AR selection behaviour?
3. Are Team and other management-reporting references shared across modules, or owned by AR configuration in the MVP?
4. What exact minimum identity, catalogue, numbering, currency, Bank Account, and tax setup blocks Company activation?
5. What Company-level Receipt FX configuration is required, and how does its purpose differ from Billing and Reporting FX?
6. What first-release applicability dimensions define numbering-series eligibility, and what combination defines a separately configured scope?

These remain **TBD**; this document does not resolve them by assumption.

## 30. Acceptance Summary

| Capability | Acceptance outcome |
|---|---|
| Isolation and hierarchy | Company setup remains inside one Tenant; Organisation is optional and provides no MVP inheritance. |
| Core/AR boundary | Shared Company facts and AR-specific policies are distinguishable, with uncertain ownership labelled Boundary TBD. |
| Identity and lifecycle | Company identity can be maintained and inactivation preserves history. |
| Locations/GST/LUT | Confirmed uniqueness, association, conditional-validation, and history rules are enforceable. |
| Fiscal periods | Annual periods derive from a pattern, future changes are controlled, and history is preserved. |
| Numbering | PI/TI/DN/CN support configurable series; final numbers are assigned after approval and never reused. |
| Catalogues | Business nature drives applicable setup; platform suggestions and Tenant-private configuration can coexist. |
| Management reporting | Company settings drive the enabled Business Segment, Team, and Location bases; no generic user-defined dimension engine is implied. |
| Currency and FX | Currency purpose is explicit; Billing and Reporting FX may differ; approved values are retained. |
| Bank and tax setup | Reusable inputs support Billing without forcing GSTIN routing or conflating classification with tax rules. |
| Accounting setup | Company-defined stable GL Accounts and effective mappings resolve Receivable, Revenue, and CGST/SGST/IGST accounts without hardcoded account names. |
| Presentation and email | Reusable Company defaults and document behaviour coexist without changing historical output. |
| Reminders and recurrence | Company reminder defaults are bounded; actual recurrence remains Sales-Order/contract driven. |
| Activation | Review presents required, conditional, optional, and TBD readiness accurately. |
| Integrity and audit | Material configuration changes preserve historical outcomes and record who/when/what. |

## 31. Inputs for Domain Modeling

The next documentation layer must use the following business concepts and constraints without treating this list as a physical schema:

| Domain input | Required interpretation |
|---|---|
| Ownership context | Tenant isolation; optional Organisation grouping; Company as legal/billing entity; no Organisation inheritance in MVP. |
| Core and AR boundaries | Shared Company identity/masters versus AR-specific numbering, FX use, document, delivery, and reminder configuration; preserve Boundary TBD items. |
| Company lifecycle | Active/Inactive state with historical access and auditable change. |
| Location/GST/LUT relationships | One physical Company Location may carry multiple applicable fixed purposes; non-Registered-Office purposes may repeat; exactly one active Registered Office; GST Registration to multiple Locations; zero-or-one Registration per Location; exactly one active default Location per GSTIN where applicable; no same-state duplicate active GST registration in MVP; one active LUT per GSTIN and fiscal period; LUT required for current EXPWOP and SEZWOP routes. |
| Fiscal behaviour | Default annual pattern, derived periods, controlled future adjustment, authoritative dates, and immutable historical associations. |
| Numbering invariants | PI/TI/DN/CN series scopes, approval-time final assignment, non-reuse, parallel series, and fiscal rollover. |
| Catalogue structures | Service Category → Service Type and Product Category → Product → SKU; platform suggestions, Company adoption/configuration, and Tenant-private extensions. |
| Classification and tax | Controlled Tax Types; Company-configured HSN/SAC; controlled numeric rates; effective eligible-rate mappings; controlled GST/Tax Treatment (`TAXABLE`, `NIL_RATED`, `EXEMPT`, `NON_GST`); separate Tax Statutory COMPONENT/SECTION codes and Code Rates; actual approved line tax facts retained. |
| Accounting setup | Company-created Hierarchies and Groups; stable GL Accounts; effective Group and GL placements; one-table Supply-Type/optional-HSN-SAC Revenue GL Mapping; statutory-code Tax GL Mapping; one default Receivable GL; direct Bank GL FK; finalized resolved account references. |
| Reporting dimensions | Independent Business Segment, Team, and Location bases with their approved cardinality/history rules; broader custom/arbitrary dimensions remain DEFERRED. |
| Currency and FX | Currency purpose, relevant pairs, rate type/purpose/effective context, authorization, and historical rate retention. |
| Bank, presentation, and delivery | Multiple Company accounts, AR selection behaviour, reusable assets/settings, document-level email behaviour, and historical reproducibility. |
| Reminder and recurrence boundaries | Company → Client → Invoice reminder precedence; Sales Order/contract ownership of recurrence. |
| Activation, history, and audit | Conditional readiness, no silent historical rewrite, and actor/time/change evidence for material configuration changes. |

Domain modelling must retain the unresolved decisions in Section 29 and must not convert deferred module behaviour into Company Configuration requirements.
