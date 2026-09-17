# Implementation Plan: Inventory Stock and Valuation

**Branch**: `011-inventory-stock` | **Date**: 2026-09-17 | **Spec**: [spec.md](./spec.md)

## Summary

API-only tracked stock with moving-average balances. Bill receive / invoice issue reuse existing posting; transfers have no GL; adjustments post COGS vs inventory.

## Technical Context

Python 3.12, Django/DRF, existing `post_generated`. No new dependencies.

## Constitution Check

PASS. RLS on new tables. Warehouses are not a second tenant.

## Project Structure

```text
backend/apps/finance/models/stock.py
backend/apps/finance/services/stock.py
backend/apps/finance/api/stock_views.py
backend/apps/finance/tests/test_stock.py
```
