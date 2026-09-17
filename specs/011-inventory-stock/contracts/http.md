# HTTP

Settings: `inventory_account_id`, `cogs_account_id`.
Item create: `tracked`, `kind`.

`GET/POST /warehouses` `{ name }`
`GET /stock/balances`
`POST /stock/adjust` `{ warehouse_id, item_id, quantity, unit_cost? }` Idempotency-Key
`POST /stock/transfer` `{ from_warehouse_id, to_warehouse_id, item_id, quantity }`
`GET /reports/inventory-valuation`

Permission: `finance.item.maintain` for warehouse/adjust/transfer; `finance.report.view` for valuation; document.post still posts bills/invoices.
