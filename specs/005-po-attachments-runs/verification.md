# Verification — 005-po-attachments-runs

**Date**: 2026-09-17  
**Frontend**: not built (product owner).

## Commands

From `backend/`:

```text
..\.venv\Scripts\python -m pytest apps\finance\tests apps\authentication\tests -q
→ 22 passed, 1 skipped (Postgres isolation)  exit 0

..\.venv\Scripts\python manage.py check
→ System check identified no issues (0 silenced)  exit 0

..\.venv\Scripts\python manage.py makemigrations --check --dry-run
→ No changes detected  exit 0
```

## Coverage vs spec

| Story | Evidence |
|---|---|
| US1 attachments | `test_po_payment_run_attachment_statement` |
| US2 PO convert | same; TB empty until bill post |
| US3 payment run | two bills, replay same id |
| US4 statement + credits | vendor-statement GET; credit-note in `test_sales`; vendor-credit in `test_purchases` |

## Remaining

- Screens still deferred.
- Next: Phase 4 banking (CSV import, match, reconcile, P&L/BS).
