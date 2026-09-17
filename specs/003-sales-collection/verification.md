# Verification — 003-sales-collection

**Date**: 2026-09-17  
**Frontend**: not built (product owner).

## Commands

From `backend/`:

```text
..\.venv\Scripts\python -m pytest apps\finance\tests apps\authentication\tests -q
→ 19 passed, 1 skipped (Postgres isolation)  exit 0

..\.venv\Scripts\python manage.py check
→ System check identified no issues (0 silenced)  exit 0

..\.venv\Scripts\python manage.py makemigrations --check --dry-run
→ No changes detected  exit 0
```

## Coverage vs spec

| Story | Evidence |
|---|---|
| US1 contacts/items/tax | `_sales_setup` in `test_sales.py` |
| US2 quote → invoice → post 110 | `test_invoice_payment_credit_refund` |
| US3 pay 60/80, advance, refund, over-allocation | same |
| US4 FX 1.10/1.15, missing_rate, aging as-of | `test_fx_invoice_and_settlement`, aging in first test |
| Clerk cannot post | first test grants `sales_clerk` |

## Remaining

- Postgres RLS/concurrency gate still skipped on SQLite.
- Credit-note posting is implemented (`POST /credit-notes`) but the happy-path test covers refund-of-advance instead.
- Screens, PDF, email, bills, and purchasing are out of scope.
