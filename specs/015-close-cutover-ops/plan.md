# Implementation Plan: Period close tails, cutover, webhooks, ops

**Branch**: `015-close-cutover-ops` | **Date**: 2026-09-18 | **Spec**: [spec.md](./spec.md)

## Summary

Extend existing Django finance: reversing adjustments, unrealized FX via `post_generated`/`reverse_journal`, ordered cutover on `FinanceSettings`, HMAC outbox, PDF from the existing export helper, golden JSON, Postgres CI two-role job.

## Technical Context

Python 3.12, Django 5, DRF, PostgreSQL 16, pytest. SQLite remains the fast suite. `httpx` already installed. PDF is a tiny stdlib writer (no ReportLab).

## Constitution Check

PASS: org resolvers, `finance_tx`, posted journals immutable, RLS ENABLE-without-FORCE, no secrets in logs.

## Project Structure

```text
backend/apps/finance/models/config.py
backend/apps/finance/services/adjustments.py
backend/apps/finance/services/fx.py
backend/apps/finance/services/cutover.py
backend/apps/finance/services/webhooks.py
backend/apps/finance/api/ops_views.py
.github/workflows/finance-postgres.yml
```
