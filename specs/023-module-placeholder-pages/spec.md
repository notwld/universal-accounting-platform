# Feature Specification: Finance module placeholder pages

**Feature Branch**: `023-module-placeholder-pages`

**Created**: 2026-09-18

**Status**: Ready for planning

**Input**: Create a page for each sidebar item; forms and CRUD will come later — placeholders for now.

## User Scenarios & Testing

### User Story 1 - Navigate to every module page (Priority: P1)

An authenticated user with an organization can open each sidebar child and land on a dedicated page that names the module and states that list/forms/CRUD will follow.

**Why this priority**: Unblocks navigation IA and future screen work.

**Independent Test**: Click every sidebar child; each resolves to a real route (no 404) inside the app shell.

**Acceptance Scenarios**:

1. **Given** the user is on the dashboard, **When** they open any sidebar child link, **Then** they see a page titled with that item’s name inside the shell.
2. **Given** an unknown module path, **When** visited, **Then** the app returns not found (not a blank generic page claiming a fake module).

### User Story 2 - Honest placeholder copy (Priority: P2)

Each page notes that list/forms/CRUD **and RBAC** are planned, without fake financial data.

**Acceptance Scenarios**:

1. **Given** a module placeholder, **When** viewed, **Then** copy indicates upcoming list/forms/CRUD and permission-aware UI, and does not invent balances or documents.

### Edge Cases

- Active nav highlighting matches the current path.
- Mobile drawer closes after navigation.
- Home/dashboard remains the existing dashboard page.
- Future RBAC must not treat hidden nav as security; API remains authoritative.

## Requirements

- **FR-001**: Every sidebar child has an `href` to a real App Router page.
- **FR-002**: Pages share one placeholder presentation; no per-module CRUD yet.
- **FR-003**: Placeholder states that forms, CRUD, and RBAC (permission-gated nav/actions) will be added later.
- **FR-004**: Invalid module paths → not found.
- **FR-005**: Single nav registry drives sidebar labels and routes.
- **FR-006**: RBAC design must follow production practices in [research-rbac.md](./research-rbac.md): UI affordance only; backend `FinanceGrant` / `ACTIONS` enforce; gate on permission actions not role name strings.

## Success Criteria

- **SC-001**: Zero sidebar children remain unlinked `#` / “coming soon” only spans.
- **SC-002**: Visiting each registered href returns HTTP 200 in the app.
- **SC-003**: No mocked monetary amounts on placeholder pages.
- **SC-004**: Placeholder copy mentions upcoming RBAC without implementing gates yet.

## Assumptions

- Routes live under the authenticated shell (same chrome as dashboard). No `books` path segment.
- Backend API mapping may appear as metadata for future work, not live fetches yet.
- Effective permissions will come from org-scoped grants APIs already on the backend; frontend will not invent a second policy language.
