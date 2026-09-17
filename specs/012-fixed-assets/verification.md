# Verification: Fixed Assets

**Date**: 2026-09-17

## Commands

```powershell
Set-Location backend
..\.venv\Scripts\python manage.py check
..\.venv\Scripts\python -m pytest apps\finance\tests\test_assets.py -q
```

`manage.py check` clean. Tests passed: capitalize 1,200 (replay does not duplicate); two months at 100 (accum 200); rerun silent; write-down 100; dispose 1 March proceeds 950 posts 50 loss; second dispose rejected; register NBV equals GL net.

## Not in this slice

Screens, SMS, Plaid/TrueLayer/Yodlee, declining-balance, component assets, tax depreciation packs, lease accounting.
