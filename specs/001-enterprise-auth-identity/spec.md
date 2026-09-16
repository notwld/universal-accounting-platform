# Feature Specification: Enterprise Auth & Identity Module

**Feature Branch**: `001-enterprise-auth-identity`  
**Created**: 2026-09-16  
**Status**: Active  
**Input**: Implement UAP Auth & Identity Module v2.0 MD; fill gaps; SMTP; CORS; STRIDE.

## User Scenarios & Testing

### User Story 1 — Bootstrap after Clerk sign-in (P1)

User completes custom Clerk UI login; frontend calls `POST /api/v1/auth/bootstrap` with Bearer JWT; Django JIT-provisions local user, projects session, returns context + authz version.

**Independent Test**: Mock valid JWT → bootstrap → local user + session row + 200 envelope.

**Acceptance Scenarios**:
1. **Given** valid Clerk JWT and unknown local user, **When** bootstrap, **Then** JIT user created and 200 with user/context.
2. **Given** suspended local user, **When** bootstrap, **Then** 403.
3. **Given** invalid/expired JWT, **When** bootstrap, **Then** 401.

### User Story 2 — Me / context / switch (P1)

Authenticated user reads identity and tenant context; switches org/location only when membership allows.

**Independent Test**: Seed memberships; call me/context/switch with header vs body IDs.

**Acceptance Scenarios**:
1. **Given** membership in org A, **When** switch to org B without membership, **Then** 403.
2. **Given** valid membership, **When** switch, **Then** 200 and authorization_version present.

### User Story 3 — Sessions & security events (P2)

User lists session projections and own security events (hashed IP/UA).

### User Story 4 — Clerk webhooks (P2)

Signed Clerk webhooks enqueue Celery processing; idempotent on provider+event_id; login path never depends on webhook success.

### User Story 5 — Custom Clerk frontend (P1)

Custom `/account/login` (and sign-up/forgot) UI using Clerk under the hood; on success → bootstrap → app shell.

### User Story 6 — SMTP security mail + CORS + STRIDE (P1)

Transactional SMTP for security notifications; hardened CORS; STRIDE threat model + control mapping documented and enforced in code.

## Edge Cases

- Redis down: degrade cache; auth still works via DB (503 only if DB down).
- Clerk API down: JWT verify still works offline via JWKS cache.
- Webhook signature invalid → 401; duplicate event → ack without reprocess.
- Context headers spoofed → ignored unless membership proves access.
- SMTP misconfigured → log + queue failure; do not block bootstrap.

## Requirements

### Functional
- FR-001: Clerk JWT verification (issuer, azp/aud, skew, signature).
- FR-002: Auth APIs only: bootstrap, me, context, context/switch, sessions, security-events, clerk webhook.
- FR-003: Models: user, session_projection, security_event, provider_event, idempotency; stub org/location/membership.
- FR-004: Redis auth cache with TTL jitter + stampede lock.
- FR-005: Celery queues for webhooks, security mail, reconciliation.
- FR-006: Idempotency-Key on bootstrap and context switch.
- FR-007: Standard success/error envelopes + request ID.
- FR-008: Custom frontend Clerk flows (no prebuilt Clerk components required).
- FR-009: SMTP settings + Celery email for security events.
- FR-010: CORS allowlist + credentials policy + CSRF trusted origins.
- FR-011: STRIDE document + mitigations wired (rate limits, audit, RLS hooks, no client-trusted RBAC).

### Gaps closed beyond source MD
- GAP-1: Minimal Organization / Location / Membership models (MD assumed them).
- GAP-2: SMTP for app security notifications (Clerk still owns auth email).
- GAP-3: Explicit CORS middleware config (MD only listed env vars).
- GAP-4: STRIDE threat model (absent from MD).
- GAP-5: Docker Compose for Postgres/Redis local run.
- GAP-6: Field encryption helpers for email ciphertext/HMAC.

## Success Criteria

- SC-001: All catalogue APIs implemented and tested with mocked JWT.
- SC-002: No Django credential endpoints exist.
- SC-003: CORS rejects non-allowlisted origins.
- SC-004: STRIDE.md maps each threat to a control present in code.
- SC-005: SMTP task sends via TLS-capable backend when configured.
