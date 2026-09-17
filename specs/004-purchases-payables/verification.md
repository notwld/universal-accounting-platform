# Verification — 004-purchases-payables

**Date**: 2026-09-17  
**Frontend**: not built (product owner).

## Commands

From `backend/`:

```text
..\.venv\Scripts\python -m pytest apps\finance\tests apps\authentication\tests -q
→ 21 passed, 1 skipped (Postgres isolation)  exit 0

..\.venv\Scripts\python manage.py check
→ System check identified no issues (0 silenced)  exit 0

..\.venv\Scripts\python manage.py makemigrations --check --dry-run
→ No changes detected  exit 0
```

## Coverage vs spec

| Story | Evidence |
|---|---|
| US1 vendor/item/tax | `_purchase_setup` in `test_purchases.py` |
| US2 bill 110 + paid expense 55 | `test_bill_payment_expense_refund` |
| US3 pay 60/80, advance, refund, over-allocation | same |
| US4 FX 1.10/1.15 loss, missing_rate, aging as-of | `test_fx_bill_and_settlement` |
| Clerk split | purchasing clerk drafts, cannot post; sales clerk cannot create bills |

## Remaining

- Postgres RLS/concurrency gate still skipped on SQLite.
- Vendor-credit posting is implemented (`POST /vendor-credits`) but the happy-path test covers refund-of-advance instead.
- Screens, attachments, purchase orders, PDF, and payment runs are out of scope.
