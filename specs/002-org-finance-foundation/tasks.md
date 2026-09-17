# Tasks: Organization Finance Foundation and Immutable Ledger

**Input**: Design documents from `/specs/002-org-finance-foundation/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/finance-http.md, quickstart.md

**Tests**: Required by spec acceptance scenarios and the finance agent build guide (accounting, isolation, concurrency). No frontend.

**Organization**: Tasks grouped by user story. Backend/API only.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1–US5 from spec.md

## Path Conventions

- `backend/apps/finance/` new app
- `backend/apps/tenancy/` org create + `finance_role` FK
- `backend/apps/authentication/` reuse envelope/RLS; narrow step-up helper

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Register the finance app without behavior

- [x] T001 Create `backend/apps/finance/` package (`apps.py`, `models/__init__.py`, `services/__init__.py`, `api/__init__.py`, `selectors/__init__.py`, `tests/__init__.py`)
- [x] T002 Register `apps.finance` in `backend/config/settings.py` INSTALLED_APPS and add `/api/v1/finance/` plus `/api/v1/organizations/` includes in `backend/config/urls.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared errors, money helpers, RLS-inside-transaction, permission constants

**⚠️ CRITICAL**: No user story work until this phase is complete

- [x] T003 Add finance error codes (`period_closed`, `journal_imbalanced`, `cross_organization`, `stale_version`, `base_currency_locked`, `control_account_restricted`, `already_reversed`, `account_inactive`, `missing_context`, `step_up_required`) to `backend/apps/authentication/constants.py` ERROR_CATALOGUE
- [x] T004 Add `require_finance_transaction_context` in `backend/apps/finance/services/context.py` that opens `transaction.atomic()`, calls `set_rls_context` with validated membership org, and raises `missing_context` if untrusted
- [x] T005 Add permission action constants and preset map in `backend/apps/finance/permissions.py` (`finance.access.manage`, `finance.settings.configure`, `finance.account.maintain`, `finance.journal.create`, `finance.journal.post`, `finance.journal.reverse`, `finance.journal.read`, `finance.report.view`, `finance.period.lock`, `finance.period.reopen`) matching data-model.md
- [x] T006 Add `quantize_amount(amount, exponent)` in `backend/apps/finance/services/money.py` using `Decimal` only (no float)
- [x] T007 Add Clerk JWT freshness check `require_step_up(request)` in `backend/apps/authentication/services/step_up.py` (iat or auth_time within 5 minutes → else `step_up_required`)

**Checkpoint**: Foundation ready

---

## Phase 3: User Story 1 - Open independent books (P1) 🎯 MVP

**Goal**: Create orgs, complete per-org finance setup, isolated settings/chart/sequences

**Independent Test**: Two orgs, different currencies and fiscal starts; A data invisible under B context

**FIN**: FIN-01, FIN-06 foundation, FR-001–003, FR-012 (sequence row)

- [x] T008 [P] [US1] Add `Currency` (code PK, exponent 0–3, name) and seed ISO currencies in `backend/apps/finance/models/currency.py` + data migration
- [x] T009 [P] [US1] Add `FinanceSettings` 1:1 Organization in `backend/apps/finance/models/settings.py` (country_code required, base_currency FK, fiscal_year_start_month 1–12, timezone, locale, tax_registration_applies, setup_completed_at). No AED/Dubai defaults
- [x] T010 [P] [US1] Add `FinanceRole` in `backend/apps/finance/models/access.py` (organization FK, slug unique per org, name, permissions JSON, is_preset). Add nullable `Membership.finance_role` FK in `backend/apps/tenancy/models.py`
- [x] T011 [P] [US1] Add `Account` (code unique per org, classification asset/liability/equity/income/expense, is_control, control_kind ar/ap/empty, status active/inactive, version) in `backend/apps/finance/models/account.py` and `DocumentSequence` (unique organization+document_type+series, next_number, prefix) in `backend/apps/finance/models/sequence.py`
- [x] T012 [US1] Migrations + RLS SQL for new tables (`organization_id = current_setting('app.organization_id')` non-empty) in `backend/apps/finance/migrations/` and `backend/apps/finance/sql/rls.sql`
- [x] T013 [US1] Implement `create_organization` and setup seed (preset roles, journal sequence) in `backend/apps/finance/services/setup.py`. Base currency change rejected after any posted journal (`base_currency_locked`)
- [x] T014 [US1] Implement `POST/GET /api/v1/organizations` in `backend/apps/tenancy/api.py` (or `backend/apps/finance/api/organizations.py`) per `specs/002-org-finance-foundation/contracts/finance-http.md`
- [x] T015 [US1] Implement `GET/PUT /api/v1/finance/settings` and `GET/POST/PATCH /api/v1/finance/accounts` in `backend/apps/finance/api/views.py` + `backend/apps/finance/api/urls.py`
- [x] T016 [US1] Tests in `backend/apps/finance/tests/test_setup_isolation.py`: two orgs USD/Jan vs EUR/July; currency lock after post; no finance data without grant; same account codes allowed in both orgs

**Checkpoint**: US1 independently testable via API

---

## Phase 4: User Story 2 - Grant and enforce finance access (P1)

**Goal**: Explicit org-level finance roles; location does not imply finance; grants do not transfer

**Independent Test**: Accountant in A / Viewer in B; location-only member denied; generic member denied

**FIN**: FIN-01, FR-004–007, FR-011

- [x] T017 [US2] Implement `has_finance_permission(user, org, action)` in `backend/apps/finance/services/access.py`: null `finance_role` ⇒ deny; suspended/removed membership ⇒ deny; location on membership ignored except that it never grants access
- [x] T018 [US2] Implement roles/grants API `GET/POST /api/v1/finance/roles` and `GET/PUT /api/v1/finance/grants/{user_id}` in `backend/apps/finance/api/access_views.py` with step-up on writes; cannot uniquely self-grant owner; audit `access.grant`
- [x] T019 [US2] Tests in `backend/apps/finance/tests/test_access.py`: member 403; A accountant post vs B viewer post denied; location-only 403; sales_clerk cannot post/reopen; grant change audited

**Checkpoint**: Permission matrix holds without journals beyond US1 post permission checks

---

## Phase 5: User Story 3 - Record, inspect, reverse posted journals (P1)

**Goal**: Draft/post balanced journals, immutability, linked reversal, org-scoped idempotency

**Independent Test**: Post 100/100, reject imbalance, reverse, replay key, concurrent duplicate → one journal

**FIN**: FIN-02, FR-014–017, FR-019, FR-021, FR-024

- [x] T020 [P] [US3] Add `JournalEntry`/`JournalLine` in `backend/apps/finance/models/ledger.py`: status draft/posted, source_type manual/opening, version, reverses/reversed_by, Decimal debit/credit with exactly-one-nonzero constraint, denormalized organization_id on lines
- [x] T021 [P] [US3] Add `FinanceIdempotency` unique `(organization, operation, key)` in `backend/apps/finance/models/idempotency.py` and `FinanceAuditEvent` append-only in `backend/apps/finance/models/audit.py`
- [x] T022 [US3] Implement `post_journal` in `backend/apps/finance/services/posting.py`: RLS+locks in one transaction; server-side totals; quantize to currency exponent; reject imbalance with zero writes; snapshot is posted state; no signals
- [x] T023 [US3] Implement `reverse_journal` in `backend/apps/finance/services/posting.py`: opposite posted journal, reason+actor, `reversed_by` unique, retry does not duplicate
- [x] T024 [US3] Sequence allocate under `select_for_update` in `backend/apps/finance/services/sequence.py`; never reuse issued numbers
- [x] T025 [US3] DB/ORM protection: posted journals/lines not updatable/deletable from services; control accounts only `source_type=opening`
- [x] T026 [US3] Journal API: `GET/POST /api/v1/finance/journals`, `PATCH` draft, `POST .../post`, `POST .../reverse` in `backend/apps/finance/api/journal_views.py`. Idempotency-Key required on post/reverse
- [x] T027 [US3] Tests in `backend/apps/finance/tests/test_posting.py`: balanced post; imbalance no rows; posted mutate rejected; reverse preserves original; idempotent replay vs conflict; 0/2/3 decimal currencies; opening vs control account; concurrent post same key (Postgres)

**Checkpoint**: Ledger kernel demonstrable via API

---

## Phase 6: User Story 4 - Lock periods and inspect history (P2)

**Goal**: Period lock/reopen, drafts excluded from reports, close vs post race

**Independent Test**: Lock → backdated post fails; TB/GL omit drafts; concurrent close/post consistent

**FIN**: FIN-02/10 foundation, FR-018, FR-020–022

- [x] T028 [US4] Add `FiscalPeriodLock` (non-overlapping ranges, status open/locked, reopen reason fields) in `backend/apps/finance/models/period.py`
- [x] T029 [US4] Period lock checks inside `post_journal`/`reverse_journal`; shared lock order with posting (period row then journal then sequence)
- [x] T030 [US4] Period API `GET /api/v1/finance/periods`, lock, reopen (step-up + reason) in `backend/apps/finance/api/period_views.py`
- [x] T031 [US4] Trial balance and GL selectors in `backend/apps/finance/selectors/reports.py` (published only) and `GET /api/v1/finance/reports/trial-balance`, `GET /api/v1/finance/reports/general-ledger` in `backend/apps/finance/api/report_views.py`
- [x] T032 [US4] Tests in `backend/apps/finance/tests/test_periods_reports.py` and Postgres race in `backend/apps/finance/tests/test_postgres_isolation.py`

**Checkpoint**: Close controls and inspectable TB/GL

---

## Phase 7: User Story 5 - Finance API without a client app (P2)

**Goal**: Stable errors, stale version, named actions, documented operator path

**Independent Test**: Drive US1–US4 solely via HTTP; stale version rejected; cross-org refs fail closed

**FIN**: FIN-14 deferred UI; FR-023, FR-025

- [x] T033 [US5] Wire Spectacular tags for Finance in `backend/config/settings.py`; ensure all finance views use envelope helpers
- [x] T034 [US5] Contract tests in `backend/apps/finance/tests/test_api_contract.py` for error codes in `specs/002-org-finance-foundation/contracts/finance-http.md` (including `stale_version`, `cross_organization`, `missing_context`)
- [x] T035 [US5] Confirm no frontend files, empty pages, or placeholder finance routes were added

**Checkpoint**: Operator can complete quickstart.md without a GUI

---

## Phase 8: Polish & Cross-Cutting

- [x] T036 Run auth regression `backend` pytest `apps/authentication/tests` and finance tests; `manage.py check`; `makemigrations --check --dry-run`
- [x] T037 Record actual commands/exit codes in `specs/002-org-finance-foundation/verification.md`
- [x] T038 Threat-model finance writes (grants, post, reverse, export-none) as an addendum in `docs/security/STRIDE.md` without logging amounts+PII together

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup → Foundational → US1 → US2 → US3 → US4 → US5 → Polish
- US2 can overlap US1 API once Membership.finance_role exists
- US3 depends on settings/accounts/roles
- US4 depends on posting
- US5 depends on routes from US1–US4

### User Story Dependencies

- **US1**: After Phase 2
- **US2**: After T010 (role FK)
- **US3**: After US1 accounts/settings
- **US4**: After US3 post
- **US5**: After routes exist

### Parallel Opportunities

- T008–T011 models in parallel
- T020–T021 models in parallel
- US2 tests vs US1 chart tests after T010

### Parallel Example: US1 models

```text
T008 Currency
T009 FinanceSettings
T010 FinanceRole + Membership FK
T011 Account + DocumentSequence
```

---

## Implementation Strategy

### MVP

T001–T016: org create + setup + isolated chart. Stop and validate two-org test.

### Incremental

Then access → posting → periods/reports → contract polish.

### Exclusions (do not implement)

Frontend, email invites, FX journals, invoices/bills, bank, country packs, Entity/Business Center, CIA copy.
