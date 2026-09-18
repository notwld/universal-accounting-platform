# Feature Specification: Frontend production folder structure

**Feature Branch**: `017-frontend-structure`

**Created**: 2026-09-18

**Status**: Implemented

**Input**: Search for a production-level Next.js folder structure and reorganize `frontend/` to match it. No finance screens.

## User Scenarios & Testing

### User Story 1 - Developers find code by kind of work (Priority: P1)

A developer adding a screen can tell where routes live versus shared UI versus API client, without hunting through `app/`.

**Independent Test**: `pnpm build` still succeeds; `/` still renders; non-route code is outside `app/`.

**Acceptance Scenarios**:

1. **Given** the scaffold, **When** listing `src/app`, **Then** it contains only routing files (layouts, pages, error, styles).
2. **Given** the scaffold, **When** looking for the HTTP client or org store, **Then** they live under `lib/` / `stores/`, not next to `page.tsx`.

### Edge Cases

- Route groups must not change public URLs (`/` stays `/`).
- Empty domain folders (sales, banking, …) are not created until a screen exists.

## Requirements

- **FR-001**: `app/` is routing-only (Next.js App Router convention).
- **FR-002**: Shared primitives stay in `components/ui` (shadcn). Providers and other app-wide UI sit in `components/`.
- **FR-003**: HTTP client, env, and query keys live under `lib/`.
- **FR-004**: No finance feature modules until a screen is specified.
- **FR-005**: Production error UI exists at the root route.

## Success Criteria

- **SC-001**: Production build completes.
- **SC-002**: Visiting `/` still shows the scaffold home.

## Assumptions

- Feature folders (`src/features/<domain>`) are the production home for future screens; they are added per screen, not as empty trees.
- `(app)` route group is the placeholder for the authenticated product; `(auth)` is added with Clerk screens.

## Out of Scope

- Finance routes, ClerkProvider, OpenAPI client, empty `hooks/` dump.
