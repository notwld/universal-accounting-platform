# Universal Accounting Platform Constitution

## Core Principles

### I. Auth Separation (NON-NEGOTIABLE)

Clerk owns credentials, sessions, MFA, SSO, and password lifecycle.
Django owns local identity, tenancy, RBAC, RLS context, audit, and API authorization.
Django MUST NOT expose `/login`, `/logout`, `/refresh`, `/signup`, OTP, or password endpoints.

### II. Speckit Before Code

Feature work follows: specify → clarify (if needed) → plan → tasks → implement.
No multi-file production changes without Speckit artifacts unless the user waives Speckit for that turn.

### III. Ponytail Ultra

Ship the shortest correct solution. Reuse stdlib and installed deps. No speculative abstractions.
Never skip: trust-boundary validation, security controls, auditability, or STRIDE mitigations.

### IV. Tenant Isolation

Never trust `X-Organization-ID` / `X-Location-ID` alone.
Validate membership server-side. Set PostgreSQL RLS context after authorization.
Authorization lives in Django, not in Clerk JWT claims.

### V. Observability & Privacy

Structured JSON logs. Never log JWTs, secrets, raw PII, or webhook signing material.
Hash IPs/user-agents for security events when configured. Prefer ciphertext + HMAC for stored emails.

## Security Requirements

- Verify Clerk JWTs locally (JWKS/cached key); do not call Clerk on every request.
- CORS: exact origin allowlist; credentials only when required; never `*` with credentials.
- SMTP: TLS (STARTTLS 587 or SSL 465); authenticated relay; used for app security mail only (not auth OTP).
- Threat model every auth surface with STRIDE and keep mitigations mapped in `docs/security/STRIDE.md`.
- Rate-limit auth endpoints; idempotency for mutating bootstrap/context switch.

## Stack Constraints

| Layer | Choice |
|---|---|
| IdP | Clerk + custom UI |
| API | Django + DRF `/api/v1/` |
| DB | PostgreSQL (+ RLS) |
| Cache/Broker | Redis |
| Jobs | Celery |
| IDs | UUIDv7 where practical |

## Governance

This constitution supersedes informal practice. Amendments require updating this file and bumping the version.

**Version**: 1.0.0 | **Ratified**: 2026-09-16 | **Last Amended**: 2026-09-16
