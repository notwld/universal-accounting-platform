# Universal Accounting Platform — Auth & Identity Module

Implements **Enterprise Authentication & Identity Module v2.0** (Clerk + Django DRF), Speckit artifacts, SMTP security mail, CORS, STRIDE, ReDoc.

## Quick start

```bash
docker compose up -d   # optional: Postgres, Redis, Mailpit
cp .env.example .env
.\.venv\Scripts\pip install -r backend\requirements.txt
cd backend
..\.venv\Scripts\python manage.py migrate
..\.venv\Scripts\python manage.py runserver
# optional worker + beat
..\.venv\Scripts\celery -A config worker -l info -Q default,webhooks,security,maintenance
..\.venv\Scripts\celery -A config beat -l info
```

| URL | Purpose |
|---|---|
| `/api/redoc/` | ReDoc |
| `/api/docs/` | Swagger UI |
| `/api/schema/` | OpenAPI |
| `/health/` | Liveness |
| `/ready/` | Readiness |
| `/metrics/` | Prometheus text |

## Auth APIs (no login/logout/refresh)

- `POST /api/v1/auth/bootstrap`
- `GET /api/v1/auth/me`
- `GET /api/v1/auth/context`
- `POST /api/v1/auth/context/switch`
- `GET /api/v1/auth/sessions`
- `GET /api/v1/auth/security-events`
- `POST /api/v1/webhooks/clerk`

## MD coverage notes

Closed from audit ([Audit MD vs backend](c974014b-e414-4b60-91a1-7bc275a18015)):

- Error catalogue (§45) + auth response headers (§46)
- JWT `nbf`/`sid`, distinct expired/issuer/azp codes
- Trusted context before RLS; authz-versioned cache + stampede
- Session / provider-event / security-event schema parity
- Cursor pagination, sessions rate limit, health/ready/metrics
- Celery beat reconciliation + cleanup tasks
- Deletion anonymization, access logging, Sentry/OTEL hooks
- RLS SQL at `backend/apps/authentication/sql/rls.sql` (Postgres)
- Expanded §85 security tests

Still intentionally light / ops-time:

- Full Grafana dashboards & load suite (§76–78, §86)
- Separate long-term audit store beyond security events (§60)
- Production non-`BYPASSRLS` DB role provisioning (SQL provided)

Threat model: `docs/security/STRIDE.md`

## Tests

```bash
cd backend
..\.venv\Scripts\python -m pytest apps\authentication\tests -q
```
