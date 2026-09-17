# Feature Specification: Sales and Collection

**Feature Branch**: `003-sales-collection`

**Created**: 2026-09-17

**Status**: Draft

**Input**: User description: "Build Phase 2 sales and collection on the existing finance ledger: contacts, items, tax, quotes, invoices, payments, credits, refunds, advances, foreign-currency settlement, and AR aging. Backend/API only — no screens. No bills, expenses, or purchasing. Reuse the posting engine. Production quality, not an MVP."

**Requirement coverage**: FIN-03 (sales/receivables without portal/recurring), FIN-06 (tax snapshots and FX settlement), FIN-10 (AR aging). FIN-14 screens deferred. Depends on 002 ledger.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Keep customers, items, and tax rules (Priority: P1)

A Sales Clerk or Accountant maintains organization-scoped contacts (customer role), sellable goods/services, payment terms, and dated tax rates. These records belong to one organization. Changing a contact name or tax rate later must not rewrite already posted invoices.

**Why this priority**: Invoices cannot be issued without master data and tax definitions.

**Independent Test**: Create a customer, item, tax rate, and terms in org A; confirm they are invisible in org B; change the tax rate after a posted invoice and confirm the invoice still shows the original tax.

**Acceptance Scenarios**:

1. **Given** finance setup is complete, **When** an authorized user creates a customer contact, a service item, payment terms, and a tax rate effective on a date, **Then** those records are stored only for the selected organization.
2. **Given** the same user selected into organization B, **When** they list contacts or items, **Then** A's records are not returned.
3. **Given** a tax rate later changes, **When** a previously posted invoice is retrieved, **Then** its tax amounts, rate, and labels remain the posted snapshot.

---

### User Story 2 - Quote then invoice, then post once (Priority: P1)

A Sales Clerk prepares a quote (no ledger effect), converts it to an invoice draft, and an Accountant posts it. Posting creates AR, revenue, and tax in the shared ledger using server-calculated totals. Email or print delivery is not posting. Drafts can show a posting preview that does not affect reports.

**Why this priority**: This is the sell path; quotes must not post, and posting must not depend on delivery.

**Independent Test**: Quote → invoice → preview → post; retrying the post key does not create a second journal; a quote never appears on trial balance.

**Acceptance Scenarios**:

1. **Given** a customer, item, and exclusive tax of 10% on net 100, **When** an invoice is posted, **Then** the books show Dr AR 110, Cr revenue 100, Cr tax payable 10, and the invoice is posted and numbered.
2. **Given** a quote for the same lines, **When** it is saved or accepted, **Then** trial balance is unchanged. **When** it is converted to an invoice, **Then** a new invoice draft exists linked to the quote and the quote is not deleted.
3. **Given** an invoice draft, **When** posting preview is requested, **Then** proposed journal lines are returned and no journal is written. **When** posting succeeds, **Then** one journal exists linked to that invoice.
4. **Given** a posted invoice, **When** line prices or tax are edited, **Then** the change is rejected. Correction uses a credit note.
5. **Given** a Sales Clerk, **When** they create an invoice draft, **Then** it succeeds; **When** they post it, **Then** posting is denied. An Accountant can post.
6. **Given** a successful post, **When** the same idempotency key is retried, **Then** the original posted invoice is returned. Delivery is out of scope; posting does not send messages.

---

### User Story 3 - Collect, credit, refund, and not over-allocate (Priority: P1)

An Accountant records customer receipts against posted invoices, including partial payment, overpayment (customer advance), credit notes applied to invoices, and refunds of advances or credits. Allocations cannot exceed remaining invoice balance or remaining payment/credit. Concurrent allocations cannot over-settle.

**Why this priority**: Collection is the rest of the sell path; outstanding balances must stay truthful.

**Independent Test**: Invoice 110 → pay 60 → outstanding 50 → pay 80 → AR 0 and advance 30 → credit/refund path; two concurrent 80 allocations against 100 fail one atomically.

**Acceptance Scenarios**:

1. **Given** a posted invoice of 110, **When** a receipt of 60 is allocated to it, **Then** Dr bank 60, Cr AR 60, outstanding 50.
2. **Given** remaining 50, **When** a receipt of 80 is allocated, **Then** Dr bank 80, Cr AR 50, Cr customer advance 30.
3. **Given** a posted credit note against that customer, **When** it is applied to an open invoice, **Then** outstanding decreases without creating a second cash posting.
4. **Given** an advance, **When** a refund is recorded, **Then** the advance decreases and cash/bank decreases; the original receipt remains.
5. **Given** two concurrent allocations of 80 against an invoice of 100, **When** both complete, **Then** at most 100 is allocated and the conflicting request fails without corrupting balances.
6. **Given** a posted payment, **When** it is mutated, **Then** the attempt is rejected; corrections are new documents linked to the original.

---

### User Story 4 - Foreign-currency invoices and dated AR (Priority: P2)

An organization with USD books can invoice in EUR using a stored rate. Settlement at a different rate produces realized FX. AR aging as of a past date uses settlements known at that date, not today's remaining balance. Drafts never appear in aging or financial totals.

**Why this priority**: Phase 2 gate requires FX settlement and historical aging tied to the ledger.

**Independent Test**: EUR 100 at 1.10, paid at 1.15; aging as-of before payment still shows the receivable; GL AR matches the subledger.

**Acceptance Scenarios**:

1. **Given** USD books and rate 1.10, **When** EUR 100 plus no tax is posted, **Then** AR is USD 110 (base = foreign × stored rate). Missing rate blocks posting.
2. **Given** that invoice, **When** it is paid in EUR 100 at 1.15, **Then** Dr bank 115, Cr AR 110, Cr realized FX gain 5.
3. **Given** a partial payment after invoice date, **When** AR aging is requested as of a date before the payment, **Then** the invoice still appears outstanding for the pre-payment amount.
4. **Given** drafts, **When** aging or trial balance is requested, **Then** they are omitted.
5. **Given** AR control total from the ledger, **When** compared to open invoice minus allocations as of the same date, **Then** they agree.

---

### User Story 5 - Operate sales through the API without screens (Priority: P2)

Authorized operators complete contacts, quotes, invoices, posting, payments, credits, refunds, and aging through the versioned finance API. No graphical application ships.

**Why this priority**: Product owner deferred all screens.

**Independent Test**: Drive US1–US4 solely via documented API requests, including permission and cross-organization negatives.

**Acceptance Scenarios**:

1. **Given** a valid grant, **When** the operator runs quote → invoice → post → partial pay → credit → refund, **Then** each step succeeds or fails with a stable reason (closed period, imbalance, over-allocation, missing rate, insufficient permission, cross-organization, stale version, idempotency conflict).
2. **Given** organization A selected, **When** a B invoice id is referenced, **Then** no B data is returned.

---

### Edge Cases

- Inclusive tax: quoted price includes tax; net and tax still snapshot and post correctly.
- Zero-tax / exempt line next to a taxed line on one invoice.
- Invoice in base currency: no FX lines.
- Credit exceeding remaining invoice balance: rejected, not silent over-apply.
- Refund exceeding remaining advance/credit: rejected.
- Period locked covering invoice date: post rejected.
- Inactive item or contact: new drafts rejected; posted history unchanged.
- Contact is both customer and vendor later: this slice only uses the customer role; one contact record.
- Sales order, stock, bills, expenses, recurring invoices, customer portal, email delivery, and PDF files are out of scope.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Contacts, items, payment terms, tax rates, quotes, invoices, credit notes, customer payments, allocations, refunds, and AR aging MUST be organization-scoped from trusted membership context.
- **FR-002**: A contact MAY be marked as a customer in this slice. Vendor-only purchasing workflows are out of scope. One contact record per party per organization.
- **FR-003**: Items are goods or services. Tracked inventory, warehouses, and COGS from stock layers are out of scope. Service and untracked goods may be invoiced.
- **FR-004**: Tax rates are dated, organization-owned, and support exclusive and inclusive pricing. Posted documents snapshot tax identity, rate, and computed tax. A later rate change MUST NOT rewrite posted documents.
- **FR-005**: Quotes MUST NOT post to the ledger. Converting a quote creates an invoice draft linked to it.
- **FR-006**: Invoice posting MUST use the shared posting engine. Server recalculates totals. Client totals are not authoritative. Posted commercial fields are immutable.
- **FR-007**: Invoice posting MUST debit AR control, credit revenue (and other income accounts as mapped), and credit tax payable for output tax. Unexplained imbalance rejects the post with no partial write.
- **FR-008**: Sales Clerk MAY create/edit drafts of quotes and invoices. Posting invoices, recording payments, and issuing credits/refunds require the corresponding action permissions (not implied by Sales Clerk).
- **FR-009**: Customer payments allocate to invoices under lock. Allocations MUST NOT exceed remaining invoice balance or remaining payment funds. Excess receipt is a customer advance liability.
- **FR-010**: Credit notes reduce receivable when applied. Refunds reduce cash/bank and outstanding credit or advance. Original posted documents remain.
- **FR-011**: Idempotency is per organization, operation, and key for post invoice, record payment, apply credit, and refund.
- **FR-012**: Foreign amounts convert as base = foreign × stored rate. Missing rate blocks posting and settlement. Settlement difference posts to realized FX. Unrealized revaluation is out of scope.
- **FR-013**: AR aging and outstanding balances as of a date MUST use documents and allocations with dates on or before that date. Drafts excluded. Results MUST tie to AR control in the ledger as of the same date.
- **FR-014**: Document numbers unique per organization, type, and series; issued numbers not reused.
- **FR-015**: No screens, empty navigation, PDF renderer, email send, customer portal, recurring billing, or purchase documents in this feature.
- **FR-016**: Posting MUST NOT be triggered by delivery. This slice does not enqueue delivery; a future delivery retry MUST be able to exist without creating another journal (no post-on-send hook).

### Key Entities

- **Contact**: Organization party; customer flag in this slice.
- **Item**: Sellable good or service; price default; tax mapping optional.
- **Payment term**: Due-date rule (e.g. due on receipt, net N days).
- **Tax rate**: Dated rate, inclusive/exclusive, name/label.
- **Quote / lines**: Non-posting offer; may convert to invoice.
- **Invoice / lines**: Receivable document; draft then posted; snapshots names, tax, rates, base equivalents.
- **Credit note / lines**: Linked correction of a posted invoice or unapplied customer credit.
- **Customer payment**: Cash/bank receipt; not a bank-statement line.
- **Allocation**: Links payment or credit to invoice, with date and amount.
- **Customer refund**: Outflow against advance or credit.
- **Exchange rate**: Manual stored rate for a currency pair and date.
- **AR aging row**: Derived, not stored balances.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator can complete quote → posted invoice → partial payment → credit → refund for a sample customer in one sitting (under 20 minutes) without a graphical app.
- **SC-002**: The 110 invoice, 60 receipt, 80 overpayment examples produce the stated outstanding and advance amounts in 100% of test runs.
- **SC-003**: Duplicate post or payment with the same key creates one financial effect; concurrent over-allocation against one invoice never exceeds its original amount.
- **SC-004**: EUR 100 at 1.10 settled at 1.15 yields base AR 110 and realized FX gain 5; missing rate yields zero posted invoice.
- **SC-005**: Aging as of a date before a payment still includes that invoice's then-outstanding amount; trial balance AR equals AR subledger as of that date.
- **SC-006**: Cross-organization invoice or payment access fails in 100% of attempts. Sales Clerk cannot post invoices or record payments.
- **SC-007**: Changing a tax rate or contact name after posting leaves posted invoice snapshots unchanged.

## Assumptions

- 002 ledger, sequences, period locks, grants, and shared posting are already available.
- Accrual accounting. No cash-basis reports.
- No frontend. Printable output is the document JSON snapshot, not a typeset file.
- No email/SMS delivery in this slice. Posting is an explicit action.
- Optional single-step approval is represented by role split (prepare vs post), not a separate approval engine. Multilevel/threshold approval is a later package.
- Default tax example is exclusive 10% for tests, not a real jurisdiction.
- Bank accounts for receipts are GL-linked cash/bank accounts already on the chart; statement import is out of scope.
- Purchases, expenses, attachments, inventory, recurring invoices, reminders, and portal are out of scope.

## Out of Scope

- Any user interface.
- Bills, expenses, vendor payments, purchase orders.
- Sales orders, warehouses, stock valuation.
- Customer portal, gateways, email delivery, PDF libraries.
- Recurring invoices, reminders, multilevel approval.
- Unrealized FX revaluation and period-end FX.
- Country e-invoicing and filing.
