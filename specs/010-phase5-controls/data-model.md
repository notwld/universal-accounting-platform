# Data Model

## BankRule (existing)

Add: `match_kind` contains|regex (default contains); `amount_min`, `amount_max` nullable decimals.

## BankFeed

organization, account, url, active, last_fetched_at, last_error. Table `finance_bank_feed`.

## SavedFilter

organization, name, resource (invoice|bill|bank_line), params JSON. Unique (org, resource, name). Table `finance_saved_filter`.

## FinanceException

organization, kind, object_type, object_id, reason, status open|resolved. Table `finance_exception`.

## ApprovalAction

organization, object_type, object_id, actor_user_id. Unique (object_type, object_id, actor_user_id). Table `finance_approval_action`.

## FinanceSettings

`approval_threshold` decimal default 0; `approval_levels` smallint default 1.

## Reminder

`emailed_at` nullable datetime.

RLS ENABLE without FORCE on new tables.
