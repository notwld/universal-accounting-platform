# Research: Purchases and Payables

## 1. Frontend / attachments / PDF

- **Decision**: None. No screens, no file storage, no receipt preview.
- **Rationale**: Owner: no screens. Phase 3 attachments are a later slice.
- **Alternatives**: Attachment authorization now — extra storage without a user workflow.

## 2. Approval

- **Decision**: Purchasing Clerk drafts bills; `finance.document.post` / `finance.payment.record` to post money. Sales Clerk has no bill.create. No ApprovalDecision table.
- **Rationale**: Same role-split as 003. Multilevel is package H.
- **Alternatives**: Pending-approval status — extra state without a second actor type.

## 3. Posting

- **Decision**: Reuse `post_generated`. Add `source_type` in {bill, expense, vendor_payment, vendor_credit, vendor_refund}. Allow AP/vendor-advance/tax control accounts for those types.
- **Rationale**: One engine. Invert the 003 sales journals.
- **Alternatives**: Signals on bill save — forbidden.

## 4. Documents

- **Decision**: Separate Bill, VendorCredit, VendorPayment, PaidExpense models. Separate BillAllocation (do not add bill FK to sales Allocation).
- **Rationale**: Product rule: distinct models where lifecycle differs. Overloading Allocation with eight nullable FKs is the wrong kind of reuse.
- **Alternatives**: One polymorphic document table — rejected by the product plan.

## 5. Tax / FX

- **Decision**: Reuse `line_tax` and `resolve_rate`. Input tax debits the tax rate's existing tax account. Vendor advance is an **asset**. FX: same `base = foreign × stored_rate`. Paying a EUR bill at a higher USD rate is a realized **loss**.
- **Rationale**: Spec. Unrealized revaluation is later.
- **Alternatives**: Separate recoverable-tax account — not needed until a country pack.

## 6. Paid expense

- **Decision**: One-shot posted document: Dr expense/tax, Cr bank. No AP, no allocation.
- **Rationale**: Spec US2. Distinct from a bill that is paid the same day (that remains bill + payment).
- **Alternatives**: Auto-create bill+payment — two documents for one user action.

## 7. Allocations

- **Decision**: `BillAllocation` rows; `select_for_update` on bill then payment/credit. Remaining = posted_total − sum(allocations). Overpay remainder → vendor advance asset.
- **Rationale**: Mirror 003 concurrent-allocation gate.
