# HTTP

Reminder run unchanged; response `created[].emailed` bool.

Bank rule create/patch: `match_kind`, `amount_min`, `amount_max`. Import response includes `categorized`.

`POST /bank-statements` file may be csv, xlsx, xls, ofx, qif.

`GET/POST /bank-feeds` `{ account_id, url }`  
`POST /bank-feeds/{id}/fetch`

`GET/POST /saved-filters` `{ name, resource, params }`  
`GET /invoices?saved_filter_id=` (also bills, bank-lines)

`GET /exceptions?status=open`  
`POST /exceptions/{id}/resolve` `{ reason }`

Settings: `approval_threshold`, `approval_levels`.

Permissions: payment.record for feeds; journal.read for exceptions list; settings.configure for filters write; document.approve unchanged.
