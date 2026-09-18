# Verification — 015 close / cutover / ops

Date: 2026-09-18

## Ran

- `pytest apps/finance/tests` — 25 passed, 3 skipped (Postgres RLS unless `DATABASE_URL` is PostgreSQL)

## Delivered

Accruals/deferrals, unrealized FX reval, PDF export, golden TB fixture, ordered cutover with openings XOR history, HMAC webhook outbox/retry/DLQ, Postgres two-role CI workflow, query-count load assertion, SLO alert YAML, backup/restore runbook.

## Not claimed

Column-mapping CSV import jobs, live PITR restore, concurrent idempotency/refund races (advisory-lock two-connection only), jurisdiction tax packs, screens.
