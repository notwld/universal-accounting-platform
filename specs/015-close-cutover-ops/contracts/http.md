# HTTP

- `POST /api/v1/finance/adjustments` Idempotency-Key; `{kind, debit_account_id, credit_account_id, amount, entry_date, reverse_on, memo}`
- `POST /api/v1/finance/adjustments/reverse` `{as_of}`
- `POST /api/v1/finance/fx/revalue` Idempotency-Key; `{as_of}`
- `POST /api/v1/finance/cutover` `{mode, stage, dry_run, rows}`
- `GET|POST /api/v1/finance/webhooks` create endpoint
- `POST /api/v1/finance/webhooks/deliver`
- `GET /api/v1/finance/ops/metrics`
- Reports: `export=pdf` in addition to csv|xlsx
