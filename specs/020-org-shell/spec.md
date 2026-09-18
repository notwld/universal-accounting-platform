# Feature Specification: Org picker and app shell

**Feature Branch**: `020-org-shell`

**Created**: 2026-09-18

**Status**: Implemented

**Input**: When logged in, show organization cards, remember selection, redirect to dashboard with that org active; header/sidebar like Zoho Books (researched UX).

## User Scenarios & Testing

### User Story 1 - Pick an organization (Priority: P1)

A signed-in user sees organization cards, chooses one, and lands on the dashboard with that organization selected.

**Independent Test**: After sign-in, `/` lists orgs; clicking one opens `/dashboard` with the org name in the header.

### User Story 2 - Remember selection (Priority: P1)

Returning with a remembered org skips the picker and opens the dashboard already scoped.

**Independent Test**: Reload `/` with a saved org id still in memberships → redirect to `/dashboard`.

### User Story 3 - Shell navigation (Priority: P2)

Dashboard shows a dark top header and left sidebar (Home active); org remains visible.

**Independent Test**: `/dashboard` shows header + sidebar; unsigned users are sent to sign-in.

### Edge Cases

- No orgs: empty state with create organization.
- Saved org no longer a membership: clear and show picker.
- No fake finance amounts on the dashboard.

## Requirements

- **FR-001**: Signed-in home shows organization cards (or create).
- **FR-002**: Selected org is persisted and sent as `X-Organization-ID`.
- **FR-003**: Dashboard requires an active org.
- **FR-004**: Shell has header + sidebar matching the agreed Zoho-like structure.

## Success Criteria

- **SC-001**: User can go sign-in → org card → dashboard without losing org context on refresh.
- **SC-002**: Header shows the selected organization name.

## Assumptions

- Nav items beyond Home are visible but not fully built.
- Clerk session JWT authorizes API calls after bootstrap.

## Out of Scope

- Real receivables/payables widgets, full Sales nested routes, quick-create menu.
