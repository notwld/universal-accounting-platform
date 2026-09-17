# HTTP

`GET/POST /tags` `{ name }`

Account create/patch: `cashflow_kind`.
Journal lines: `tag_id`.

`GET /reports/trial-balance|general-ledger|profit-loss` `tag_id`
`GET /reports/profit-loss` `compare_from` `compare_to`
`GET /reports/balance-sheet` `compare_as_of`
`GET /reports/cash-flow` `from` `to`

Permission: `finance.settings.configure` to create tags; `finance.report.view` to read reports; `finance.account.maintain` to set `cashflow_kind`.
