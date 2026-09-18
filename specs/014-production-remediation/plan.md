# Implementation Plan: Finance Backend Production Remediation

**Branch**: `014-production-remediation` | **Date**: 2026-09-18 | **Spec**: [spec.md](./spec.md)  
**Source**: `docs/engineering/finance-backend-production-remediation.md`

## Summary

Fix P1 defects B0–B7 and named P2 B8/B10 in the existing Django finance module. No new tenant model. No frontend.

## Technical Context

Python 3.12, Django 5, PostgreSQL 16, existing `finance_tx` / `post_generated`. SQLite remains the fast suite; Postgres tests skip unless `DATABASE_URL` is PostgreSQL.

## Constitution Check

PASS if RLS stays ENABLE-without-FORCE, posted journals stay immutable, and org resolvers never trust raw FKs.

## Project Structure

```text
backend/apps/finance/services/resolve.py
backend/apps/finance/services/money.py
backend/apps/finance/services/posting.py
backend/apps/finance/tests/postgres/
deploy/postgres/init.sql
```
