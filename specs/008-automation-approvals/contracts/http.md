# HTTP

Recurring create accepts `frequency`, `weekday`, `month_of_year`, `auto_post`.

`POST /invoices/{id}/submit|approve|reject` (reject `{ reason }`) same for bills.

Settings PUT: `require_document_approval`, `allow_self_approve`.

`POST /reminder-rules` `{ document_kind, days_before_due }`
`GET /reminders`
`POST /reminders/run` `{ as_of? }`
