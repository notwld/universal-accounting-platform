# Implementation Plan: Sales and Collection

**Branch**: `003-sales-collection` | **Date**: 2026-09-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-sales-collection/spec.md`

## Summary

API-only sales path on the 002 ledger: contacts/items/tax/terms, quotes (no post), invoices that post through the shared engine, receipts/allocations/credits/refunds/advances, stored-rate FX, AR aging as-of. No screens, bills, PDF, or email.

## Technical Context

**Language/Version**: Python 3.12+

**Primary Dependencies**: Django/DRF already installed; reuse finance posting, sequences, grants, envelope

**Storage**: PostgreSQL for concurrency allocation tests; SQLite for calculation/API tests

**Testing**: pytest-django

**Target Platform**: Existing Django API

**Project Type**: Backend feature in `backend/apps/finance/`

**Performance Goals**: Single document post p95 ≤ 1s (design target)

**Constraints**: No frontend. No new dependencies. One posting engine. Decimal money. Role split instead of approval engine.

**Scale/Scope**: FIN-03/06/10 sales slice. Not GA.

## Constitution Check

| Principle | Status | Notes |
|---|---|---|
| Auth Separation | PASS | No new credential APIs |
| Speckit Before Code | PASS | |
| Ponytail Ultra | PASS | No PDF/email/approval engine; quotes+invoices+settlement only |
| Tenant Isolation | PASS | Same `_org_action` + RLS in `finance_tx` |
| Privacy | PASS | Existing audit/envelope |

Post-design: PASS. Journal `source_type` extended; control accounts allowed for document sources only.

## Project Structure

```text
specs/003-sales-collection/
backend/apps/finance/
  models/sales.py          # contact, item, tax, terms, quote, invoice, credit, payment
  services/tax.py
  services/sales.py        # invoice post, allocations
  selectors/aging.py
  api/sales_views.py
```

**Structure Decision**: Stay inside `apps.finance`. Do not add a second app or frontend.

## Complexity Tracking

No constitution violations.
