# Implementation Plan: Purchases and Payables

**Branch**: `004-purchases-payables` | **Date**: 2026-09-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-purchases-payables/spec.md`

## Summary

API-only buy path on the 002 ledger and 003 tax/FX/settlement conventions: vendor flag on contacts, bills that post through the shared engine, paid expenses (cash, no AP), vendor payments/credits/refunds/advances, stored-rate FX, AP aging as-of. No screens, POs, attachments, PDF, or email.

## Technical Context

**Language/Version**: Python 3.12+

**Primary Dependencies**: Django/DRF already installed; reuse finance posting, tax, FX resolve_rate, sequences, grants, envelope

**Storage**: PostgreSQL for concurrency allocation tests; SQLite for calculation/API tests

**Testing**: pytest-django

**Target Platform**: Existing Django API

**Project Type**: Backend feature in `backend/apps/finance/`

**Performance Goals**: Single document post p95 ≤ 1s (design target)

**Constraints**: No frontend. No new dependencies. One posting engine. Decimal money. Role split instead of approval engine.

**Scale/Scope**: FIN-04/06/10 purchases slice. Not GA.

## Constitution Check

| Principle | Status | Notes |
|---|---|---|
| Auth Separation | PASS | No new credential APIs |
| Speckit Before Code | PASS | |
| Ponytail Ultra | PASS | Mirror 003; no PO/attachment/approval engine |
| Tenant Isolation | PASS | Same `_org_action` + RLS in `finance_tx` |
| Privacy | PASS | Existing audit/envelope |

Post-design: PASS. Journal `source_type` extended for bill/expense/vendor settlement; AP/vendor-advance control accounts allowed for those types.

## Project Structure

```text
specs/004-purchases-payables/
backend/apps/finance/
  models/purchases.py
  services/purchases.py
  selectors/aging.py          # add ap_aging
  api/purchase_views.py
```

**Structure Decision**: Stay inside `apps.finance`. Do not add a second app or frontend. Do not overload sales Allocation.

## Complexity Tracking

No constitution violations.
