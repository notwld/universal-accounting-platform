# Feature Specification: Purchase Orders, Attachments, Payment Runs

**Feature Branch**: `005-po-attachments-runs`

**Created**: 2026-09-17

**Status**: Draft

**Input**: User description: "Implement previously skipped Phase 3 items: attachments with org-scoped authorized download and size/type limits, purchase orders that convert to bills without posting, vendor payment runs, and vendor statements. Also cover skipped credit-note/vendor-credit happy paths from 003/004. API only, no screens. Then continue to banking."

**Requirement coverage**: FIN-04 (PO, payment runs, supplier statements), FIN-03 credit application, Phase 3 attachment authorization. Screens still deferred.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Attach a receipt and retrieve only inside the organization (Priority: P1)

An Accountant or Purchasing Clerk attaches a PDF or image to a bill, expense, purchase order, or invoice. The file is stored for that organization. Another organization cannot download it. Oversized or disallowed types are rejected. Download is an authorized request, not a public link.

**Why this priority**: Phase 3 required attachment authorization before calling purchases complete.

**Independent Test**: Upload a small PDF to a bill in org A; download succeeds; org B cannot download; a `.exe` and an oversized file are rejected.

**Acceptance Scenarios**:

1. **Given** a bill in organization A, **When** an authorized user uploads a PDF under the size limit, **Then** the attachment is listed on that bill and can be downloaded by an A member with finance access.
2. **Given** that attachment id, **When** the same user is selected into organization B, **When** they request the file, **Then** it is not returned.
3. **Given** a disallowed type or a file over the size limit, **When** upload is attempted, **Then** it is rejected and nothing is stored.

---

### User Story 2 - Purchase order then bill, no ledger until the bill posts (Priority: P1)

A Purchasing Clerk records a purchase order (non-posting). Converting it creates a bill draft linked to the PO. The PO is not deleted. Trial balance is unchanged until the bill is posted.

**Why this priority**: Quote→invoice already exists on sales; the buy path was missing the matching non-posting order.

**Independent Test**: PO → convert → bill draft; TB empty until bill post; converting twice is rejected.

**Acceptance Scenarios**:

1. **Given** a vendor and item, **When** a PO is saved, **Then** no journal is written.
2. **Given** that PO, **When** it is converted, **Then** a bill draft exists linked to the PO and the PO is marked converted, not deleted.
3. **Given** a converted PO, **When** convert is retried, **Then** the request is rejected.

---

### User Story 3 - Pay several bills in one run (Priority: P1)

An Accountant selects open bills and records one payment run against a bank account. Each vendor gets one vendor payment; allocations cannot over-settle. The run is idempotent. A Purchasing Clerk cannot post a run.

**Why this priority**: FIN-04 payment runs; paying bills one HTTP call at a time is not the operator workflow.

**Independent Test**: Two posted bills (possibly two vendors) paid in one run; AP reduced; replay same key does not double-pay.

**Acceptance Scenarios**:

1. **Given** two posted bills with outstanding, **When** a payment run allocates each outstanding amount, **Then** each bill is settled and bank decreases by the total.
2. **Given** a successful run, **When** the same idempotency key is retried, **Then** the original run is returned with no extra journals.
3. **Given** an allocation that exceeds a bill, **When** the run is submitted, **Then** nothing posts.

---

### User Story 4 - Vendor statement and credit application (Priority: P2)

An Accountant retrieves a vendor statement for a date range (bills, payments, credits, outstanding). A customer credit note applied to an open invoice, and a vendor credit applied to an open bill, reduce outstanding without a second cash posting.

**Why this priority**: Phase 3 vendor statements; 003/004 implemented credits but did not prove the apply path in tests.

**Independent Test**: Statement lists the posted bill; credit against an open bill/invoice reduces outstanding.

**Acceptance Scenarios**:

1. **Given** posted vendor activity, **When** a statement is requested for that vendor and period, **Then** bills, payments, and credits in range appear and outstanding matches the subledger.
2. **Given** an open invoice of 110, **When** a credit of 110 is applied, **Then** AR outstanding is 0 and no extra bank movement is created.
3. **Given** an open bill of 110, **When** a vendor credit of 110 is applied, **Then** AP outstanding is 0 and no extra bank movement is created.

---

### Edge Cases

- Attachment download without organization context is denied.
- PO convert copies tax/item snapshots into the bill draft using current tax calculation (same as quote convert).
- Payment run with bills of mixed vendors creates one payment per vendor.
- Empty payment run is rejected.
- Statement excludes other vendors and other organizations.

## Requirements *(mandatory)*

- **FR-001**: Attachments MUST belong to one organization and one existing finance document (bill, expense, purchase order, invoice, credit note, vendor credit).
- **FR-002**: Upload MUST reject types outside PDF/PNG/JPEG/WebP and files larger than 10 MiB. Download MUST require the same organization context and a finance grant; public/raw media URLs MUST NOT be the access path.
- **FR-003**: Purchase orders MUST NOT post. Convert creates a bill draft linked to the PO.
- **FR-004**: Payment runs MUST create vendor payments through the existing payment service under lock/idempotency; they MUST NOT post cash a second way.
- **FR-005**: Vendor statement MUST be organization- and contact-scoped and dated.
- **FR-006**: Customer and vendor credits applied to open documents MUST reduce outstanding without a cash journal.
- **FR-007**: No screens. No stock receipts, warehouses, or payment-gateway batches.

### Key Entities

- **Purchase order / lines**: Non-posting buy offer; converts to bill draft.
- **Attachment**: Org-scoped file on a document.
- **Payment run / lines**: Batch of vendor bill allocations posted as vendor payments.
- **Vendor statement row**: Derived activity for a vendor in a period.

## Success Criteria *(mandatory)*

- **SC-001**: Org A can download its receipt; org B cannot, in 100% of attempts.
- **SC-002**: Disallowed or oversized uploads never persist a file.
- **SC-003**: PO convert does not change trial balance; posting the resulting bill does.
- **SC-004**: A two-bill payment run settles both bills with one bank decrease equal to the sum; replay does not double-pay.
- **SC-005**: Credit-note and vendor-credit application zero the target document outstanding without changing cash except where a separate refund exists.
- **SC-006**: Vendor statement for A does not include B's bills.

## Assumptions

- 003/004 posting, tax, FX, and grants already exist.
- 10 MiB and PDF/PNG/JPEG/WebP are the production limits until a country pack says otherwise.
- Purchase orders here are commercial documents, not warehouse receipts (Phase 6).
- Payable work queue is AP aging plus open bills; no separate UI queue.

## Out of Scope

- Screens, public CDN links, virus scanning appliances.
- Goods receipts, inventory, sales orders.
- Recurring bills, multilevel approval, bank statement import (next slice).
