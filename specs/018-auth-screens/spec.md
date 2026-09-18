# Feature Specification: Auth login and signup screens

**Feature Branch**: `018-auth-screens`

**Created**: 2026-09-18

**Status**: Implemented

**Input**: Simple login and signup screens in a centered container, using researched login UX. Clerk already owns credentials.

## User Scenarios & Testing

### User Story 1 - Sign in (Priority: P1)

A returning user opens sign-in, sees a centered card, enters email and password, and submits.

**Independent Test**: `/sign-in` shows a centered card with email, password, submit, and a link to sign-up.

### User Story 2 - Sign up (Priority: P1)

A new user opens sign-up, sees the same layout, enters email and password, and submits.

**Independent Test**: `/sign-up` shows a centered card with email, password, submit, and a link to sign-in.

### Edge Cases

- Password is masked with a show/hide control; signup does not ask to type it twice.
- Invalid submit shows an error on the card, not a blank page.
- Missing Clerk keys still render the screens; submit explains that auth is not configured.

## Requirements

- **FR-001**: Dedicated sign-in and sign-up routes.
- **FR-002**: Each screen is a single centered card (not full-bleed form).
- **FR-003**: Visible labels, email autocomplete, password reveal; primary action is full width.
- **FR-004**: Each screen links to the other.
- **FR-005**: Credentials go to Clerk when keys are present; no local password store.

## Success Criteria

- **SC-001**: Unauthenticated visitor can open both screens and move between them.
- **SC-002**: Card stays readable on a phone-width viewport.

## Assumptions

- Identity remains Clerk; Django is not a login API.
- Email verification, if Clerk requires it, stays on the same card.

## Out of Scope

- Finance screens, OAuth button set (Clerk dashboard), org switcher, password-reset as a separate route.
