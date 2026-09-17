# HTTP contract: sales and collection

Same auth, org header, envelope, decimal strings, Idempotency-Key on money actions.

New permissions: `finance.contact.maintain`, `finance.item.maintain`, `finance.invoice.create`, `finance.document.post`, `finance.payment.record`.  
Sales Clerk: contact, item, invoice.create, journal.read, report.view. Not document.post or payment.record.

## Master data

`GET/POST /api/v1/finance/contacts`  
`PATCH /api/v1/finance/contacts/{id}`

`GET/POST /api/v1/finance/items`  
`PATCH /api/v1/finance/items/{id}`

`GET/POST /api/v1/finance/tax-rates`

`GET/POST /api/v1/finance/payment-terms`

`GET/POST /api/v1/finance/exchange-rates` body `{ currency, rate, as_of }`

`PUT /api/v1/finance/settings` may include `ar_account_id`, `advance_account_id`, `fx_gain_account_id`, `fx_loss_account_id`.

## Quotes

`GET/POST /api/v1/finance/quotes`  
`PATCH /api/v1/finance/quotes/{id}`  
`POST /api/v1/finance/quotes/{id}/convert` → invoice draft

## Invoices

`GET/POST /api/v1/finance/invoices`  
`PATCH` draft only, `stale_version`  
`GET /api/v1/finance/invoices/{id}/preview` proposed journal, no write  
`POST /api/v1/finance/invoices/{id}/post` Idempotency-Key, `finance.document.post`

## Credits / payments / refunds

`POST /api/v1/finance/credit-notes` + `.../{id}/post`  
`POST /api/v1/finance/payments` + `.../{id}/post` body includes `allocations: [{ invoice_id, amount }]`  
`POST /api/v1/finance/refunds` body `{ payment_id|credit_note_id, amount, bank_account_id, entry_date }`

## Reports

`GET /api/v1/finance/reports/ar-aging?as_of=`

## Extra error codes

| code | HTTP |
|---|---|
| over_allocation | 409 |
| missing_rate | 422 |
| quote_not_convertible | 422 |
