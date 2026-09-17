# Implementation Plan: Organization Finance Foundation and Immutable Ledger

**Branch**: `002-org-finance-foundation` | **Date**: 2026-09-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-org-finance-foundation/spec.md`

## Summary

Backend-only finance kernel: create/select organizations, explicit finance roles, trusted RLS, per-org settings/chart/sequences/period locks, and an immutable balanced journal with reversals, opening balances, trial balance, and GL. No screens. Reuse Clerk identity, Organization, Membership, request envelope, and `set_rls_context`. One posting function; no signals; no CIA copy; no UAE defaults.

## Technical Context

**Language/Version**: Python 3.12+

**Primary Dependencies**: Django 5.x, DRF, existing Clerk JWT auth, Celery/Redis already installed (jobs only if a finance write needs after-commit work; none required for manual journals)

**Storage**: PostgreSQL required for RLS/concurrency gates; SQLite remains the default local `DATABASE_URL` and must not be treated as isolation proof

**Testing**: pytest-django; Postgres tests marked and using a non-bypass app role

**Target Platform**: Existing Django ASGI/WSGI API

**Project Type**: Backend API feature in the existing monorepo (`backend/` only)

**Performance Goals**: Single-journal post p95 ≤ 1s excluding network; list/detail p95 ≤ 500ms on the reference dataset (design target, not an SLA)

**Constraints**: No frontend. No Entity/Business Center. No country tax pack. Decimal money only. Posted rows immutable. RLS context inside the write transaction. Ponytail ultra: no factories, no second ledger, no unused nav.

**Scale/Scope**: Phase 1 kernel (FIN-01/02 + foundation FIN-06/10/11). Not general availability of the finance product.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| I. Auth Separation | PASS | No credential endpoints. Step-up uses Clerk JWT freshness. |
| II. Speckit Before Code | PASS | Spec + this plan before implementation. |
| III. Ponytail Ultra | PASS | One app, one posting service, reuse envelope/RLS helper/IDs. Frontend skipped. Email invite skipped. |
| IV. Tenant Isolation | PASS | Membership + finance_role; RLS set inside the transaction; never trust headers alone. |
| V. Observability & Privacy | PASS | Reuse request IDs; audit events without PII dumps; no JWT/secret logging. |

Post-design re-check: still PASS. Contracts stay under `/api/v1/`. Finance idempotency is a separate table so auth uniqueness is untouched.

## Project Structure

### Documentation (this feature)

```text
specs/002-org-finance-foundation/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── finance-http.md
└── tasks.md                 # /speckit-tasks, not this command
```

### Source Code (repository root)

```text
backend/
  apps/tenancy/              # Organization/Membership; add finance_role FK + org create API
  apps/authentication/       # Reuse JWT, envelope, set_rls_context; narrow step-up helper
  apps/finance/
    models/                  # settings, currency, account, sequence, period, journal, audit, idempotency, role
    services/                # setup, permissions, posting, reversal, sequences, reports
    api/                     # DRF views under /api/v1/finance/
    selectors/               # trial balance, GL
    migrations/              # schema + RLS SQL
    tests/                   # accounting + Postgres isolation
  config/settings.py         # register app
  config/urls.py             # /api/v1/finance/, /api/v1/organizations/
```

**Structure Decision**: Modular monolith as in the product plan. No `frontend/` work. Split models by file only where the product plan already named groups; keep services few (`posting.py`, `access.py`, `setup.py`, `reports.py`).

## Complexity Tracking

> No constitution violations.
