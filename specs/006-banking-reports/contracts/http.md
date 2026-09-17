# HTTP: banking

`POST /api/v1/finance/bank-statements` multipart `account_id` + `file` (CSV or XLSX, columns `date,amount,description`)  
`GET /api/v1/finance/bank-lines?account_id=`

`POST /api/v1/finance/bank-lines/{id}/match` `{ customer_payment_id | vendor_payment_id }`  
`POST /api/v1/finance/bank-lines/{id}/categorize` `{ account_id }` Idempotency-Key

`POST /api/v1/finance/bank-reconciliations` `{ account_id, start_on, end_on, opening, closing }`  
`POST /api/v1/finance/bank-reconciliations/{id}/complete`  
`POST /api/v1/finance/bank-reconciliations/{id}/reopen` `{ reason }`

`GET /api/v1/finance/reports/profit-loss?from=&to=`  
`GET /api/v1/finance/reports/balance-sheet?as_of=`

Permission: `finance.payment.record` for import/match/categorize/reconcile; `finance.report.view` for reports.
