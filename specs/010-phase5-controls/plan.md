# Implementation Plan: Phase 5 Controls and Statement Formats

**Branch**: `010-phase5-controls` | **Date**: 2026-09-17 | **Spec**: [spec.md](./spec.md)

## Summary

API-only: reminder SMTP, bank-rule regex/amount/auto-apply, XLS/OFX/QIF parsers into existing bank lines, HTTPS file feeds with SSRF checks, saved filters, exception queue, approval threshold + N distinct approvers. No frontend. No open-banking SDK.

## Technical Context

Python 3.12, Django/DRF, existing SMTP + httpx + posting/banking. Add `xlrd` only for BIFF `.xls`. Stdlib for OFX/QIF/regex.

## Constitution Check

PASS. Speckit artifacts present. Tenant RLS on new tables. Feed URLs cannot target private IPs. SMTP is transactional reminder mail, not Clerk OTP.

## Project Structure

```text
backend/apps/finance/models/banking.py
backend/apps/finance/models/config.py
backend/apps/finance/models/recurring.py
backend/apps/finance/services/banking.py
backend/apps/finance/services/reminders.py
backend/apps/finance/services/approvals.py
backend/apps/finance/services/workflow.py
backend/apps/finance/api/*.py
backend/apps/finance/tests/test_phase5.py
```
