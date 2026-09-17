# Verification: Recurring Documents

**Date**: 2026-09-17

## Commands

```powershell
Set-Location backend
..\.venv\Scripts\python manage.py check
..\.venv\Scripts\python -m pytest apps\finance\tests\test_recurring.py -q
```

`manage.py check` clean. Recurring test passed: day-31 → 31 Jan + 28 Feb drafts, replay empty, pause blocks March, bill draft + posted expense, expense replay does not add journals.

## Not in this slice

Screens, weekly/yearly cadences, auto-post invoices/bills, reminders, approvals, gateways, portal.

`.xls` / OFX / QIF / live bank feeds: do not add until a named bank actually sends that format.
