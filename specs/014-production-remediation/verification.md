# Verification — 014 production remediation

Date: 2026-09-18

## Ran

- `python manage.py check` — no issues
- `python manage.py makemigrations --check --dry-run` — no changes
- `pytest backend` — pass; PostgreSQL RLS/role tests skipped unless `DATABASE_URL` is PostgreSQL

## P1 / named P2

| Package | Result |
|---|---|
| B0 | `uap_app` role in `deploy/postgres/init.sql`; role/RLS tests skip off Postgres |
| B1 | `org_get` on request FKs; credit/payment create-and-post in one `finance_tx` |
| B2 | Credit lines carry source line, qty, `price_only`; stock reverses credited qty only |
| B3 | Quantity scale 8 independent of currency exponent |
| B4 | Idempotency insert uses an inner savepoint; command key stored before insert |
| B5 | Refunds lock the payment and recompute capacity inside the transaction |
| B6 | In-file repeats persist; cross-file fingerprint matches `review`; identical file hash replays |
| B7 | Complete rejects unresolved imported/review lines; records book balance |
| B8 | Trial balance returns opening, period, and closing debit/credit |
| B10 | ISO 4217 catalogue seeded (>100 current codes) |

## Not claimed

B9 year-close, B11 imports, B12/B13 security/ops, live two-connection Postgres CI as `uap_app`, country packs, screens, SMS, live bank clients.
