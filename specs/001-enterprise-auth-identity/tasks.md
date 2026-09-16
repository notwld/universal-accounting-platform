# Tasks: Enterprise Auth & Identity

**Input**: plan.md, spec.md

## Phase 0 — Scaffold
- [x] T001 Create `backend/` Django project + apps `authentication`, `tenancy`
- [x] T002 Docker Compose Postgres/Redis + `.env.example` (SMTP/CORS/Clerk)
- [x] T003 [P] Write `docs/security/STRIDE.md`

## Phase 1 — US1 Bootstrap
- [x] T004 Models: AuthUser, SessionProjection, IdempotencyKey, SecurityEvent, ProviderEvent
- [x] T005 Tenancy stubs: Organization, Location, Membership
- [x] T006 Clerk JWT authenticator + request-id middleware
- [x] T007 Bootstrap service + `POST /api/v1/auth/bootstrap`
- [x] T008 Cache service (Redis TTL + jitter + lock)

## Phase 2 — US2 Context
- [x] T009 me / context / context/switch APIs + serializers
- [x] T010 Context validation never trusts headers alone

## Phase 3 — US3 Sessions & events
- [x] T011 sessions list + security-events list + pagination

## Phase 4 — US4 Webhooks
- [x] T012 Clerk webhook verify + enqueue Celery handlers

## Phase 5 — US6 SMTP/CORS/STRIDE controls
- [x] T013 CORS settings + CSRF trusted origins
- [x] T014 SMTP + Celery `send_security_email` task
- [x] T015 Rate limiting + standard error envelope

## Phase 6 — US5 Frontend
- [x] T016 Vite React + Clerk custom login/signup → bootstrap

## Phase 7 — Tests
- [x] T017 pytest: JWT accept/reject, bootstrap JIT, context switch deny, webhook idempotency, CORS
