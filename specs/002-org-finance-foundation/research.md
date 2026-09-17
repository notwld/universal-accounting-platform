# Research: Organization Finance Foundation

**Date**: 2026-09-17  
**Feature**: [spec.md](./spec.md)

## 1. Frontend

- **Decision**: No frontend, SPA, or empty navigation in this slice.
- **Rationale**: Product owner instruction 2026-09-17. API is the operator surface (spec Story 5).
- **Alternatives considered**: React/Vite shell from the identity plan — deferred.

## 2. App boundary

- **Decision**: New Django app `apps.finance` under `/api/v1/finance/`. Organization create/list lives next to existing tenancy as `/api/v1/organizations/` (not a second tenant model).
- **Rationale**: Product plan repository boundaries. Auth/tenancy stay; finance owns books.
- **Alternatives considered**: Stuffing ledger models into `apps.tenancy` — mixes isolation stubs with accounting. Copying CIA finance — rejected in competitor research.

## 3. Access model

- **Decision**: Nullable `Membership.finance_role` FK to org-scoped `FinanceRole`. Null means no finance access. Location on membership never implies finance. Preset roles seeded at finance setup; custom roles are extra `FinanceRole` rows with a permission list. `membership.roles` JSON stays as today for non-finance tenancy.
- **Rationale**: One grant column, one role table. Generic `member` already grants nothing financial.
- **Alternatives considered**: Parallel tenancy service; encoding finance ACLs only in `roles` JSON — custom roles and audit of permission sets become ad hoc.

## 4. Trusted context and RLS

- **Decision**: Finance writes open `transaction.atomic()`, then call `set_rls_context` inside that transaction before any finance query. Middleware RLS is not sufficient (transaction-local `set_config`). RLS policies on all finance tables: `organization_id = current_setting('app.organization_id')` and deny empty setting. Tests use PostgreSQL and a non-`BYPASSRLS` role. SQLite tests may cover calculation/API shape only; isolation/concurrency gates require Postgres.
- **Rationale**: Spec FR-009/FR-010 and PostgreSQL owner-bypass behavior.
- **Alternatives considered**: Middleware-only RLS — fails when the view starts a new transaction. Superuser test role — cannot prove RLS.

## 5. Idempotency

- **Decision**: Finance-owned uniqueness `(organization_id, operation, key)` on `finance_idempotency`. Do not change `auth_idempotency` unique `(key, user_id)`.
- **Rationale**: Spec requires org+operation+key. Reusing auth records would break or over-constrain login idempotency.
- **Alternatives considered**: Reuse `IdempotencyService` as-is — wrong uniqueness.

## 6. Money and journals

- **Decision**: `Decimal` columns (high precision store, quantize to currency exponent on post). Shared read-only `Currency` seed (ISO code + exponent). This slice posts only in the org base currency. One `post_journal` service; no model-save signals. Imbalance aborts the transaction. Reversal inserts an opposite posted journal linked to the original.
- **Rationale**: CIA auto-balance and journal replacement are explicit anti-patterns. FX documents are a later package.
- **Alternatives considered**: Universal 2 decimal places; deleting/replacing posted lines; private per-module ledgers.

## 7. Periods and sequences

- **Decision**: Period locks are dated ranges per org. Posting is allowed iff no locked range contains the journal date. Sequences allocate `select_for_update` on the series row. Numbers never reused.
- **Rationale**: Avoid generating a full fiscal calendar before anyone closes a month.
- **Alternatives considered**: Pre-create 12 periods at setup — extra rows, no user yet.

## 8. Organization lifecycle

- **Decision**: `POST /api/v1/organizations` creates an Organization and an Owner membership for the caller (no location required). Finance setup is a separate call. Adding finance users assigns a `FinanceRole` to an existing local `AuthUser`. Email/Clerk invitations wait for a later UI package.
- **Rationale**: Bootstrap already returns `onboarding.next_step = create_organization`. Spec FR-011 allows add-or-invite; add is enough without a mail UI.
- **Alternatives considered**: Auto-create books at org create — would pick a currency/country without a user choice.

## 9. Step-up for privileged access changes

- **Decision**: Role assignment and period reopen require a Clerk JWT issued (or `auth_time`) within a short window (5 minutes). No new auth endpoints.
- **Rationale**: Constitution: Clerk owns credentials; Django must not add `/login`.
- **Alternatives considered**: Django OTP — forbidden.

## 10. Error envelope

- **Decision**: Reuse `envelope_success` / `envelope_error` / catalogue pattern. Add finance codes (`period_closed`, `journal_imbalanced`, `idempotency_conflict`, `cross_organization`, `stale_version`, `step_up_required`, `control_account_restricted`) without a second error format.
- **Rationale**: One API envelope already exists.
- **Alternatives considered**: Finance-specific envelope — redundant.
