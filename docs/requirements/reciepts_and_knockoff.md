# Receipts and Knock-off Requirements

## Status

The Payment / Receipt module is not fully frozen yet.

This document records only currently confirmed concepts.

Do not treat it as final detailed payment design.

---

# Receipt

A payment/receipt may contain:

- Customer
- Company
- Payment Date
- Payment Mode
- Bank Account
- Reference / UTR
- Amount
- Currency
- Remarks
- Allocated Amount
- Unallocated Amount

---

# Allocation

Payment may be allocated against applicable AR documents.

Current concepts include:

- TI
- PI where the business flow permits
- DN

Allocation history must be preserved.

---

# Cash Identity

Important principle:

Payment Received
=
Effective Cash Allocations
+
Unallocated Amount

TDS, waiver and write-off are not cash receipts.

They must not be counted as bank/cash payment.

---

# TDS During Knock-off

Current AR flow:

Invoice Outstanding
↓
Customer payment received
↓
TDS applicable?
↓
select TDS section/code
↓
system obtains applicable rate
↓
TDS amount calculated / recorded
↓
Cash + TDS knock-off invoice

Example:

Invoice = ₹100,000
Cash = ₹90,000
TDS = ₹10,000

Invoice settled = ₹100,000

This is the current intended AR behavior.

Do not add ERPNext-style automatic threshold/cumulative TDS logic to MVP unless separately approved.

---

# PI to TI

Where PI payments/allocations are transferred to a converted TI:

- preserve original allocation history;
- preserve transfer history;
- avoid silently rewriting historical allocation records.

Exact conversion behavior belongs to the detailed Payment/Billing design.

---

# Historical Integrity

Payment allocations and reallocations must be auditable.

The system should be able to answer:

- payment received when?
- amount?
- allocated to which document?
- by whom?
- later changed?
- amount moved from PI to TI?
- unallocated balance at each relevant stage?

Detailed write-off rules remain deferred.