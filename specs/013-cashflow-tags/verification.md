# Verification: Cash Flow, Tags, and Comparative Reports

**Date**: 2026-09-17

## Commands

```powershell
Set-Location backend
..\.venv\Scripts\python manage.py check
..\.venv\Scripts\python -m pytest apps\finance\tests\test_reports.py apps\finance\tests\test_banking.py -q
```

`manage.py check` clean. Tests passed: cash-flow operating 80 / investing −200 / financing 1,000 / net 880 equals cash change; tagged P&L omits untagged expense; comparative P&L prior net income 0; existing banking P&L/BS still green.

## Not in this slice

Screens, SMS, Plaid/TrueLayer/Yodlee, year-close posting, FX revaluation, tax reports, PDF/CSV/XLSX export, direct-method cash flow.
