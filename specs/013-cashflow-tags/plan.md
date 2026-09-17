# Implementation Plan: Cash Flow, Tags, and Comparative Reports

**Branch**: `013-cashflow-tags` | **Date**: 2026-09-17 | **Spec**: [spec.md](./spec.md)

## Summary

Tags on journal lines; filter TB/GL/P&L. Account `cashflow_kind`. Indirect cash-flow selector. Comparative query params on existing P&L/BS without renaming current keys.

## Technical Context

Python 3.12, Django/DRF, existing report selectors. No new dependencies.

## Constitution Check

PASS. RLS on tag table. Tags are not a tenant. Posted lines stay immutable.

## Project Structure

```text
backend/apps/finance/models/config.py  (ReportingTag, Account.cashflow_kind)
backend/apps/finance/models/ledger.py  (JournalLine.tag)
backend/apps/finance/selectors/reports.py
backend/apps/finance/tests/test_reports.py
```
