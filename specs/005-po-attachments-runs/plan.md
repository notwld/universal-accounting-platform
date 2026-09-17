# Implementation Plan: PO, Attachments, Payment Runs

**Branch**: `005-po-attachments-runs` | **Date**: 2026-09-17 | **Spec**: [spec.md](./spec.md)

## Summary

Finish Phase 3 API: org-scoped attachments, purchase orders (quote analog), payment runs (batched vendor payments), vendor statements, credit application tests. Then banking.

## Technical Context

**Language/Version**: Python 3.12+  
**Primary Dependencies**: Django FileField / FileResponse; reuse `post_vendor_payment`, `set_bill_lines`  
**Storage**: Default local media; PostgreSQL/SQLite  
**Testing**: pytest-django + SimpleUploadedFile  
**Constraints**: No screens. No new deps. 10 MiB, PDF/PNG/JPEG/WebP.

## Constitution Check

PASS: no credential APIs; Speckit artifacts; shortest reuse of sales quote/convert and vendor payment; `_org_action` + RLS.

## Project Structure

```text
backend/apps/finance/models/purchases.py   # PO, PaymentRun
backend/apps/finance/models/attachments.py
backend/apps/finance/services/purchases.py # convert_po, post_payment_run, statement
backend/apps/finance/api/purchase_views.py
```

## Complexity Tracking

None.
