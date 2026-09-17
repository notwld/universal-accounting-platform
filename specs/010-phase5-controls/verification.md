# Verification: Phase 5 Controls and Statement Formats

**Date**: 2026-09-17

## Commands

```powershell
Set-Location backend
..\.venv\Scripts\python manage.py check
..\.venv\Scripts\python -m pytest apps\finance\tests\test_phase5.py apps\finance\tests\test_bank_rules.py apps\finance\tests\test_approvals.py apps\finance\tests\test_banking.py apps\finance\tests\test_sales.py apps\finance\tests\test_purchases.py apps\finance\tests\test_recurring.py -q
```

`manage.py check` clean. Tests passed: reminder email once then replay silent; no-email exception then resolve; regex+amount auto-apply on import; OFX/QIF/XLS duplicate the CSV fee fingerprint; loopback feed URL rejected; mocked HTTPS fetch duplicates; saved filter lists posted invoices only; threshold 200 posts 110 without approval; two distinct approvers required above threshold.

## Not in this slice

Screens, SMS, Plaid/TrueLayer/Yodlee, payment gateways, customer portal, split/group matching.
