# Implementation Plan: Fixed Assets

**Branch**: `012-fixed-assets` | **Date**: 2026-09-17 | **Spec**: [spec.md](./spec.md)

## Summary

API-only asset register. Capitalize/depreciate/write-down/dispose reuse `post_generated`. Straight-line full months. Register NBV ties to cost and accum accounts.

## Technical Context

Python 3.12, Django/DRF, existing `post_generated`. No new dependencies.

## Constitution Check

PASS. RLS on new tables. Assets are not a second tenant. Idempotency on money posts.

## Project Structure

```text
backend/apps/finance/models/assets.py
backend/apps/finance/services/assets.py
backend/apps/finance/api/asset_views.py
backend/apps/finance/tests/test_assets.py
```
