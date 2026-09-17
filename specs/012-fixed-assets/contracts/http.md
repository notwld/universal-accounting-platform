# HTTP

`GET/POST /assets` capitalize `{ name, cost, residual, life_months, in_service_date, cost_account_id, accum_account_id, expense_account_id, credit_account_id }` Idempotency-Key

`POST /assets/depreciate` `{ through_date, asset_id? }` Idempotency-Key

`POST /assets/{id}/write-down` `{ amount, entry_date }` Idempotency-Key

`POST /assets/{id}/dispose` `{ entry_date, proceeds, proceeds_account_id?, gain_loss_account_id }` Idempotency-Key

`GET /reports/asset-register`

Permission: `finance.document.post` to mutate; `finance.report.view` for the register.
