# Verification: Bank Rules

**Date**: 2026-09-17

## Commands

```powershell
Set-Location backend
..\.venv\Scripts\python manage.py check
..\.venv\Scripts\python -m pytest apps\finance\tests\test_bank_rules.py apps\finance\tests\test_banking.py -q
```

`manage.py check` clean. Tests passed: control-account rule rejected; outflow "fee" priority 1 categorizes −15 Bank fee to purchases not the alt expense; matched −60 payment untouched; +15 FEE REFUND left imported; apply replay posts nothing.

## Not in this slice

Screens, auto-apply on import, regex/amount-range rules, split/group matching, `.xls`/OFX/QIF/live feeds.
