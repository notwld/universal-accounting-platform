# HTTP: PO, attachments, payment runs

`GET/POST /api/v1/finance/purchase-orders` `finance.bill.create`  
`POST /api/v1/finance/purchase-orders/{id}/convert` → bill draft

`POST /api/v1/finance/attachments` multipart `object_type`, `object_id`, `file`  
`GET /api/v1/finance/attachments?object_type=&object_id=`  
`GET /api/v1/finance/attachments/{id}/download`

`POST /api/v1/finance/payment-runs` Idempotency-Key, `finance.payment.record`  
body `{ bank_account_id, entry_date, currency, items: [{ bill_id, amount }] }`

`GET /api/v1/finance/contacts/{id}/vendor-statement?from=&to=` `finance.report.view`

Errors: reuse `quote_not_convertible` for converted PO, `over_allocation`, `validation_error` for file limits, `cross_organization`.
