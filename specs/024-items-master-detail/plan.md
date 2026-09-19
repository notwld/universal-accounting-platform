# Plan: Items master-detail workspace

**Date**: 2026-09-19 | **Spec**: [spec.md](./spec.md)

## Summary

Ship a reusable master-detail workspace (list + preview) per UX research (side-by-side on desktop, stacked on mobile; search + progressive filter disclosure; paginated list; empty detail state). Use it for five Items routes against existing finance APIs.

## Design read

Redesign-preserve of UAP shell; dense product UI; IBM Plex already in place. Dials: VARIANCE 3 · MOTION 3 · DENSITY 8.

## Structure

```text
frontend/src/features/workspace/master-detail-workspace.tsx
frontend/src/features/items/api.ts
frontend/src/features/items/items-page.tsx
frontend/src/features/items/warehouses-page.tsx
frontend/src/features/items/stock-balances-page.tsx
frontend/src/features/items/stock-adjustments-page.tsx
frontend/src/features/items/stock-transfers-page.tsx
frontend/src/app/(app)/(shell)/items/page.tsx
frontend/src/app/(app)/(shell)/items/warehouses/page.tsx
...
```

## Research notes

- Master-detail: sync selection, empty detail placeholder, preserve filters across selection ([UX Patterns](https://uxpatternsguide.com/patterns/master-detail/)).
- Filters: icon toggles panel; show applied state; search complements filters ([SaaS UI](https://www.saasui.design/blog/saas-filtering-sorting-ux-patterns)).
- Pagination: numbered “X–Y of Z” for stable position in dense SaaS lists.
