# Feature Specification: Purchases and Payables

**Feature Branch**: `004-purchases-payables`

**Created**: 2026-09-17

**Status**: Draft

**Input**: User description: "Build Phase 3 purchases and expenses on the existing finance ledger and sales conventions: vendor contacts, bills, paid expenses, vendor credits, vendor payments, advances, refunds, FX settlement, and AP aging. Backend/API only — no screens. No purchase orders, attachments, PDF, email, or approval engine. Reuse the posting engine. Production quality, not an MVP."

**Requirement coverage**: FIN-04 (purchasing/payables without PO/receipts/recurring/statements UI), FIN-06 (tax snapshots and FX settlement on payables), FIN-10 (AP aging). FIN-14 screens deferred. Depends on 002 ledger and 003 contacts/tax/FX/settlement.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Keep vendors and purchase mappings (Priority: P1)

A Purchasing Clerk or Accountant marks a contact as a vendor and records sellable/purchasable items with an expense (or asset) account for bills. Records belong to one organization. Changing a contact name or tax rate later must not rewrite already posted bills.

**Why this priority**: Bills cannot be issued without a vendor and expense mapping.

**Independent Test**: Create a vendor and item expense mapping in org A; confirm they are invisible in org B; change the tax rate after a posted bill and confirm the bill still shows the original tax.

**Acceptance Scenarios**:

1. **Given** finance setup is complete, **When** an authorized user creates a vendor contact and an item mapped to an expense account and a tax rate, **Then** those records are stored only for the selected organization.
2. **Given** the same user selected into organization B, **When** they list contacts or bills, **Then** A's records are not returned.
3. **Given** a tax rate later changes, **When** a previously posted bill is retrieved, **Then** its tax amounts, rate, and labels remain the posted snapshot.

---

### User Story 2 - Bill then post once; paid expense posts cash (Priority: P1)

A Purchasing Clerk prepares a bill draft. An Accountant posts it. Posting creates AP, expense, and recoverable tax in the shared ledger using server-calculated totals. A paid expense (cash purchase, no AP) posts expense and tax against bank in one step. Drafts can show a posting preview that does not affect reports. Purchase orders do not exist in this slice and must not post.

**Why this priority**: This is the buy path; posting must not depend on attachments or delivery.

**Independent Test**: Bill draft → preview → post; paid expense posts cash; retrying the post key does not create a second journal.

**Acceptance Scenarios**:

1. **Given** a vendor, item, and exclusive tax of 10% on net 100, **When** a bill is posted, **Then** the books show Dr expense 100, Dr tax 10, Cr AP 110, and the bill is posted and numbered.
2. **Given** a bill draft, **When** posting preview is requested, **Then** proposed journal lines are returned and no journal is written. **When** posting succeeds, **Then** one journal exists linked to that bill.
3. **Given** a posted bill, **When** line prices or tax are edited, **Then** the change is rejected. Correction uses a vendor credit.
4. **Given** a Purchasing Clerk, **When** they create a bill draft, **Then** it succeeds; **When** they post it, **Then** posting is denied. An Accountant can post. A Sales Clerk cannot create or post bills.
5. **Given** a paid expense of net 50 plus 10% tax paid from bank, **When** it is recorded, **Then** Dr expense 50, Dr tax 5, Cr bank 55. No AP movement.
6. **Given** a successful post, **When** the same idempotency key is retried, **Then** the original posted bill (or expense) is returned.

---

### User Story 3 - Pay, credit, refund, and not over-allocate (Priority: P1)

An Accountant records vendor payments against posted bills, including partial payment, overpayment (vendor advance), vendor credits applied to bills, and refunds of advances. Allocations cannot exceed remaining bill balance or remaining payment/credit. Concurrent allocations cannot over-settle.

**Why this priority**: Settlement is the rest of the buy path; outstanding payables must stay truthful.

**Independent Test**: Bill 110 → pay 60 → outstanding 50 → pay 80 → AP 0 and vendor advance 30 → credit/refund path; over-allocation is rejected.

**Acceptance Scenarios**:

1. **Given** a posted bill of 110, **When** a payment of 60 is allocated to it, **Then** Dr AP 60, Cr bank 60, outstanding 50.
2. **Given** remaining 50, **When** a payment of 80 is allocated, **Then** Dr AP 50, Dr vendor advance 30, Cr bank 80.
3. **Given** a posted vendor credit against that vendor, **When** it is applied to an open bill, **Then** outstanding decreases without creating a second cash posting.
4. **Given** a vendor advance, **When** a refund is recorded, **Then** the advance decreases and cash/bank increases; the original payment remains.
5. **Given** an allocation that exceeds remaining bill or payment, **When** it is submitted, **Then** it is rejected and balances are unchanged.
6. **Given** a posted vendor payment, **When** it is mutated, **Then** the attempt is rejected; corrections are new documents linked to the original.

---

### User Story 4 - Foreign-currency bills and dated AP (Priority: P2)

An organization with USD books can receive a EUR bill using a stored rate. Settlement at a different rate produces realized FX. AP aging as of a past date uses settlements known at that date. Drafts never appear in aging or financial totals.

**Why this priority**: Phase 3 gate requires FX settlement and historical aging tied to the ledger, matching sales.

**Independent Test**: EUR 100 at 1.10, paid at 1.15; aging as-of before payment still shows the payable; GL AP matches the subledger.

**Acceptance Scenarios**:

1. **Given** USD books and rate 1.10, **When** EUR 100 plus no tax is posted as a bill, **Then** AP is USD 110 (base = foreign × stored rate). Missing rate blocks posting.
2. **Given** that bill, **When** it is paid in EUR 100 at 1.15, **Then** Dr AP 110, Dr realized FX loss 5, Cr bank 115.
3. **Given** a partial payment after bill date, **When** AP aging is requested as of a date before the payment, **Then** the bill still appears outstanding for the pre-payment amount.
4. **Given** drafts, **When** aging or trial balance is requested, **Then** they are omitted.
5. **Given** AP control total from the ledger, **When** compared to open bills minus allocations as of the same date, **Then** they agree.

---

### User Story 5 - Operate purchases through the API without screens (Priority: P2)

Authorized operators complete vendors, bills, posting, payments, credits, refunds, paid expenses, and AP aging through the versioned finance API. No graphical application ships.

**Why this priority**: Product owner deferred all screens.

**Independent Test**: Drive US1–US4 solely via documented API requests, including permission and cross-organization negatives.

**Acceptance Scenarios**:

1. **Given** a valid grant, **When** the operator runs bill → post → partial pay → credit → refund, **Then** each step succeeds or fails with a stable reason (closed period, imbalance, over-allocation, missing rate, insufficient permission, cross-organization, stale version, idempotency conflict).
2. **Given** organization A selected, **When** a B bill id is referenced, **Then** no B data is returned.

---

### Edge Cases

- Inclusive tax: quoted price includes tax; net and tax still snapshot and post correctly.
- Zero-tax / exempt line next to a taxed line on one bill.
- Bill in base currency: no FX lines.
- Credit exceeding remaining bill balance: rejected, not silent over-apply.
- Refund exceeding remaining vendor advance: rejected.
- Period locked covering bill date: post rejected.
- Inactive item or contact: new drafts rejected; posted history unchanged.
- Contact may be both customer and vendor; this slice uses the vendor role.
- Purchase orders, stock receipts, attachments, recurring bills, supplier statements, and payment runs are out of scope.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Vendor contacts, items with expense mapping, bills, vendor credits, vendor payments, allocations, refunds, paid expenses, and AP aging MUST be organization-scoped from trusted membership context.
- **FR-002**: A contact MAY be marked as a vendor. Customer-only sales workflows remain on 003. One contact record per party per organization.
- **FR-003**: Bill lines MUST map to an expense or asset account (from the item or an explicit account). Tracked inventory, warehouses, and COGS from stock layers are out of scope.
- **FR-004**: Tax rates are dated, organization-owned, and support exclusive and inclusive pricing. Posted documents snapshot tax identity, rate, and computed tax. A later rate change MUST NOT rewrite posted documents. Purchase tax is recoverable (debit the tax account used by the rate).
- **FR-005**: Purchase orders MUST NOT exist in this slice and MUST NOT post.
- **FR-006**: Bill posting MUST use the shared posting engine. Server recalculates totals. Client totals are not authoritative. Posted commercial fields are immutable.
- **FR-007**: Bill posting MUST credit AP control, debit expense (and other mapped accounts), and debit tax for input tax. Unexplained imbalance rejects the post with no partial write.
- **FR-008**: Purchasing Clerk MAY create/edit bill drafts. Posting bills, recording vendor payments, paid expenses, credits, and refunds require the corresponding action permissions (not implied by Purchasing Clerk). Sales Clerk MUST NOT create or post bills.
- **FR-009**: Vendor payments allocate to bills under lock. Allocations MUST NOT exceed remaining bill balance or remaining payment funds. Excess payment is a vendor advance asset.
- **FR-010**: Vendor credits reduce payable when applied. Refunds of vendor advances increase cash/bank and reduce the advance. Original posted documents remain.
- **FR-011**: Paid expenses MUST post expense and tax against cash/bank with no AP. They require payment-recording permission.
- **FR-012**: Idempotency is per organization, operation, and key for post bill, paid expense, record vendor payment, apply vendor credit, and vendor refund.
- **FR-013**: Foreign amounts convert as base = foreign × stored rate. Missing rate blocks posting and settlement. Settlement difference posts to realized FX. Unrealized revaluation is out of scope.
- **FR-014**: AP aging and outstanding balances as of a date MUST use documents and allocations with dates on or before that date. Drafts excluded. Results MUST tie to AP control in the ledger as of the same date.
- **FR-015**: Document numbers unique per organization, type, and series; issued numbers not reused.
- **FR-016**: No screens, empty navigation, PDF renderer, email send, attachments, customer/supplier portal, recurring billing, purchase orders, or payment-run batches in this feature.

### Key Entities

- **Contact**: Organization party; vendor flag in this slice (may also be a customer).
- **Item**: Purchasable good or service; expense/asset account mapping.
- **Bill / lines**: Payable document; draft then posted; snapshots names, tax, rates, base equivalents.
- **Vendor credit / lines**: Linked correction of a posted bill or unapplied vendor credit.
- **Vendor payment**: Cash/bank outflow; not a bank-statement line.
- **Bill allocation**: Links payment or credit to bill, with date and amount.
- **Vendor refund**: Inflow against vendor advance.
- **Paid expense**: Immediate cash purchase; no AP.
- **AP aging row**: Derived, not stored balances.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator can complete bill → posted bill → partial payment → credit → refund for a sample vendor in one sitting (under 20 minutes) without a graphical app.
- **SC-002**: The 110 bill, 60 payment, 80 overpayment examples produce the stated outstanding and vendor-advance amounts in 100% of test runs.
- **SC-003**: Duplicate post or payment with the same key creates one financial effect; over-allocation against one bill never exceeds its original amount.
- **SC-004**: EUR 100 at 1.10 settled at 1.15 yields base AP 110 and realized FX loss 5; missing rate yields zero posted bill.
- **SC-005**: Aging as of a date before a payment still includes that bill's then-outstanding amount; trial balance AP equals AP subledger as of that date.
- **SC-006**: Cross-organization bill or payment access fails in 100% of attempts. Sales Clerk cannot create bills. Purchasing Clerk cannot post bills or record payments.
- **SC-007**: Changing a tax rate or contact name after posting leaves posted bill snapshots unchanged.
- **SC-008**: A paid expense posts expense and tax against bank with no AP change.

## Assumptions

- 002 ledger and 003 contacts, tax, FX rates, posting engine, sequences, period locks, and grants are already available.
- Accrual accounting. No cash-basis reports.
- No frontend. Printable output is the document JSON snapshot, not a typeset file.
- No email/SMS delivery or file attachments in this slice.
- Optional single-step approval is represented by role split (prepare vs post), not a separate approval engine.
- Default tax example is exclusive 10% for tests, not a real jurisdiction.
- Bank accounts for payments are GL-linked cash/bank accounts already on the chart; statement import is out of scope.
- Vendor advance is an asset (prepaid). Customer advance from 003 remains a liability.
- Input tax uses the tax rate's existing tax account (debit on purchase, credit on sale).

## Out of Scope

- Any user interface.
- Purchase orders, goods receipts, warehouses, stock valuation.
- Attachments, receipt preview, supplier portal, email, PDF.
- Recurring bills, reminders, multilevel approval, payment runs.
- Unrealized FX revaluation and period-end FX.
- Country e-invoicing and filing.
