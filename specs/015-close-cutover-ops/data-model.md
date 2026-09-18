# Data model

## FinanceSettings (existing)

- `cutover_mode` blank | `openings` | `history`
- `cutover_stage` last completed stage name

## FinanceAdjustment

org, kind accrual|deferral, debit_account, credit_account, amount, entry_date, reverse_on, memo, journal, reverse_journal

## FinanceFxReval

org, as_of unique, journal nullable, reverse_journal nullable, amount

## FinanceWebhookEndpoint

org, url, secret, events JSON, enabled

## FinanceWebhookDelivery

org, endpoint, event_id unique-per-org, event_type, payload, status pending|delivered|dead, attempts, next_attempt, last_error
