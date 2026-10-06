# Company Configuration Requirements

## Status and scope

**Document status:** `PROPOSED` for review. This document defines what Company Configuration must support; it does not define physical SQL tables, APIs, or implementation mechanics.

Company Configuration establishes reusable Company masters, defaults, and policies needed before normal AR operations.

## 1. Company Identity & Legal Registration

- Administrators can maintain the identity and contact channels of the legal/billing entity.
- Company Legal Name identifies the legal entity.
- Display / Short Name provides a shorter business-facing label.
- System-generated Company Code (in `COM000001` form) provides a stable global operational reference; it is immutable in normal operation and is not a relational key.
- Entity Type selects the primary legal form from jurisdiction-scoped, platform-managed reference data.
- Jurisdiction- and Entity-Type-applicable identifier inputs (such as PAN, CIN, LLPIN) are shown and stored as Company identifier records rather than permanent identifier-specific Company columns.
- Base Time Zone supplies Company-local time for scheduled actions.
- Company email, phone, website, and logo maintain contact channels and assets.
- Company Status supports `DRAFT`, `ACTIVE`, and `INACTIVE`; incomplete configuration may persist while Draft.

## 2. Company Locations

- A Company can maintain multiple stable physical/business Locations (e.g. Registered Office, Branch, Warehouse).
- Location Code is an immutable Company-scoped stable reference used for import and integrations.
- Location Name is a mutable display/search name.
- Exactly one active Registered Office exists per Company when setup is completed/usable.
- One Company Location may carry more than one fixed purpose (e.g., Registered Office + Billing Office).
- A Location may optionally link to one GST Registration and one Location Cost Center within the same Company.
- Mapped Location state/jurisdiction must be compatible with its GST Registration.
- At most one active Location mapped to a GST Registration is marked as its default.
- Historically used locations are deactivated rather than hard-deleted.
- Location address and jurisdiction history is effective-dated for the same stable Location.

## 3. GST Registrations & LUTs

- A Company can maintain multiple GST registrations when GST registration is applicable.
- Each GST registration belongs to one Indian State/UT (Subdivision code) and uses a 15-character structurally valid GSTIN.
- Company Legal Name and GST-registration Legal Name are distinct current facts.
- GST Registration lifecycle is `DRAFT` → `ACTIVE` → `INACTIVE`.
- At most one active GST registration is supported per Company per Indian State/UT in MVP.
- Excel Bulk Import supports GST Registrations and normalized GST Location Mappings with create-or-compare and additive mapping rules.
- LUT configuration applies to current without-payment Export/SEZ routes (`EXPWOP` and `SEZWOP`).
- At most one active LUT reference exists per GSTIN and fiscal period.
- Missing required LUT blocks finalization for `EXPWOP` and `SEZWOP`; `EXPWP` and `SEZWP` are not blocked solely for missing LUT.

## 4. Fiscal / Financial Period Configuration

- A Company defines one normal recurring fiscal-year pattern using `APR_MAR`, `JAN_DEC`, or `CUSTOM` (with explicit recurring start month and day).
- Actual Financial Year dates are authoritative and carry display codes (e.g. `2026-27`).
- Financial Years start in `DRAFT` and follow `DRAFT` → `OPEN` → `CLOSED`.
- Financial Years for the same Company must not overlap.
- Short or transition Financial Years are explicitly supported.
- Creating a future Financial Year does not close or lock the previous Financial Year.
- Financial Year, accounting close, and accounting lock remain separate concepts.

## 5. AR Document Numbering

- Configures numbering/series for Proforma Invoice (PI), Tax Invoice (TI), Debit Note (DN), and Credit Note (CN).
- Numbering may vary by Company, fiscal period, seller GST registration, and parallel series.
- Final financial document numbers are assigned only after approval/finalization.
- Parallel series retain independent counters.
- Eligibility conditions use controlled criteria (e.g. GSTIN, Location, Document Type).

## 6. Payment Terms

- Maintains reusable `IMMEDIATE` (0 days) and `NET_DAYS` Payment Terms.
- A Company can mark at most one active Payment Term as the Company default.
- Customer Onboarding may select one active same-Company Payment Term as Customer Default Credit Period; if omitted, the Company default applies.

## 7. Customer Code Configuration

- Customer Code is system-generated and configuration belongs to Company Configuration.
- The prefix is Company-configured (NOT hard-coded).
- Numeric padding/digits are Company-configured.
- The sequence is scoped to the Company, starts at 1, and does not automatically reset.
- Code is allocated only during successful `NEW_CUSTOMER` approval/publication and remains stable once allocated.
- Prefix validation, padding overflow behavior, and Company-readiness / Customer-approval configuration gate remain `REVIEW` items.

## 8. Business Nature & Catalogues

- Company selects business nature: Services, Goods, or Both.
- **Services Catalogue**: Service Category → Service Type. Service Type stores SAC, Base GST Nature (`TAXABLE`, `NIL_RATED`, `EXEMPT`, `NON_GST`), conditional selected eligible GST rate, `tcs_check_required` flag, and optional Business Segment.
- **Goods Catalogue**: Product Category → Product → SKU. SKU stores SKU Code, Product, HSN, Base GST Nature, conditional selected eligible GST rate, UOM, `tcs_check_required` flag, and optional Business Segment.
- **HSN / SAC Classification**: Company configures relevant HSN/SAC codes (`company_hsn_sac_codes`) and effective eligible rates (`company_hsn_sac_tax_rates`). Service Type references SAC; SKU references HSN.
- Terminal inactivation hierarchy applies: parents cannot be inactivated while active children exist, and child re-parenting is prohibited.

## 9. Cost Centers & Management Reporting

- `company_cost_center_settings` enables or disables reporting bases: Business Segment, Team, and Location.
- Business Segment: direct association with Service Types and SKUs.
- Team: Cost Center Team reporting buckets group actual Company Teams; actual Teams hold effective-dated user memberships.
- Location Cost Center: groups physical Company Locations.

## 10. Currencies, Banking & FX

- Configures Base Currency, additional Reporting Currencies, and AR Currencies (with Billing and Receipt permissions).
- Stores directional corporate/spot Exchange Rates (`exchange_rates`) and FX Policies (`fx_policies`).
- Maintains Company Bank Accounts with currency, bank details, account type, optional Bank GL FK, and default billing bank per currency.

## 11. Document Presentation, Branding & Delivery

- Company branding stores logo, signature, and stamp file references in `stored_files`.
- Maintains versioned document templates (`company_document_templates`).
- Email provider configuration (`email_provider_configs`) and delivery settings (`company_invoice_delivery_settings`).
- Reminder policies (`reminder_policies`) and schedule rules (`reminder_schedule_rules`).
