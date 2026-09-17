# Data Model: Organization Finance Foundation

## Existing (reuse)

- **Organization**: `tenancy_organization`. One set of books.
- **Membership**: `tenancy_membership`. Unchanged unique `(user_id, organization)`. Finance access is a separate `FinanceGrant`, not a FK on membership.
- **Location**: unchanged; never a books owner. Location-only membership + no `FinanceGrant` ⇒ no finance.

## New entities

### Currency (shared reference)

| Field | Rules |
|---|---|
| code | ISO 4217, PK, 3 chars |
| exponent | 0–3 typical, integer minor units |
| name | display |

Read-only to tenants. Seed ISO list in migration/data. No per-org currency rows.

### FinanceRole / FinanceGrant

Explicit organization-level grant. `FinanceGrant(organization, user_id, role)` unique per user+org. Null/absent grant means no finance access. Location on `Membership` never implies a grant. Preset roles seeded at organization create.

| Field | Rules |
|---|---|
| id | UUIDv7 |
| organization | FK, required |
| slug | unique per org (`owner`, `finance_admin`, `accountant`, `sales_clerk`, `purchasing_clerk`, `approver`, `viewer`, or custom) |
| name | display |
| permissions | JSON list of action strings |
| is_preset | preset rows not deletable |

Preset permission map (code constants; seeded rows copy them):

| Slug | Permissions |
|---|---|
| owner | all finance actions including `finance.access.manage` |
| finance_admin | settings, chart, access.manage, report.view; not period.reopen unless also granted |
| accountant | journal.create, journal.post, journal.reverse, period.lock, period.reopen, report.view, chart.read |
| sales_clerk | none of journal post/reverse/period in this slice (reserved for later documents) |
| purchasing_clerk | same as sales_clerk for this slice |
| approver | report.view only in this slice |
| viewer | report.view, chart.read, journal.read |

Actions: `finance.access.manage`, `finance.settings.configure`, `finance.account.maintain`, `finance.journal.create`, `finance.journal.post`, `finance.journal.reverse`, `finance.journal.read`, `finance.report.view`, `finance.period.lock`, `finance.period.reopen`.

### FinanceSettings (1:1 Organization)

| Field | Rules |
|---|---|
| organization | PK/FK |
| country_code | ISO 3166-1 alpha-2, required at setup |
| base_currency | FK Currency, immutable once any posted journal exists |
| fiscal_year_start_month | 1–12 |
| timezone | IANA name |
| locale | language/format preference |
| tax_registration_applies | boolean; no tax engine in this slice |
| setup_completed_at | set on first successful setup |

No AED/Dubai defaults. No TRN field.

### Account

| Field | Rules |
|---|---|
| organization | required |
| code | unique per org |
| name | required |
| classification | asset, liability, equity, income, expense |
| is_control | if true, only opening/adjustment posting workflows may post |
| control_kind | nullable `ar` / `ap` / empty |
| status | active / inactive |
| version | integer, bump on edit |

Inactive accounts cannot be used on new posts.

### DocumentSequence

| Field | Rules |
|---|---|
| organization | required |
| document_type | `journal` this slice |
| series | default `default` |
| prefix | optional string |
| next_number | integer, allocated under row lock |
| unique | `(organization, document_type, series)` |

Issued numbers never decrement.

### FiscalPeriodLock

| Field | Rules |
|---|---|
| organization | required |
| start_on | date inclusive |
| end_on | date inclusive |
| status | open / locked |
| locked_by, locked_at | set on lock |
| reopen_reason, reopened_by, reopened_at | set on reopen; prior lock remains in audit |

Reject overlapping lock rows for the same org. Posting allowed when no **locked** row contains `journal.entry_date`.

### JournalEntry

| Field | Rules |
|---|---|
| organization | required |
| status | draft / posted |
| entry_date | required |
| number | assigned at post |
| memo | optional |
| source_type | `manual` / `opening` |
| version | optimistic concurrency |
| posted_at, posted_by | set once |
| reverses_id | FK self, nullable |
| reversed_by_id | FK self, nullable, unique — second reversal rejected |
| currency | must equal org base currency this slice |

Posted header immutable except `reversed_by_id` when a reversal links.

State: `draft → posted`. Posted → linked reversal (new posted journal). No delete.

### JournalLine

| Field | Rules |
|---|---|
| journal | FK |
| organization | denormalized, same as journal, RLS |
| account | FK, same org |
| description | optional |
| debit | Decimal ≥ 0 |
| credit | Decimal ≥ 0 |

Constraint: exactly one of debit, credit > 0; the other = 0. Sum(debit)=sum(credit) in base currency at post. Lines of posted journals immutable (no UPDATE/DELETE for app role).

### FinanceIdempotency

| Field | Rules |
|---|---|
| organization | required |
| operation | e.g. `journal.post`, `journal.reverse` |
| key | client key |
| request_hash | hash of body |
| journal_id | result |
| unique | `(organization, operation, key)` |

Identical body → return existing. Different body → conflict. In-progress unique violation → conflict.

### FinanceAuditEvent

| Field | Rules |
|---|---|
| organization | required |
| actor_user_id | required |
| action | post, reverse, lock, reopen, access.grant, settings.update |
| object_type, object_id | identifiers |
| payload | minimal ids/amounts, no secrets |

Append-only via API.

## Relationships

```text
Organization 1—1 FinanceSettings
Organization 1—* FinanceRole
Membership *—0..1 FinanceRole
Organization 1—* Account, DocumentSequence, FiscalPeriodLock, JournalEntry, FinanceIdempotency, FinanceAuditEvent
JournalEntry 1—* JournalLine
JournalEntry 0..1 — reverses → JournalEntry
```

## Validation rules (service + DB)

1. All finance FKs same `organization_id`.
2. Base currency change blocked if posted journals exist.
3. Closed period contains date ⇒ post/reverse rejected.
4. Control accounts: only `source_type=opening` (this slice).
5. RLS: `current_setting('app.organization_id')` must match row `organization_id` and be non-empty.
