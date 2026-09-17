# Verification: Banking and Reports

**Date**: 2026-09-17

## Commands

```powershell
Set-Location backend
..\.venv\Scripts\python manage.py check
..\.venv\Scripts\python -m pytest apps\finance\tests\test_banking.py -q
```

`manage.py check` clean. `test_banking.py` passed: XLSX import (ISO + Excel serial dates), CSV re-import as duplicates, match does not post, categorize posts `source_type=bank`, recon imbalance vs complete, P&L/BS tie.

## Not in this slice

Screens, split/group matching, transfers, FX revaluation, report CSV export.

Do not add `.xls`, OFX/QIF, or live feeds until a named bank actually sends that format.
