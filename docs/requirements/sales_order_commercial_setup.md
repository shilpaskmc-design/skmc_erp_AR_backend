# Sales Order / Commercial Setup

## Purpose

Sales Order defines the commercial agreement or internal supply instruction from which billing may occur.

It is not merely an order number.

It may contain:

- transaction classification: `CUSTOMER_SALE` or `INTER_UNIT`
- customer where the classification is `CUSTOMER_SALE`
- seller company
- commercial terms
- service/goods lines
- currency
- pricing
- billing method
- customer references
- expected billing dates

---

# High-Level Flow

Select Transaction Classification
↓
Select Customer or Destination Company GST Context
↓
Select Seller Company
↓
Determine Supply Context
↓
Enter Common Details
↓
Add Services / Goods
↓
Commercial Terms
↓
Customer Contacts
↓
Bill-To / Ship-To where relevant; Ship-To may be a Customer Location or the seller Company's own Location
↓
Customer Reference / PO / Engagement Letter
↓
Review
↓
Submit
↓
Approval

---

# Common Details

Possible common fields include:

- Sales Order Reference
- Contract Date
- Effective From
- Effective To
- Transaction Classification (`CUSTOMER_SALE` / `INTER_UNIT`)
- Customer for `CUSTOMER_SALE`
- Seller Company
- source seller GST Registration and Location
- destination Company GST Registration and Location for `INTER_UNIT`
- Cost Center / reporting configuration
- Engagement Manager / Owner
- Billing Currency / Currencies
- Payment Terms

For `INTER_UNIT`, both source and destination belong to the same Company but use different GST Registrations. The transaction must not create a normal Customer receivable and must not model the destination as a Customer. The Company Chart of Accounts/Accounting Setup foundation and AR Revenue/Tax GL mappings are current approved configuration. The Sales Order does not normally select Revenue or Tax GL Accounts and does not own accounting posting; Billing resolves the applicable mapped accounts before invoice finalization and the finalized AR transaction preserves the resolved references. Inter-Unit clearing and balancing treatment remains open for the future Accounting design.

Ship-To uses a discriminated choice: `CUSTOMER_LOCATION` or `COMPANY_LOCATION`, with only the corresponding Location reference populated. Final documents snapshot the address actually used.

---

# Service Lines

Service lines may contain:

- Service Category
- Service Type
- SAC
- Description
- Quantity
- UOM
- Currency
- Rate
- Pricing Method
- Discount
- Line Amount
- Expected Billing Date

Service Type is the lowest selectable/billable service catalogue item. Its SAC resolves from the Company's configured SAC reference; the Sales Order does not introduce free-text SAC or a separate service-tax assignment.

---

# Goods Lines

Goods lines may contain:

- Product Category
- Product
- SKU
- HSN
- Description
- Quantity
- UOM
- Currency
- Rate
- Discount
- Line Amount
- Expected Billing Date

SKU is the lowest selectable/billable goods catalogue item. Its HSN resolves from the Company's configured HSN reference; the Sales Order does not introduce free-text HSN or a separate SKU-tax assignment.

---

# Customer-Specific Pricing

Customer pricing belongs to commercial setup / Sales Order.

It should not modify the underlying Service or Product catalogue.

Example:

SKU ABC
Standard catalogue identity remains unchanged.

Customer A rate
→ ₹10,000

Customer B rate
→ ₹12,000

Rates belong to commercial agreement, not SKU master.

---

# Billing Types

Current billing concepts include:

- Advance
- Milestone
- Periodic
- Recurring

Recurring billing configuration primarily belongs to the Sales Order / contract.

It should not be treated as generic Company Configuration.

---

# Payment Terms

MVP may initially support:

- Immediate
- Net X Days

Architecture should not prevent future payment schedules such as:

- partial advance
- milestones
- multiple installments
- percentage-based due amounts

Do not build the advanced payment schedule unless required by MVP.

---

# Approval

Sales Order is submitted through the AR approval process.

Current MVP approval may remain simple.

Future multi-stage workflow should remain possible.
