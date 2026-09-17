# Billing and Invoicing Requirements

## Purpose

Billing converts approved commercial arrangements into outgoing AR documents.

Supported AR document concepts:

- PI — Proforma Invoice
- TI — Tax Invoice
- CN — Credit Note
- DN — Debit Note

---

# High-Level Billing Flow

Customer Sale or Inter-Unit Classification
↓
Sales Order
↓
Select Services / Goods
↓
Select Document Type
↓
Header Details
↓
Line Details
↓
Dispatch / Shipment Details where applicable
↓
Tax Determination
↓
Narration / Additional Details
↓
Submit
↓
Approval
↓
Final Number
↓
PDF
↓
Invoice Delivery
↓
Receivable when the document is an eligible Customer Sale

---

# Seller Context

Billing should capture:

- Seller Company
- Seller GSTIN where applicable
- Seller Location

Each active GST Registration may have several linked Locations and exactly one active default Location for that GSTIN where applicable. The default supports preselection only; the selected source GST Registration and Location remain explicit and must be compatible.

Preferred UX:

Select Company
↓
show active GST registrations
↓
select Seller GSTIN
↓
show only linked seller locations

Reverse filtering may also be supported:

Select Seller Location
↓
show applicable GST registrations

GSTIN is conditionally mandatory.

If transaction is issued under a registered seller establishment:
→ GSTIN required.

If selected location has no applicable GST registration:
→ do not automatically use another state's GSTIN.

---

# Customer / Inter-Unit Supply Context

For `CUSTOMER_SALE`, the invoice should preserve:

- Customer
- Customer GST registration where relevant
- Bill-To
- Ship-To where relevant
- Place of Supply
- Supply Type

For `INTER_UNIT`, the document instead captures source GST Registration/Location and destination GST Registration/Location belonging to the same Company. It does not create a normal Customer receivable and the destination must not be represented as a Customer. Approved Revenue/Tax GL resolution applies where relevant, while balancing and inter-unit clearing entries remain an open Accounting design.

Ship-To can reference either a Customer Location or the seller Company's own Location. `ship_to_type` distinguishes `CUSTOMER_LOCATION` from `COMPANY_LOCATION`; only the matching reference is populated. The final document snapshots the address actually used.

Supply Type and Place of Supply participate in tax treatment.

---

# Service Invoice Header

Typical fields may include:

- Customer
- Seller Company
- Seller GSTIN
- Seller Location
- Place of Supply
- Supply Type
- Invoice Date
- Financial Year
- Currency
- Exchange Rate where applicable
- Payment Terms / Credit Period
- Bank Account
- reference invoice/document where applicable

---

# Goods Invoice Additional Fields

Goods billing may additionally contain:

- Bill-To
- Ship-To
- Dispatch Date
- Delivery Date
- Dispatch From
- Vehicle Number
- Vehicle Type
- LR Number / Date
- Airway Bill Number / Date
- Shipping Bill Number / Date
- E-Way Bill Number / Date

Fields should be shown based on applicability.

Do not make every possible shipment field mandatory.

---

# Invoice Lines

Service line:

- Service Type
- SAC
- Quantity
- UOM
- Rate
- Discount
- Taxable Amount
- GST Rate
- Tax Amount

Each line records GST/Tax Treatment as one of `TAXABLE`, `NIL_RATED`, `EXEMPT`, or `NON_GST`. This is a controlled treatment classification, not a numeric tax-rate type; numeric `0%` does not imply NIL_RATED, EXEMPT, or NON_GST.

Goods line:

- SKU
- HSN
- Quantity
- UOM
- Rate
- Discount
- Taxable Amount
- GST Rate
- Tax Amount

Tax resolution for a Service line:

```text
Select Service Type
→ resolve its Company-configured SAC
→ load only effective eligible rates from the Company SAC-to-rate mapping
→ select/resolve and revalidate the applicable rate
→ apply the configured Tax Treatment
→ use seller GST context and Place of Supply to determine CGST + SGST or IGST
→ snapshot SAC code/description as required, treatment, applied rate, components and amounts
```

Goods follow the same process from SKU to the Company's configured HSN. The HSN/SAC code does not itself determine CGST versus SGST versus IGST.

The current catalogue default is stored directly as `service_types.selected_tax_rate_id` or `skus.selected_tax_rate_id` and must be eligible through `company_hsn_sac_tax_rates`. Billing revalidates it for the transaction date. No separate service/SKU tax-assignment table is part of the MVP.

Tax Type, Company HSN/SAC, numeric Tax Rate, HSN/SAC-to-rate eligibility, Tax Treatment, and Tax Statutory Codes/Rates remain separate controlled concepts. GST COMPONENT and TDS/TCS SECTION identities do not merge with ordinary GST item rates.

---

# Automatic Receivable, Revenue, and Tax GL Resolution

The Company creates stable GL Accounts independently from its effective-dated hierarchy placement, then configures Revenue and Tax/Statutory GL mappings and one default Receivable GL. Account identity does not store Supply Type, HSN/SAC, parent Group, or calculated balance.

Invoice-time flow:

```text
Invoice is being created
→ Invoice date determines which mappings are effective
→ Supply Type is already known
→ Service Type / SKU supplies its configured SAC / HSN
→ Check effective Revenue GL Mappings
→ Use a matching Supply Type + HSN/SAC mapping when present
→ Otherwise use the matching general Supply-Type mapping
→ Resolve CGST / SGST / IGST COMPONENT identities and their effective Tax GL mappings
→ For an eligible Customer Sale, resolve the Company's default Receivable GL
→ Store resolved Revenue/Tax IDs on finalized lines and Receivable ID on the finalized document
```

The invoice user does not normally select receivable, revenue, or tax ledgers. If no effective mapping matches, mappings overlap/are ambiguous at the same specificity, or a required GL is inactive/not date-valid, finalization is blocked rather than selecting a wrong account.

`B2B`, `B2C`, `EXPWOP`, `EXPWP`, `SEZWOP`, and `SEZWP` are the mapping inputs. `DOMESTIC` is not a special location-detection value, and SEZ is not forced to a domestic or export account. The Company decides its mapping.

HSN/SAC remains the item's statutory classification and is not permanently tied to one GL Account. The same SAC may resolve to domestic revenue for one Supply Type and export revenue for another.

Each finalized line preserves its resolved `revenue_gl_account_id` and applicable CGST/SGST/IGST GL Account references. An eligible Customer-Sale document preserves `receivable_gl_account_id`. Later hierarchy or mapping changes apply prospectively and do not reclassify historical invoices.

The selected Company Bank Account may reference its stable GL Account directly. No separate bank-to-GL mapping table is used. Full bank/receipt posting journals remain deferred.

Names such as `Sales - Domestic`, `Sales - Export`, `Scrap Sales`, and `Output IGST` are examples only; mapping uses Company GL Account IDs.

---

# Financial Year

Financial Year should normally resolve from transaction/invoice date.

Users should not manually select a year when the date determines it unambiguously.

---

# Payment Term and Due Date

Billing resolves the selected reusable Company Payment Term according to the approved commercial context.

When a document is approved/finalized, preserve the selected Payment Term identity/context, the credit-days value actually used, and the derived due date as transaction-time truth. Later edits or inactivation of the current `payment_terms` master must not recalculate an already approved/finalized document.

---

# Exchange Rate

Applicable exchange rate is selected/resolved according to the configured FX policy.

Actual rate used by the final document must be snapshotted.

Historical invoice FX must never change because the current exchange-rate master changes later.

Exact Corporate / Spot / User-Fixed behavior remains subject to further configuration design.

---

# LUT Validation

Before final approval/finalization:

For the current without-payment routes:

- EXPWOP
- SEZWOP

validate the applicable LUT for the selected seller GST Registration and applicable Financial Year / fiscal period.

Missing required LUT
→ BLOCK final billing.

`EXPWP` and `SEZWP` are not blocked solely for missing LUT.

---

# Numbering Series

Final document number should be consumed only at finalization/approval.

Draft documents should not unnecessarily consume final statutory numbers.

Multiple parallel numbering series may exist.

Series eligibility uses controlled factors. Candidate factors include:

- Document Type
- GSTIN
- Location
- Supply Type
- Business Segment
- Team / Cost Center
- Transaction Nature, such as Goods / Services, if approved

The exact first-release condition-type allow-list, operator vocabulary, and multi-condition combination semantics remain OPEN. `Custom Series` is not treated as an executable condition type; parallel/custom-named series are represented by the sequence rows themselves.

MVP:

1 eligible series
→ auto-select.

Multiple eligible series
→ user selects.

No eligible series
→ block finalization.

Future architecture must allow conditional/priority-based automatic resolution.

Consumed document numbers must never be reused after cancellation.

---

# Historical Snapshot

Final financial documents must preserve the actual values used at issuance.

Examples:

- legal company name
- seller GSTIN
- seller address
- customer address
- HSN/SAC
- HSN/SAC description where required
- GST rate
- GST/Tax Treatment
- tax amounts
- resolved Receivable, Revenue, and applicable Tax GL Account IDs
- Supply Type
- Place of Supply
- exchange rate
- selected Payment Term / credit-days context and derived due date
- bank information shown
- template/branding version or equivalent pinned output context where necessary

Current master, hierarchy, Group placement, or mapping changes must not rewrite finalized invoices. A historical accounting change requires a future explicit reclassification/correction entry, not an in-place master-data rewrite.

The finalized rendered PDF is a separate immutable artifact from current template/branding configuration. Binary output is stored through the shared `ObjectStorage` / `stored_files` pattern; changing current template, branding, or master data must not replace or regenerate an already-issued PDF in place.

---

# Filing and E-Invoice Edit Locks

GSTR-1 filing is represented by an auditable filing batch identified by GST Registration + Return Period + Return Type. A draft batch may include or remove documents with audit history and does not permanently lock them.

Only this condition creates the GSTR-1 hard edit lock:

**Invoice included in a FILED GSTR-1 return / filing batch.**

The filed batch preserves filing status, reference, filed timestamp, actor, and the exact included documents. Its document membership is immutable after filing.

Successful e-invoice/IRN generation also blocks editing of the issued document. Corrections then use the applicable cancellation, amendment, Credit Note, or Debit Note process rather than changing the issued invoice in place.
