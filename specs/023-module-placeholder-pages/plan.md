# Implementation Plan: Finance module placeholder pages

**Branch**: `023-module-placeholder-pages` | **Date**: 2026-09-18 | **Spec**: [spec.md](./spec.md)

## Summary

Extract a shared nav registry with hrefs. Wrap shell routes in `AppShell` layout (route group `(shell)`, not in URLs). Serve module pages via one validated catch-all placeholder; keep dashboard as-is. No CRUD/forms. No `books` path segments or folder names.

## Technical Context

**Stack**: Next.js App Router, existing shell  
**Approach**: `frontend/src/features/shell/nav.ts` + `(app)/(shell)/layout.tsx` + `(shell)/[...slug]/page.tsx`  
**Constraints**: Ponytail ultra — one placeholder component, no per-file page explosion

## Structure

```text
frontend/src/features/shell/nav.ts
frontend/src/features/shell/module-placeholder.tsx
frontend/src/app/(app)/(shell)/layout.tsx
frontend/src/app/(app)/(shell)/dashboard/page.tsx
frontend/src/app/(app)/(shell)/[...slug]/page.tsx
specs/023-module-placeholder-pages/research-rbac.md
```

## Follow-ups (not this feature)

- `useFinancePermissions` + `<Can>` gates wired to `FinanceGrant` / `ACTIONS`
- Permission fields on `nav.ts` children; hide modules without view/create grants
- See [research-rbac.md](./research-rbac.md)
