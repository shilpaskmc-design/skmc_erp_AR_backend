# Customer Onboarding Requirements

## Purpose

Customer Onboarding creates and maintains the customer/legal-party information required by the AR process.

---

# Search Existing Customer

Before creating a new customer, users should be able to search by relevant identifiers such as:

- Customer / Legal Name
- PAN
- GSTIN
- Organisation
- existing customer identifiers

Duplicate statutory identifiers such as PAN/GSTIN should be validated.

Current direction:
duplicate PAN/GSTIN should be hard-blocked where the identifier is expected to be unique.

---

# Organisation

Organisation is optional.

A customer may exist without belonging to an Organisation.

Conceptually:

Organisation
└── Customer / Legal Entity

or:

Customer / Legal Entity
without Organisation

The MVP does not require complex Organisation-level configuration inheritance.

---

# Customer Information

Customer onboarding may contain:

- Legal details
- Customer Code
- statutory identifiers
- locations
- GST registrations
- contacts
- supporting documents

Customer Code is generated/assigned after approval for a new customer.

Updating an approved customer does not create a new Customer Code.

---

# Locations

Customer locations are maintained independently.

A customer may have:

- Registered Address
- Billing Address
- Shipping Address
- Branch / Office
- other business locations

Locations should not be deleted after they have been used in financial transactions.

Historical transaction addresses must remain reproducible.

---

# GST Registrations

A customer may have:

- one GST registration
- multiple GST registrations
- no GST registration

GST registrations and physical locations should remain separate concepts.

Relevant locations may be mapped to a GST registration.

---

# Contacts

Contacts are maintained independently from locations and GST registrations.

Possible contact roles include:

- Primary
- Billing
- Finance
- Escalation

One contact may perform multiple roles.

Example:

Rahul Sharma
- Primary
- Billing
- Finance

The design should therefore support multiple roles for one contact.

---

# Workflow

Initial onboarding workflow:

Draft
↓
Save / Resume
↓
Submit for Approval
↓
Finance / Authorized Review

Available decisions:

- Approve
- Edit
- Return
- Reject

New approved customer
→ Customer Code assigned.

Returned customer
→ corrected
→ resubmitted.

Multi-level configurable approvals are future capability, not MVP.

---

# Historical Integrity

Changes to customer legal data, addresses or GST registrations must not rewrite historical invoices.

Final financial transactions preserve the customer information actually used when the document was finalized.