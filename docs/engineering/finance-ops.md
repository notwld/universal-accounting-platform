# Finance ops notes (B13)

- **Backup**: PostgreSQL `pg_dump` + media volume. Restore is `pg_restore` then `manage.py migrate --check`.
- **Rollback**: forward-only migrations; revert by restoring the backup taken before deploy.
- **Posting SLO**: p95 journal post under 2s on a 10k-line org is the local target; alert on `finance_post_total` drop or 5xx spike.
- **Logs**: `apps.authentication.access` includes request_id, org_id, path, status, duration_ms. Do not log JWT or request bodies.
- **Metrics**: `/metrics` counters `finance_http_requests_total`, `finance_post_total`.
