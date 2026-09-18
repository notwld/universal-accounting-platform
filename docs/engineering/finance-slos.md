# Finance SLOs

| Signal | Objective | Alert when |
|---|---|---|
| Posting | 99% of post commands succeed in 5s | `finance_post_total` error ratio > 1% for 10m |
| Reports | Trial balance / P&L p95 < 5s for a midsize ledger | report duration > 10s for 5m |
| Imports / cutover | Dry-run and apply complete without silent row loss | import error count > 0 for a job |
| Webhooks | Deliveries leave pending within 15m or go dead | pending older than 15m or dead spike |
| Jobs | Recurring/reminder/deliver lag < 15m | last success older than 15m |

Wire these to log metrics (`request_id`, `organization_id`, duration, result). Production alert rules: `deploy/alerts/finance-slos.yml`.
