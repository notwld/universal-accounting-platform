# Feature: Redirect to login + forgot password

**Created**: 2026-09-18

**Input**: Don't show home Sign in/Create account; redirect to login; add forgot password.

## Requirements

- **FR-001**: Unsigned visitors to `/` go to `/sign-in`.
- **FR-002**: Sign-in offers forgot password (email code → new password) via Clerk.

## Success Criteria

- **SC-001**: Opening `/` while signed out lands on `/sign-in`.
- **SC-002**: User can request a reset code and set a new password on the same card flow.
