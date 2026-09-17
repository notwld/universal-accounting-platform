# HTTP contract: finance foundation

Auth: existing Clerk Bearer JWT. Organization: `X-Organization-ID` validated by membership (existing middleware). Envelope: existing `{ data, meta }` / `{ error: { code, message, field_errors, request_id, timestamp } }`.

Money in JSON: decimal strings. Idempotency: header `Idempotency-Key` on post/reverse.

All finance routes require a trusted organization context except organization create/list.

## Organizations (tenancy)

### `POST /api/v1/organizations`

Create organization + Owner membership for the caller. No location. Does not complete finance setup.

Body: `{ "name": string }`  
201: `{ id, name, status }`

### `GET /api/v1/organizations`

List organizations the caller has active membership in.  
200: `{ items: [{ id, name, status, finance_setup_complete, finance_role_slug|null }] }`

## Finance settings

### `GET /api/v1/finance/settings`

Requires `finance.settings.configure` or `finance.report.view`.

### `PUT /api/v1/finance/settings`

Requires `finance.settings.configure`.  
Body: `{ country_code, base_currency, fiscal_year_start_month, timezone, locale, tax_registration_applies }`  
Seeds preset `FinanceRole` rows and default journal sequence if missing.  
Error `base_currency_locked` if posted journals exist and currency changes.

## Access

### `GET /api/v1/finance/roles`

List org roles (presets + custom). Requires `finance.access.manage` or Owner.

### `POST /api/v1/finance/roles`

Create custom role. Body: `{ name, permissions[] }`. Requires `finance.access.manage`. Step-up: JWT `iat`/`auth_time` within 5 minutes or `step_up_required`.

### `GET /api/v1/finance/grants`

List memberships with finance_role. Requires `finance.access.manage`.

### `PUT /api/v1/finance/grants/{user_id}`

Assign or clear `finance_role` for an existing local user who already has a membership (create membership as active if missing and caller is Owner/Admin). Body: `{ role_slug }` or `{ role_slug: null }`. Step-up required. Caller cannot uniquely grant themselves `owner` if they are not already owner. Audit `access.grant`.

## Chart

### `GET /api/v1/finance/accounts`

### `POST /api/v1/finance/accounts`

Body: `{ code, name, classification, is_control, control_kind }`  
Requires `finance.account.maintain`.

### `PATCH /api/v1/finance/accounts/{id}`

Honors `version`. Error `stale_version`. Cannot change organization. Posted history is not rewritten (name/code changes affect future presentation only; journals snapshot account id).

## Journals

### `GET /api/v1/finance/journals`

Query: `from`, `to`, `status`. Requires `finance.journal.read` or `finance.report.view`.

### `POST /api/v1/finance/journals`

Create draft. Requires `finance.journal.create`.  
Body: `{ entry_date, memo, source_type, lines: [{ account_id, description, debit, credit }], version? }`  
Recalculate totals server-side.

### `PATCH /api/v1/finance/journals/{id}`

Draft only. `stale_version` if mismatch.

### `POST /api/v1/finance/journals/{id}/post`

Requires `finance.journal.post`. Idempotency-Key required.  
Locks sequence + period + journal; rechecks version; quantizes; rejects imbalance (`journal_imbalanced`); rejects closed period (`period_closed`); rejects foreign org accounts (`cross_organization`); control accounts unless `source_type=opening` (`control_account_restricted`).  
201/200: posted journal with number.

### `POST /api/v1/finance/journals/{id}/reverse`

Requires `finance.journal.reverse`. Body: `{ reason, entry_date? }`. Idempotency-Key required. Original posted only; not already reversed. New posted opposite journal. Error `already_reversed`.

## Periods

### `GET /api/v1/finance/periods`

### `POST /api/v1/finance/periods/{id}/lock`

Requires `finance.period.lock`. Creates or locks range. Body on create: `{ start_on, end_on }`.

### `POST /api/v1/finance/periods/{id}/reopen`

Requires `finance.period.reopen`. Body: `{ reason }`. Step-up required. Audit.

## Reports

### `GET /api/v1/finance/reports/trial-balance?from&to`

Requires `finance.report.view`. Published entries only.

### `GET /api/v1/finance/reports/general-ledger?from&to&account_id`

Requires `finance.report.view`. Drill-through: each line includes `journal_id`.

## Error codes (finance)

| code | HTTP |
|---|---|
| permission_denied | 403 |
| organization_access_denied | 403 |
| step_up_required | 403 |
| period_closed | 409 |
| journal_imbalanced | 422 |
| idempotency_conflict | 409 |
| cross_organization | 404 |
| stale_version | 409 |
| base_currency_locked | 409 |
| control_account_restricted | 422 |
| already_reversed | 409 |
| account_inactive | 422 |
| missing_context | 403 |
