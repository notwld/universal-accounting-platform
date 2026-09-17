# Quickstart validation — finance foundation

No frontend. PostgreSQL is required for isolation/concurrency; SQLite is not evidence for those gates.

## Prerequisites

- Repo venv, `backend/` on `PYTHONPATH` as today
- Auth tests still pass: `Set-Location backend; ..\.venv\Scripts\python -m pytest apps\authentication\tests -q`
- `DATABASE_URL` pointing at Postgres for marked tests (app role without `BYPASSRLS`)

## Setup

1. Apply migrations (includes finance RLS policies).
2. Seed currencies if not in migration data.
3. Authenticate with a Clerk JWT as in existing auth tests.

## Scenario A — two books, one user

1. `POST /api/v1/organizations` name A; `PUT /api/v1/finance/settings` USD, January, country US.
2. Repeat for B with EUR, fiscal start July, country DE (switch `X-Organization-ID`).
3. Create one income and one asset account in each.
4. GET settings/accounts for A while selected into B → A rows absent (`cross_organization` / empty).

Expected: independent charts and currencies; A USD remains after B setup.

## Scenario B — post, fail imbalance, reverse, replay

1. Draft journal Dr 100 Cr 100; `POST .../post` with Idempotency-Key `k1`.
2. Trial balance and GL show 100 / 100.
3. Unbalanced draft post → `journal_imbalanced`, no new journal row.
4. `POST .../reverse` with reason; original unchanged; TB nets to zero.
5. Replay `k1` with same body → same journal id. Replay `k1` with different body → `idempotency_conflict`.
6. PATCH posted journal → rejected.

## Scenario C — permissions and location

1. User Viewer on B cannot post.
2. Membership with location set and `finance_role` null cannot GET journals.
3. Generic `member` without finance_role → 403 on finance routes.

## Scenario D — period lock race (Postgres only)

1. Lock period covering the journal date.
2. Concurrent post dated in that period vs lock: outcome is either posted-then-open or rejected-and-locked, never posted into a locked range.
3. Reopen with reason + fresh JWT; post succeeds.

## Commands (record actual exit codes at implement time)

```powershell
Set-Location backend
..\.venv\Scripts\python -m pytest apps\authentication\tests -q
..\.venv\Scripts\python -m pytest apps\finance\tests -q
..\.venv\Scripts\python manage.py check
..\.venv\Scripts\python manage.py makemigrations --check --dry-run
```

Postgres isolation module (name may match tasks.md): run only when `DATABASE_URL` is Postgres.

## Out of scope here

Browser flows, invoices, FX journals, bank import, country packs.
