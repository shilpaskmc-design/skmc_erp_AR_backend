# Module Boundaries

## Purpose

The wider product is intended to evolve into a SaaS business platform with multiple services/modules.

Potential platform capabilities include:

- Core / Shared Business Capabilities
- Accounts Receivable (AR)
- Accounts Payable (AP)
- Accounting
- HR
- KRA
- Future business tools

The current product-development focus is the Accounts Receivable service.

The architecture must avoid both:

1. creating one tightly coupled application where every module depends on every other module; and
2. prematurely creating a separate microservice for every shared master.

---

## Architectural Direction

Current development should use clear domain and feature boundaries.

Conceptually:

Platform
├── Core / Shared
├── AR
├── AP — future
├── Accounting — future
├── HR — future
└── KRA — separate domain/tool

AR may depend on Core/Shared capabilities.

Core/Shared capabilities must not depend on AR-specific behavior.

Example:

AR Billing
→ may consume Company

Company
→ must not contain Invoice Reminder logic.

---

# Core / Shared Capabilities

The following concepts are currently considered reusable/shared:

- Tenant
- Organisation
- Company
- Company Locations
- GST Registrations
- Financial Years / Fiscal Periods
- Time Zone
- Currency Reference
- Base Currency
- Reporting Currencies
- Exchange Rate Framework
- Company Bank Accounts, including the direct nullable same-Company Bank GL association
- Controlled Tax Type families
- Company-configured HSN / SAC codes
- Numeric Tax Rate and Company HSN/SAC eligible-rate references
- Controlled Tax / GST Treatments
- Tax Statutory Codes (GST COMPONENT, TDS/TCS SECTION) and Code Rates
- Cost Centers / reporting masters
- Company accounting identity and hierarchy: Account Hierarchies, Account Groups, effective Group relationships, stable Company GL Accounts, and effective GL-to-Group placement
- Company Accounting Settings, including the default Receivable GL
- Company/User access concepts
- Approval infrastructure — future shared capability
- Audit infrastructure

Shared ownership does not imply identical behavior across modules.

Example:

TDS statutory reference
├── AR → customer-deducted TDS
└── AP → vendor-payment TDS

---

# Customer / Party Boundary for the Current MVP

**Status: PROPOSED baseline; implementation is not authorized by this section.**

Customer Onboarding remains an AR-owned aggregate in the current MVP. Within that aggregate, legal/display identity, PAN and other statutory identifiers, Customer GST registrations, stable/effective-dated physical Customer Locations, Contact identity, and Contact Details are common/Party-like in meaning.

Customer Code lifecycle, Customer default Payment Term/credit period, Customer Contact-purpose assignments, Customer approval, and commercial/receivable behavior are Customer/AR-specific.

No shared Party, Vendor, or Contact master is approved for MVP. Common/Party-like data remains physically Customer-owned, but this does not declare permanent AR domain ownership. The boundary must remain explicit so a future approved Party model can link or extract common identity while Customer/AR behavior stays in AR.

Where a change in either category requires approval, it uses the Customer-specific onboarding/amendment workflow. Controlled changes remain conceptually classified as `COMMON/PARTY-LIKE` or `CUSTOMER/AR-SPECIFIC`. The current working persistence direction is Customer-specific Request + immutable JSONB Request Snapshots + append-only Actions; exact history means the exact submitted request payload, not typed Customer revision children. A future Party model may move common identity approval to Party; it must not force AR and future AP/Vendor onboarding to share terms, Contact purposes, or workflow routes.

The consolidated Customer decision/status baseline is [Customer Business Rules](../modules/customer/business_rules.md), with unresolved matters isolated in [Customer Open Decisions](../modules/customer/open_decisions.md).

---

# AR-Specific Capabilities

Current AR-owned capabilities include:

- Customer onboarding
- Service Catalogue
- Product / SKU Catalogue
- Sales Order / Commercial Setup
- Customer-Sale / Inter-Unit transaction classification
- LUT validation for outgoing invoices
- PI
- TI
- CN
- DN
- AR document numbering
- Billing
- Effective Revenue GL Mapping from Supply Type plus optional Company HSN/SAC to a Revenue GL Account
- Effective Tax GL Account Mapping from a controlled Tax Statutory COMPONENT/SECTION code to the applicable GL Account
- Invoice-context Revenue and Tax GL resolution behavior
- GSTR-1 filing batches and filed-membership edit locks
- E-invoice / IRN evidence and edit lock
- Receivables
- Receipt / Knock-off
- AR Document Branding
- Invoice Delivery
- Customer default Payment Term / credit-period selection and AR inheritance behavior
- AR Reminders
- AR Approval Workflow
- AR Audit Events
- Preservation of the resolved Receivable GL on finalized eligible AR Documents, resolved Revenue and applicable CGST/SGST/IGST GL Accounts on finalized AR lines, and resolved GL identity on applicable settlement adjustments

AR consumes Core/Shared Company Accounting and statutory identities and owns its invoice-context mapping and resolution rules. Core/Shared must not depend on invoices, Sales Orders, AR reminders, AR Revenue mapping behavior, AR Tax GL resolution behavior, or AR Receipt/Knock-off behavior.

A stable GL Account is the Company accounting identity. It is distinct from effective hierarchy/Group placement, AR Revenue mapping, Tax GL mapping, and the transaction-time resolved GL references preserved by finalized AR records. Example account names are never fixed product values.

The current AR capability does not implement a General Ledger posting engine. Full journal posting and ledger behavior, reconciliation, period closing/locking, historical reclassification/correction entries, and Inter-Unit clearing belong to the future Accounting domain. Account Types and broader accounting classifications, advanced Management-hierarchy behavior, and starter CoA templates/import/export remain deferred or open under their owning design decisions.

---

# Feature-Oriented Development

Prefer feature/domain-oriented structure.

Example:

core/
  company/
  location/
  currency/
  statutory_tax/

ar/
  customer/
  catalogue/
  sales_order/
  billing/
  numbering/
  reminders/
  receipts/

Avoid making the primary architecture:

models/
services/
controllers/

where unrelated domains become mixed together.

Technical layers may still exist inside each feature.

---

# Future Service Extraction

The current implementation must remain extractable later.

Possible future architecture:

core-service
ar-service
ap-service
accounting-service

Current code should therefore avoid:

- AR-specific logic inside Core entities
- direct cross-domain database assumptions where avoidable
- duplicate Company/Location/Currency masters inside AR
- generic catch-all settings tables
- tightly coupled workflow logic

The goal is not to implement microservices now.

The goal is to preserve clean boundaries so future extraction is practical.
