# Verification: Inventory Stock and Valuation

**Date**: 2026-09-17

## Commands

```powershell
Set-Location backend
..\.venv\Scripts\python manage.py check
..\.venv\Scripts\python -m pytest apps\finance\tests\test_stock.py apps\finance\tests\test_sales.py apps\finance\tests\test_purchases.py -q
```

`manage.py check` clean. Tests passed: bill 10×8 → qty 10 value 80 inventory debit 80; invoice 4 → COGS 32 remaining 6/48; invoice 7 `negative_stock` with qty unchanged; transfer 2 to West; adjust −1 on Main; valuation `stock_total` equals `gl_inventory` (40). Existing untracked sales/purchases tests still green.

## Not in this slice

Screens, SMS, Plaid/TrueLayer/Yodlee, FIFO, lots/serials, assets, country packs.
