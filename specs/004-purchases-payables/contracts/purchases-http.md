# HTTP contract: purchases and payables

Same auth, org header, envelope, decimal strings, Idempotency-Key on money actions.

New permission: `finance.bill.create`.  
Reuse `finance.document.post`, `finance.payment.record`, `finance.contact.maintain`, `finance.item.maintain`.

Purchasing Clerk: contact, item, bill.create, journal.read, report.view. Not document.post or payment.record.  
Sales Clerk: unchanged; no bill.create.

## Master data

`POST /api/v1/finance/contacts` may include `is_vendor`, `is_customer`.  
`POST /api/v1/finance/items` may include `expense_account_id`.

`PUT /api/v1/finance/settings` may include `ap_account_id`, `vendor_advance_account_id`.

## Bills

`GET/POST /api/v1/finance/bills`  
`GET /api/v1/finance/bills/{id}/preview` proposed journal, no write  
`POST /api/v1/finance/bills/{id}/post` Idempotency-Key, `finance.document.post`

## Credits / payments / refunds / expenses

`POST /api/v1/finance/vendor-credits` body includes optional `bill_id` and `lines`; posts immediately (`finance.document.post`)  
`POST /api/v1/finance/vendor-payments` body includes `allocations: [{ bill_id, amount }]` (`finance.payment.record`)  
`POST /api/v1/finance/vendor-refunds` body `{ payment_id, amount, bank_account_id, entry_date }`  
`POST /api/v1/finance/expenses` paid expense, posts immediately (`finance.payment.record`)

## Reports

`GET /api/v1/finance/reports/ap-aging?as_of=`

## Extra error codes

Reuse `over_allocation`, `missing_rate`. No new catalogue codes required.
