# Implementation Plan: Recurring Documents

**Branch**: `007-recurring-documents` | **Date**: 2026-09-17 | **Spec**: [spec.md](./spec.md)

## Summary

API-only monthly recurring invoices (draft), bills (draft), and expenses (posted once). Unique occurrence dates. Pause/resume. Reuse existing document create/post services.

## Technical Context

Python/Django, existing sales/purchases services, Celery beat daily run. No new dependencies. No frontend.

## Constitution Check

PASS.
