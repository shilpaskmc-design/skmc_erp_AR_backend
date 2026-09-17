# Tax and Statutory Rules

## Purpose

This document records currently confirmed AR tax behavior.

It is not intended to become a generic configurable tax-rule engine.

---

# HSN / SAC Classification

HSN and SAC are statutory item classifications configured by each Company for the codes relevant to its business. The Company-owned concept is `company_hsn_sac_codes`. The MVP does not require loading thousands of unrelated codes into every Company catalogue.

This is the current India-first classification design. A future foreign-seller rollout may require a broader Company Tax Classification model, but that generalization is DEFERRED and must preserve historical India GST data. No speculative scheme framework or generic tax engine is introduced now.

They are separate from company-defined catalogue naming.

They are also separate from Tax Type, numeric Tax Rate, Tax Treatment, TDS/TCS section, and accounting GL Account.

Services:

Service Type
→ Company-configured SAC (`company_hsn_sac_code_id`, classification type SAC)

Goods:

SKU
→ Company-configured HSN (`company_hsn_sac_code_id`, classification type HSN)

Do not derive final statutory classification only from Category level.

---

# Tax Types

`tax_types` is the controlled system/reference master for broad tax families such as GST, TDS, TCS, VAT and CESS.

It answers “What kind of tax is this?” It does not store HSN/SAC, a percentage, a Tax Treatment, or a TDS/TCS section.

`tax_rates` and `tax_statutory_codes` reference the applicable Tax Type. Do not repeat uncontrolled GST/TDS/TCS strings across those tables.

Keep the reference concepts distinct:

- `tax_rates` stores reusable ordinary item/supply percentage-rate identities, currently primarily GST HSN/SAC rates.
- `tax_treatments` stores tax nature such as TAXABLE, NIL_RATED, EXEMPT, or NON_GST; treatment is not a percentage.
- `tax_statutory_codes` stores statutory COMPONENT or SECTION identities.
- `tax_statutory_code_rates` stores effective statutory SECTION/case rates, primarily TDS/TCS.

Although `tax_rates` and `tax_statutory_code_rates` both contain percentages, they represent different business identities. A TDS/TCS SECTION/case rate does not reference an ordinary item Tax Rate merely because the numeric values could match.

---

# HSN / SAC and GST Rates

A single HSN or SAC may support multiple valid GST rates.

Therefore:

HSN / SAC
→ Set of valid GST rates

During catalogue setup:

Service Type / SKU
↓
Select HSN / SAC
↓
Show only rates valid for the selected HSN / SAC
↓
Company selects applicable rate

The system must not show every GST rate after a classification is selected.

Company-configured HSN/SAC records map to controlled tax-rate references through `company_hsn_sac_tax_rates`, an allowed effective-dated relationship. Items must not store an uncontrolled percentage as text. Statutory rate mappings should preserve effective-date history.

For the same Company HSN/SAC and eligible GST Tax Rate, active effective periods cannot overlap. Historical relationships are date-ended/inactivated rather than overwritten or deleted.

For the current catalogue default, `service_types.selected_tax_rate_id` and `skus.selected_tax_rate_id` store one selected eligible rate directly. The selection must belong to the item's Company HSN/SAC code through a currently valid mapping. No separate service/SKU tax-assignment table is required for MVP.

---

# GST Component Determination

Service Type / SKU should not directly store:

- CGST
- SGST
- IGST

Instead:

Configured HSN / SAC
+
selected eligible GST rate
+
Tax Treatment
+
seller GST context
+
place of supply
+
supply type
+
transaction date
↓
backend determines actual GST components and amounts.

Domestic concept:

Same-state
→ CGST + SGST

Inter-state
→ IGST

CGST, SGST, and IGST have controlled `tax_statutory_codes` rows with `code_kind = COMPONENT`. They are component identities, not TDS/TCS statutory sections and not ordinary GST item rates. `tax_rates` continues to hold item rates such as 5%, 12%, or 18%.

`code_kind = SECTION` identifies TDS/TCS statutory section/category identities. Effective SECTION/case percentages belong to `tax_statutory_code_rates`; ordinary GST item rates remain in `tax_rates`. Active effective ranges for the same statutory code and logical case cannot overlap, including the default/null case.

For accounting resolution, the Company maps the relevant COMPONENT code to a stable GL Account through an effective-dated `tax_gl_account_mappings` row. The mapping stores a statutory-code FK rather than free-text component code.

---

# Supply Types

Current AR business terminology:

B2B

B2C

EXPORT
├── EXPWOP
└── EXPWP

DEEMED_EXPORT / SEZ
├── SEZWOP
└── SEZWP

Current derivation:

Indian customer + GST registration
→ B2B

Indian customer + no GST registration
→ B2C

Export default
→ EXPWOP

Authorized Finance / Authority may change:
EXPWOP ↔ EXPWP

Deemed Export / SEZ default
→ SEZWOP

Authorized Finance / Authority may change:
SEZWOP ↔ SEZWP

---

# Place of Supply

For India:
→ State-based place of supply.

For outside India:
→ Country-based place of supply.

Billing should explicitly retain Place of Supply and Supply Type.

---

# LUT

Current MVP business decision:

LUT validation applies to the current **without-payment** Export / SEZ routes:

- EXPWOP
- SEZWOP

For those routes, an applicable valid LUT must exist for final billing.

If a required applicable LUT is unavailable:
→ final billing is blocked.

`EXPWP` and `SEZWP` do not require LUT merely because the transaction is Export or SEZ with payment.

This is intentionally a current business/product rule and may be revised later if management/legal policy changes.

LUT belongs to:

GST Registration
+
Financial Year / Fiscal Period

Historical LUT records must be preserved.

---

# GST / Tax Treatment

The current treatment values are:

- TAXABLE
- NIL_RATED
- EXEMPT
- NON_GST

These values are maintained as controlled `tax_treatments` references. GST/Tax Treatment is a classification, not a numeric Tax Rate Type. Do not assume rate = 0 fully represents these statutory treatments. Do not add `ZERO_RATED` unless a later product decision explicitly requires it.

---

# Billing Tax Resolution

Services:

Service Type
↓
Company-configured SAC resolves
↓
`company_hsn_sac_tax_rates` supplies only eligible effective GST rates
↓
Applicable rate is selected/resolved and revalidated
↓
Tax Treatment is applied
↓
seller jurisdiction + Place of Supply determine CGST + SGST or IGST
↓
final line snapshots SAC code/description as required, treatment, rate, components, and amounts

Goods follow the same flow from SKU to Company-configured HSN.

HSN/SAC never determines CGST versus SGST versus IGST by itself. Jurisdiction, Place of Supply, and seller GST context determine the component.

---

# GSTR-1 Filing and Invoice Edit Lock

Model each GSTR-1 filing as an auditable batch identified by:

- GST Registration
- Return Period
- Return Type

A batch may be prepared in `DRAFT` status and invoices may be added or removed with audit history. Draft membership does not permanently lock an invoice.

The hard edit lock applies only when the following statement is true:

**Invoice included in a FILED GSTR-1 return / filing batch.**

The filed batch must retain the filing reference, filed timestamp, filing actor, and exact included documents. After filing, corrections follow the applicable cancellation, amendment, Credit Note, or Debit Note process.

Successful e-invoice/IRN generation independently blocks editing of the issued invoice.

---

# TDS — AR Flow

Keep the current AR flow simple.

During receipt / knock-off:

TDS applicable
↓
User selects applicable TDS section/code
↓
System obtains the section's applicable configured rate
↓
TDS amount is calculated / recorded
↓
Cash + TDS may settle the receivable

Example:

Invoice = ₹100,000
Cash Received = ₹90,000
TDS = ₹10,000

Receivable Knock-off = ₹100,000

Detailed threshold/cumulative automation is NOT part of current MVP unless separately approved.

Manual override behavior remains a Payment-module decision.

TDS references resolve through `tax_types` → `tax_statutory_codes` (`code_kind = SECTION`) → `tax_statutory_code_rates`. They do not use Company HSN/SAC or ordinary GST item-rate mappings. Where accounting resolution is enabled, the SECTION code resolves through the Company's effective Tax GL Account Mapping.

---

# TCS — AR Flow

Current AR design remains:

Statutory classification / item configuration
↓
TCS applicability check
↓
Invoice line
↓
Applicable / Not Applicable
↓
calculate where applicable

A Service Type or SKU may require mandatory TCS applicability checking.

Mandatory Check = YES

does NOT mean TCS must always be charged.

It means the billing user/system cannot silently ignore the applicability decision.

Detailed thresholds, exemptions and calculation behavior remain to be finalized later.

When TCS applies, its section/rate resolves through `tax_types` → `tax_statutory_codes` (`code_kind = SECTION`) → `tax_statutory_code_rates`, according to the later approved Billing rules. HSN/SAC relevance and `tcs_check_required` trigger the applicability decision; they do not turn the GST rate into a TCS rate. Any resolved accounting GL comes from the effective statutory-code mapping, not from the section name.

---

# Historical Tax Integrity

Final invoice should preserve transaction-time tax facts such as:

- HSN / SAC used
- HSN / SAC description where required
- selected GST rate
- GST treatment/components
- taxable value
- tax amount
- Supply Type
- Place of Supply
- seller GSTIN
- TCS details where applicable

Later master changes must not alter historical invoices.
