# Verification — 002-org-finance-foundation

**Date**: 2026-09-17  
**Frontend**: not built (product owner).

## Commands

From `backend/`:

```text
..\.venv\Scripts\python -m pytest apps\finance\tests apps\authentication\tests -q
→ 17 passed, 1 skipped (Postgres isolation)  exit 0

..\.venv\Scripts\python manage.py check
→ System check identified no issues (0 silenced)  exit 0

..\.venv\Scripts\python manage.py makemigrations --check --dry-run
→ No changes detected  exit 0
```

## Coverage vs spec

| Story | Evidence |
|---|---|
| US1 two books | `test_two_organizations_isolated` |
| US2 grants / location / member | `test_access_and_posting`, `test_member_without_grant_denied`, `test_location_membership_without_grant` |
| US3 post / imbalance / reverse / idempotency | `test_access_and_posting` |
| US4 period lock / TB / GL | `test_access_and_posting` |
| US5 API errors | same; no frontend files added |

## Remaining

- Postgres RLS/concurrency gate needs `DATABASE_URL` to PostgreSQL and a non-`BYPASSRLS` app role (`test_postgres_isolation.py` skipped on SQLite).
- Email invitations, FX journals, documents, banking, and UI are later packages.
