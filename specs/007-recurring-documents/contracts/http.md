# HTTP: recurring

`POST /api/v1/finance/recurring` `{ kind, contact_id, currency, start_on, day_of_month, lines, end_on?, bank_account_id? }`  
`GET /api/v1/finance/recurring`  
`POST /api/v1/finance/recurring/{id}/pause`  
`POST /api/v1/finance/recurring/{id}/resume`  
`POST /api/v1/finance/recurring/run` `{ as_of? }`

Permissions: `finance.invoice.create` (invoice), `finance.bill.create` (bill), `finance.payment.record` (expense). Run processes only kinds the caller can create.
