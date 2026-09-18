# Finance Backend Production Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Work in order, use test-driven changes, keep each accounting operation atomic, and request review after every numbered work package. Do not implement frontend code from this document.

**Goal:** Repair the verified correctness and isolation defects, then complete the finance backend to a production accounting release gate.

**Architecture:** Keep the existing Django modular monolith and one immutable double-entry ledger. Move command ownership into transaction-bound services, enforce organization boundaries in PostgreSQL and application code, and make all subledgers reconcile to the posted ledger.

**Tech Stack:** Python 3.12+, Django 5, Django REST Framework, PostgreSQL 16, Celery, Redis, pytest, pytest-django, and the existing Clerk-based identity boundary.

**Spec:** `docs/superpowers/plans/2026-09-17-generalized-finance-system.md`

**Companion conventions:** `docs/engineering/finance-agent-build-guide.md`. That guide remains the general coding standard; this document is the authoritative defect register, remaining backend backlog, and release gate.

## Global constraints

- One organization is one set of books; users may have memberships in multiple organizations.
- Do not add Entity, Business Center, or Location as a finance owner.
- Keep the core country-neutral and enable jurisdiction rules only through verified capability packs.
- Preserve posted history through linked reversals.
- Do not expose unfinished APIs or weaken financial invariants to preserve compatibility.

**Status:** Required before production release  
**Reviewed baseline:** commits `6e8dc1d` and `abd622b` on 2026-09-18  
**Scope:** Django/DRF finance backend, PostgreSQL, Celery, Redis, API contracts, data migration, security, observability, and operations  
**Out of scope:** browser UI, mobile UI, Entity, Business Center, Location-as-books-owner, consolidation, and intercompany accounting

## 1. Product boundary

One `tenancy.Organization` is one independent set of books. A user may belong to and hold different finance permissions in multiple organizations. Every finance request, job, query, write, attachment, import, export, audit event, and integration callback must resolve exactly one organization before touching finance data.

Reuse `Organization` and `Membership`. Do not introduce another tenant owner model. Warehouses are stock locations. Reporting tags are analytical dimensions. Neither is an accounting owner or security boundary.

This is a production accounting backend for small and midsize businesses across industries. The core must remain country-neutral. Jurisdiction-specific behavior is enabled through explicit, versioned country capability packs after accountant and authority validation.

## 2. Verified baseline

The current repository contains a broad finance API and service layer for setup, chart of accounts, journals, sales, purchases, payments, banking, recurring documents, approvals, inventory, assets, and reports.

Verification on 2026-09-18 produced:

- `python manage.py check`: passed.
- `python manage.py makemigrations --check --dry-run`: no model changes detected.
- Full test suite: 31 passed and 1 skipped in 143.91 seconds.
- The skipped test is the only PostgreSQL/RLS test and checks policy names rather than actual isolation or concurrency.
- The finance package contains roughly 10,000 lines of Python and only 19 finance test functions. Existing coverage is a smoke suite, not production evidence.

Passing tests do not certify the books. The defects below can corrupt inventory, duplicate money movement, drop bank transactions, cross tenant boundaries, or produce misleading reports.

### Confirmed issue register

| Priority | Verified issue | Required correction | Owning package |
|---|---|---|---|
| P1 | Raw request IDs can create cross-organization references and failed create/post requests leave orphan rows | Organization-scoped resolvers and one atomic command service | B1 |
| P1 | Partial customer/vendor credits reverse every source stock movement | Source-line quantities and proportional return movements | B2 |
| P1 | Stock quantity is rounded using currency precision | Independent quantity and valuation precision | B3 |
| P1 | Concurrent idempotency collision queries inside a broken transaction; retries can create redundant documents | Command-level idempotency with safe conflict recovery | B4 |
| P1 | Concurrent refunds can exceed the remaining payment advance | Lock payment and recompute capacity inside the transaction | B5 |
| P1 | Same-date/amount/description bank rows are discarded as duplicates | Preserve rows and route ambiguous matches to review | B6 |
| P1 | Reconciliation can complete with unresolved lines and no ledger comparison | Evidence-based statement-to-book reconciliation | B7 |
| P1 | Supplied PostgreSQL role can bypass RLS; test checks only policy names | Restricted runtime role and behavioral isolation tests | B0 |
| P2 | Trial balance returns period movement without opening/closing balances | Production trial-balance semantics and drill-through | B8 |
| P2 | Currency catalogue contains only 20 hardcoded currencies | Versioned complete ISO 4217 data | B10 |

## 3. Non-negotiable engineering rules

1. **One ledger:** every financial total comes from posted journal lines or a reconciled subledger tied to them. Never maintain a second accounting truth.
2. **Thin API views:** parse the request, authorize the action, call one application service, and serialize the result. Views must not assemble or post financial models directly.
3. **Atomic commands:** create, validate, approve, post, allocate, move stock, and audit within one database transaction when they form one user action.
4. **Tenant-safe references:** load every foreign key with `organization=org`. A row's own `organization_id` is insufficient if one of its references belongs to another organization.
5. **Restricted PostgreSQL role:** migrations may own tables; the runtime application role must not own them, be superuser, or have `BYPASSRLS`.
6. **Append and reverse:** posted journals and their lines are immutable. Corrections create linked reversals and replacement documents.
7. **Explicit state machines:** document transitions are named commands with allowed source states. Reject implicit state changes and invalid repeats with stable error codes.
8. **Money and quantity are separate types:** money uses the currency exponent; quantity, exchange rates, unit cost, percentages, and tax rates use their own documented precision.
9. **Idempotency covers the whole command:** a retry returns the original command result. It must not create another draft, allocation, stock movement, payment, sequence number, or audit event.
10. **Lock before deciding:** when a decision depends on current balance, status, sequence, stock, allocation, approval count, or period state, read it under the lock used by the write.
11. **Effective-dated configuration:** tax, exchange rate, fiscal period, numbering, and country behavior are resolved for the transaction date and snapshotted on posting.
12. **No model signals for posting:** accounting effects must be visible in services and tests.
13. **No dead endpoints:** an API is advertised only when authorization, validation, persistence, audit, idempotency, tests, schema documentation, and operating instructions are complete.
14. **No fabricated compliance:** country tax, e-invoicing, filing, or accounting certification is not claimed without recorded expert review and sandbox evidence.

## 4. Severity and release policy

| Level | Meaning | Release treatment |
|---|---|---|
| P0 | Confirmed tenant leak, unrecoverable book corruption, or security compromise | Stop all releases and repair existing data |
| P1 | Can misstate books, duplicate money, lose transactions, or bypass required controls | Block production release |
| P2 | Materially incomplete accounting workflow or misleading behavior | Fix before the affected module is enabled |
| P3 | Maintainability, usability, or operational improvement | Schedule with the owning work package |

No feature is production-ready while a P0/P1 defect affects it. A feature flag may hide a complete module during rollout; it must not disguise unfinished correctness.

## 5. Work package B0: Establish a trusted PostgreSQL test environment

**Goal:** make PostgreSQL behavior, RLS, locks, constraints, and concurrent writes part of normal verification.

**Files:**

- Modify `docker-compose.yml`.
- Modify `backend/config/settings.py` and `.env.example`.
- Create `backend/apps/finance/tests/postgres/` with isolation and concurrency tests.
- Modify CI configuration when it is added to the repository.

- [x] Define a migration owner role and a separate `uap_app` runtime role. The runtime role must have only required schema/table/sequence privileges and must not have `SUPERUSER`, `BYPASSRLS`, or table ownership.
- [ ] Run migrations as the owner and application tests as `uap_app`.
- [x] Add an automated assertion against `pg_roles` and `pg_class` proving the runtime role is restricted and does not own finance tables.
- [x] Replace `test_rls_policies_exist` with behavioral tests: organization A cannot read, update, delete, or insert rows belonging to B; the same user can switch between authorized A and B contexts; a missing context returns no tenant rows and cannot write.
- [ ] Add two-connection tests for idempotency collisions, document posting, refunds, allocations, stock issue, sequence generation, and period close versus backdated posting.
- [x] Keep SQLite for fast pure-domain tests only. The production gate always runs PostgreSQL.

**Acceptance evidence:** the PostgreSQL suite passes as the restricted runtime role and fails when a cross-organization query or write is deliberately introduced.

## 6. Work package B1: Enforce tenant integrity and atomic command boundaries

**Problem:** several API views create finance rows using raw request foreign keys. Credit notes, vendor credits, payments, items, purchase orders, and related rows can be persisted before the posting service validates them. Failed posts leave orphan drafts, and known foreign IDs can form cross-organization relationships.

**Files:**

- Modify `backend/apps/finance/api/sales_views.py`.
- Modify `backend/apps/finance/api/purchase_views.py`.
- Modify `backend/apps/finance/api/views.py` and other direct-create views.
- Create focused command services under `backend/apps/finance/services/` only where an existing service cannot own the command cleanly.
- Add migrations for database constraints that PostgreSQL can enforce directly.
- Add `backend/apps/finance/tests/postgres/test_tenant_references.py`.

- [x] Inventory every request-supplied foreign key and map it to an organization-scoped resolver.
- [x] Replace direct model creation in API views with command services that validate all references before any row is written.
- [x] Wrap each create-and-post command in one `finance_tx` transaction. A rejected command leaves no document, line, allocation, stock movement, sequence, or audit event.
- [x] Validate parent and child organization equality for invoices, bills, credits, payments, contacts, items, accounts, taxes, warehouses, attachments, reporting tags, and allocations.
- [ ] Add database protection for parent-child tenant equality where practical. Where PostgreSQL cannot express a cross-table `CHECK`, constrain writes to services and add a deferred constraint trigger or a composite tenant-aware foreign key.
- [x] Return `cross_organization` without revealing whether a foreign row exists.
- [ ] Add negative tests for every document type using a valid ID from a second organization.

**Acceptance evidence:** no tested command can create a cross-organization reference, and every forced mid-command failure leaves the database unchanged.

## 7. Work package B2: Redesign credit notes, vendor credits, and stock returns

**Problem:** a credit linked to an invoice reverses every stock movement for that invoice. Vendor credits do the same for bills. Credit lines do not identify an original line, item, warehouse, or quantity.

**Files:**

- Modify `backend/apps/finance/models/sales.py` and `purchases.py`.
- Modify `backend/apps/finance/models/stock.py`.
- Modify `backend/apps/finance/services/sales.py`, `purchases.py`, and `stock.py`.
- Add migrations and API contract changes.
- Add `backend/apps/finance/tests/test_credit_returns.py`.

- [x] Add an immutable reference from each credit line to the original invoice or bill line when the credit reverses a source document.
- [x] Snapshot `item_id`, credited quantity, unit amount, tax, warehouse, and the original stock cost consumed by the return.
- [x] Track cumulative credited quantity and value per source line under row locks.
- [x] Reject quantities or values that exceed the uncredited source balance.
- [x] Support explicit price-only credits that affect AR/AP and revenue/expense without moving stock.
- [x] Reverse only the credited stock quantity. Restore sales returns at the original issued cost; remove purchase returns using the defined moving-average policy and record any required valuation difference explicitly.
- [x] Make repeat posting idempotent and prohibit posting an already posted credit under a different key.
- [ ] Add tests for partial return, multiple partial returns, full return, price-only credit, service item credit, mixed tracked/untracked lines, cross-warehouse return, over-credit, retry, and concurrent credits.

**Acceptance evidence:** inventory, COGS, AR/AP, tax, and source-document outstanding amounts remain tied after every scenario.

## 8. Work package B3: Separate quantity, unit-cost, rate, and money precision

**Problem:** stock quantity is rounded with the base currency exponent. Fractional stock is therefore corrupted for zero- and two-decimal currencies.

**Files:**

- Modify `backend/apps/finance/services/money.py` or split it into focused numeric helpers.
- Modify `backend/apps/finance/services/stock.py`.
- Review all decimal fields in `backend/apps/finance/models/`.
- Add migration only if stored field precision changes.
- Add `backend/apps/finance/tests/test_numeric_precision.py`.

- [x] Define named precision rules: `Money`, `Quantity`, `UnitCost`, `ExchangeRate`, `TaxRate`, and `Percentage`.
- [x] Quantize stock quantity independently of currency, preserving the documented quantity scale.
- [x] Carry extra precision for moving-average unit cost; round monetary movement value only at the ledger boundary.
- [x] Define rounding mode explicitly and apply it consistently.
- [ ] Add boundary tests for JPY, USD, KWD, fractional quantities, repeating average costs, many small movements, and zero-stock cleanup.
- [ ] Provide a data audit command that identifies balances previously rounded by currency precision before this fix.

**Acceptance evidence:** the stock movement ledger reproduces stored quantities and values without currency-dependent quantity loss.

## 9. Work package B4: Make idempotency cover complete business commands

**Problems:** the concurrent insert recovery queries inside a broken atomic transaction, and payment/credit endpoints create a new document before applying an idempotency key whose request body contains that new ID.

**Files:**

- Modify `backend/apps/finance/services/posting.py`.
- Modify sales, purchase, banking, stock, asset, and recurring command services.
- Modify `backend/apps/finance/models/config.py` if the idempotency record needs a command result payload or resource type/id.
- Add `backend/apps/finance/tests/postgres/test_idempotency.py`.

- [x] Start idempotency before creating any command-owned resource.
- [x] Hash the stable external request, excluding server-generated IDs and timestamps.
- [x] Insert the key within an inner savepoint or use a locking strategy that remains queryable after a unique conflict.
- [x] Store command resource type/id on the idempotency row.
- [ ] Store command status (`in_progress`, `succeeded`, `failed_retryable`), resource type/id, response status, and a minimal response snapshot.
- [ ] Define safe handling for a crashed `in_progress` command without allowing two owners.
- [x] Return the original result for the same key and payload; return `idempotency_conflict` for a different payload.
- [ ] Add concurrent tests proving exactly one document, journal, sequence number, allocation set, stock movement set, and audit event exist.

**Acceptance evidence:** network retries and simultaneous identical requests are observationally equivalent to one successful command.

## 10. Work package B5: Lock allocations, refunds, and payment capacity

**Problem:** customer and vendor refund availability is calculated outside the transaction without locking the payment. Concurrent refunds can exceed the remaining advance.

**Files:**

- Modify `backend/apps/finance/services/sales.py` and `purchases.py`.
- Review payment runs and automatic allocations for the same pattern.
- Add `backend/apps/finance/tests/postgres/test_payment_concurrency.py`.

- [x] Enter `finance_tx` before reading payment capacity.
- [x] Lock the payment and all source documents whose outstanding values determine the command.
- [x] Recompute allocated, refunded, and available amounts while locks are held.
- [x] Reject zero and negative payments/refunds before journal construction.
- [ ] Add uniqueness or command invariants preventing duplicate allocation rows on replay.
- [ ] Test two simultaneous full refunds, refund versus allocation, two allocations against the same invoice/bill, and payment-run overlap.

**Acceptance evidence:** successful allocations plus refunds can never exceed the posted payment or source-document outstanding amount.

## 11. Work package B6: Preserve bank statement evidence and detect duplicates safely

**Problem:** a unique fingerprint of account, date, amount, and description discards legitimate repeated transactions and does not retain ambiguous candidates for review.

**Files:**

- Modify `backend/apps/finance/models/banking.py`.
- Modify `backend/apps/finance/services/banking.py`.
- Modify statement import contracts and tests.
- Add migrations and `backend/apps/finance/tests/test_bank_duplicate_review.py`.

- [x] Store the original statement file hash and import timestamp.
- [ ] Store the original statement file hash, parser version, source row number, raw normalized row, provider transaction ID when present, and import timestamp.
- [ ] Use provider transaction ID as the strongest deduplication key when it is stable.
- [x] Treat heuristic fingerprint matches as candidates, not automatic deletion.
- [x] Persist every candidate with a reason and let an authorized user accept, merge, or keep it.
- [x] Make re-import of the identical file idempotent while preserving two identical rows that occur within that file.
- [ ] Record parser errors per row and allow corrected re-import without losing evidence.
- [ ] Add fixtures for repeated card charges, recurring fees, same-day payroll rows, reversed transactions, and overlapping statement periods.

**Acceptance evidence:** a statement's row count, accepted duplicates, rejected duplicates, and errors reconcile to the source file.

## 12. Work package B7: Implement real bank reconciliation

**Problem:** reconciliation completion checks only `opening + all statement lines = closing`. It can complete with every line unresolved and never compares the statement to the general ledger.

**Files:**

- Modify `backend/apps/finance/models/banking.py` and add reconciliation-line membership/evidence.
- Modify `backend/apps/finance/services/banking.py`.
- Add selectors for book balance and reconciliation summary.
- Add `backend/apps/finance/tests/test_bank_reconciliation.py`.

- [x] Snapshot statement opening/closing and book balance at complete.
- [x] Snapshot statement opening/closing balance, book opening/closing balance, selected cleared lines, outstanding book entries, outstanding statement lines, and final difference.
- [x] Require every selected statement line to be matched, categorized, transferred, or explicitly excluded with a reason.
- [x] Calculate the ledger bank balance from posted journal lines through the reconciliation cutoff.
- [x] Complete only when the defined reconciliation equation reaches zero at currency precision.
- [x] Lock completed evidence. Reopening requires permission, reason, audit event, and version check.
- [x] Reject overlapping completed reconciliation periods for the same account unless the previous one is reopened.
- [x] Add tests for unresolved rows and duplicate candidates.
- [x] Add tests for unresolved rows, uncleared book entries, outstanding checks/deposits, fees, transfers, duplicate candidates, reopening, and backdated posting after completion.

**Acceptance evidence:** an accountant can reproduce the completed result from immutable statement and ledger evidence.

## 13. Work package B8: Correct trial balance and finish production reporting

**Problem:** trial balance currently reports gross period movement rather than opening, movement, and closing account balances. Production exports and several required reports are absent.

**Files:**

- Modify `backend/apps/finance/selectors/reports.py`.
- Split report selectors by report when the existing file becomes difficult to review.
- Add report serializers/export services and tests.

- [x] Return opening debit/credit, period debit/credit, and closing debit/credit by account, with one-sided net closing balances.
- [x] Support as-of and period semantics explicitly in the API contract.
- [x] Add drill-through IDs/counts so every reported amount traces to posted journal lines.
- [x] Tie AR and AP aging to control accounts; tie inventory valuation to inventory GL; tie the asset register to cost and accumulated depreciation; tie cash-flow change to cash accounts.
- [ ] Complete tax summary, bank reconciliation report, retained earnings/movement of equity, comparative periods, and closing package.
- [ ] Add CSV and XLSX data exports and PDF/print rendering through a deterministic report snapshot.
- [ ] Create accountant-reviewed golden fixtures for cash/accrual, credits, FX, tax, inventory, assets, and close/reopen.
- [x] Add invariants: debits equal credits, balance sheet balances, subledgers tie, and opening plus movement equals closing.

**Acceptance evidence:** every report total is reproducible from posted entries and agrees with its control account or documented reconciliation.

## 14. Work package B9: Complete period and year close

- [x] Add close prerequisites: bank reconciliations, unresolved exceptions, draft/awaiting-approval documents, subledger differences, stock/asset differences, missing FX rates, and unposted schedules.
- [x] Add an authorized close command that locks the period under the same strategy used by posting.
- [x] Add year-end retained earnings treatment appropriate to the selected accounting policy.
- [ ] Add scheduled adjustments, accruals, deferrals, depreciation, and closing FX revaluation with reversal/settlement policy.
- [x] Make reopening reasoned, permissioned, versioned, and fully audited.
- [ ] Test close versus concurrent backdated posting and every reopening consequence.

## 15. Work package B10: Complete international currency and tax foundations

- [x] Replace the 20-row currency tuple with a complete versioned ISO 4217 dataset, including active code, exponent, effective dates, and deprecation handling.
- [x] Validate exchange rates as positive, define direction as `base = transaction × rate`, and resolve the latest valid effective rate according to policy.
- [ ] Implement realized and unrealized FX with documented rounding and reversal behavior.
- [ ] Version generic tax rules: inclusive/exclusive tax, compound tax, exemptions, reverse charge, withholding, recoverable/nonrecoverable purchase tax, and effective dates.
- [ ] Snapshot the applied tax rule and presentation fields on posted documents.
- [ ] Define a country-capability interface for invoice requirements, tax reports, e-invoicing, filing, retention, language, and provider integration.
- [ ] Enable a country pack only after jurisdiction-specific fixtures, authority sandbox evidence where available, and recorded accountant review.

The generic core must not default to UAE, Dubai, or any other country. It must also not claim worldwide compliance merely because a currency code exists.

## 16. Work package B11: Complete imports, exports, and API contracts

- [ ] Build dry-run import jobs with column mapping, row validation, error download, deterministic replay, and reconciliation summary.
- [ ] Support the documented import order: settings/chart, contacts/items, opening balances or history, outstanding documents, bank opening state, then later transactions.
- [ ] Prevent posting both historical activity and duplicate opening balances for the same cutover.
- [ ] Generate and validate OpenAPI schemas for all public endpoints, stable error codes, idempotency requirements, pagination, filters, and permissions.
- [ ] Add authorized full export for an organization's configuration, master data, documents, ledger, audit, and attachments.
- [ ] Version externally consumed APIs and document deprecation policy.
- [ ] For future webhooks, require signatures, event IDs, organization routing, durable inbox/outbox state, retries, and dead-letter handling.

## 17. Work package B12: Production security and privacy

- [ ] Complete a finance STRIDE review covering tenant isolation, posting, approvals, imports, files, jobs, integrations, and exports.
- [ ] Enforce least-privilege finance permissions at the service boundary; list permissions and command permissions are separate.
- [ ] Require step-up authentication for high-impact actions such as changing bank details, exporting all books, reopening a closed period, changing base currency before first posting, and managing privileged roles.
- [ ] Scan attachments, validate actual content type, enforce size limits, store outside the web root, use expiring authorized downloads, and record access events.
- [ ] Redact financial and personal data from logs, traces, task payloads, and exception messages.
- [ ] Rate-limit expensive reports, imports, exports, login-adjacent endpoints, and integration callbacks.
- [ ] Add dependency, secret, and static security scanning to CI.

## 18. Work package B13: Reliability, performance, and operations

- [ ] Add structured logs with request ID, organization ID, command name, resource ID, idempotency key hash, duration, and result without sensitive payloads.
- [ ] Add metrics for posting latency/failure, idempotency conflicts, sequence contention, reconciliation differences, job lag, import errors, report duration, and tenant isolation failures.
- [ ] Trace API, database, Celery, storage, and external provider spans.
- [ ] Define service-level objectives and alerts for posting, report generation, imports, jobs, and integration callbacks.
- [ ] Add query-count and representative load tests for lists, dashboard aggregates, aging, ledger, and reports.
- [ ] Add safe pagination and indexed filter paths; inspect PostgreSQL query plans for large ledgers.
- [ ] Create backup, point-in-time recovery, restore, migration rollback, and incident runbooks. Execute restore and rollback exercises and retain evidence.
- [ ] Make deployments backward compatible across application and migration rollout. Destructive schema cleanup occurs only after data verification and rollback windows.

## 19. Required test portfolio

| Layer | Required evidence |
|---|---|
| Pure domain | tax, FX, money, quantity, aging buckets, schedules, depreciation, reconciliation equations |
| Service integration | each command's state transition, journal, subledger, audit, idempotency, and rollback |
| PostgreSQL | RLS, role restrictions, constraints, locks, concurrent commands, sequences, period close |
| Contract | request/response schema, permissions, errors, pagination, filters, idempotency headers |
| Property/invariant | balanced ledger, nonnegative remaining capacity, subledger ties, stock movement sum |
| Golden accounting | accountant-approved end-to-end months with expected journals and reports |
| Failure/retry | database conflict, worker retry, storage failure, email/provider timeout, partial import |
| Performance | representative organization sizes and measured query/latency budgets |
| Recovery | backup restore, migration rollback, replay of durable jobs and integration inbox |

Tests must assert amounts and state, not only HTTP status or total debits equal total credits.

## 20. Agent execution protocol

For every work package:

1. Read this guide, the relevant feature spec, models, services, API views, migrations, and existing tests.
2. Write the smallest failing test that proves the defect or missing invariant. Use PostgreSQL when locks, constraints, RLS, or concurrency matter.
3. Run the focused test and record the expected failure.
4. Make the smallest coherent implementation that fixes the complete invariant.
5. Run focused tests, the finance suite, migration checks, Django checks, and the full suite.
6. Review the diff for tenant scoping, atomicity, idempotency, audit, permissions, and data migration impact.
7. Update API schema, operator documentation, and this checklist in the same change.
8. Commit one independently reviewable work package. Do not combine unrelated refactors.

An agent must not mark a package complete based on SQLite results when PostgreSQL behavior matters. An agent must not weaken an assertion to make a failing test pass.

## 21. Backend production release gate

- [ ] All P0/P1 findings are fixed and regression-tested.
- [ ] Runtime PostgreSQL role and behavioral RLS isolation tests pass.
- [ ] Concurrent posting, allocation, refund, stock, sequence, and close tests pass.
- [ ] Credits/returns and bank duplicates preserve complete evidence.
- [ ] Reconciliation reaches zero against statement and ledger evidence.
- [ ] Trial balance and every enabled subledger/report tie to the ledger.
- [ ] No advertised backend endpoint lacks authorization, validation, audit, idempotency where applicable, tests, and API documentation.
- [ ] Country capabilities are explicit; unsupported compliance paths are absent from advertised scope.
- [ ] Representative load, migration, backup restore, rollback, and incident exercises have retained results.
- [ ] Accounting, security, engineering, and operations reviewers have recorded approval.
