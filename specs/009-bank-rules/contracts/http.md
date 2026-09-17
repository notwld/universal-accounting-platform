# HTTP: bank rules

`GET /api/v1/finance/bank-rules`  
`POST /api/v1/finance/bank-rules` `{ pattern, account_id, direction?, priority? }`  
`PATCH /api/v1/finance/bank-rules/{id}` `{ active?, priority?, pattern?, account_id?, direction? }`  
`POST /api/v1/finance/bank-rules/apply` `{ account_id? }` — optional bank GL filter

Permission: `finance.payment.record`.

Apply response: `{ categorized: [{ id, journal_id }] }` (empty on replay).
