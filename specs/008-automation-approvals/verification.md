# Verification: Cadences, Auto-Post, Reminders, Approvals

**Date**: 2026-09-17

## Commands

```powershell
Set-Location backend
..\.venv\Scripts\python manage.py check
..\.venv\Scripts\python -m pytest apps\finance\tests\test_approvals.py apps\finance\tests\test_recurring.py apps\finance\tests\test_sales.py apps\finance\tests\test_purchases.py -q
```

`manage.py check` clean. 7 tests passed: weekly Mon 2026-06-01 → 01 and 08 Jun drafts; yearly 29 Feb 2024 + 28 Feb 2025; auto-post 15 Jul posted, replay no extra journals; approval required blocks post, self-approve forbidden, reject→draft, approve then post; reminder days_before_due=0 on due date one row, replay empty.

## Not in this slice

Screens, email/SMS, gateways, portal, multilevel approval chains, bank rules, `.xls`/OFX/QIF/live feeds.
