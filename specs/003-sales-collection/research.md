# Research: Sales and Collection

## 1. Frontend / delivery / PDF

- **Decision**: None. Posting is an explicit named action. Document GET returns the snapshot (the printable artifact).
- **Rationale**: Owner: no screens. Delivery retry must never post; skipping delivery removes the hazard.
- **Alternatives**: PDF lib, email outbox — deferred.

## 2. Approval

- **Decision**: Sales Clerk drafts; `finance.document.post` / `finance.payment.record` required to post money. No ApprovalDecision table.
- **Rationale**: Spec: role split is the single-step policy. Multilevel is package H.
- **Alternatives**: Pending-approval status — extra state machine without a second actor type.

## 3. Posting

- **Decision**: Extend `post_journal` path with generated lines and `source_type` in {invoice, payment, credit, refund}. Allow AR/advance/tax control accounts only for those types. Invoice header is immutable after post; journal is the GL.
- **Rationale**: One engine. 002 blocked control accounts except opening.
- **Alternatives**: Signals on invoice save — forbidden.

## 4. Documents

- **Decision**: Separate Quote, Invoice, CreditNote, CustomerPayment models. Quote has no journal_id. Invoice stores snapshots on lines (description, qty, unit, tax id/rate/amount, currency, rate, base amounts).
- **Rationale**: Product rule: distinct models where lifecycle differs; no universal JSON document.
- **Alternatives**: One polymorphic document table — rejected by the product plan.

## 5. Tax / FX

- **Decision**: One `compute_line_tax` (exclusive: tax=net*rate; inclusive: split from gross). FX: `base = foreign * stored_rate`; `ExchangeRate` unique (org, quote_currency, date) vs base currency. Realized FX on settlement only.
- **Rationale**: Spec formula. Unrealized revaluation is later.
- **Alternatives**: Feed rates — no provider chosen.

## 6. Allocations

- **Decision**: `Allocation` rows; `select_for_update` on invoice then payment/credit. Remaining = posted_total − sum(allocations). Overpay remainder → advance journal, not extra AR credit.
- **Rationale**: Spec concurrent-allocation gate.
