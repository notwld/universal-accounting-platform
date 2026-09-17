# Implementation Plan: Banking and Reports

**Branch**: `006-banking-reports` | **Date**: 2026-09-17 | **Spec**: [spec.md](./spec.md)

## Summary

API-only bank CSV import, 1:1 match to existing payments, categorize via `post_generated`, reconciliation completeness check, P&L/BS from journal lines.

## Technical Context

Python 3.12, Django, csv stdlib, existing posting engine. No new dependencies. No frontend.

## Constitution Check

PASS.

## Project Structure

```text
backend/apps/finance/models/banking.py
backend/apps/finance/services/banking.py
backend/apps/finance/selectors/reports.py  # pnl, balance_sheet
backend/apps/finance/api/bank_views.py
```
