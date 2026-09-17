# Implementation Plan: Bank Rules

**Branch**: `009-bank-rules` | **Date**: 2026-09-17 | **Spec**: [spec.md](./spec.md)

## Summary

API-only bank rules: case-insensitive description contains-text, optional sign, priority, apply unmatched lines via existing `categorize_line`. No frontend. No import side-effect.

## Technical Context

Python 3.12, Django/DRF, existing banking + posting. No new dependencies.

## Constitution Check

PASS. Speckit artifacts present. Reuse categorize; RLS on new table; Clerk/org header unchanged.

## Project Structure

```text
backend/apps/finance/models/banking.py
backend/apps/finance/services/banking.py
backend/apps/finance/api/bank_views.py
backend/apps/finance/api/urls.py
backend/apps/finance/sql/rls.sql
backend/apps/finance/tests/test_bank_rules.py
```
