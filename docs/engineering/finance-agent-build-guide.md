# Finance product — LLM and agent build guide

**Status:** Instructions for future implementation; no implementation is performed by this document.  
**Product contract:** [Production product plan](C:/Users/builtpulse/Desktop/uap/docs/superpowers/plans/2026-09-17-generalized-finance-system.md).  
**Research:** [Reference review and competitor analysis](C:/Users/builtpulse/Desktop/uap/docs/research/2026-09-17-finance-competitor-analysis.md).

## 1. Mission and instruction priority

Build the agreed production finance product for small and midsize businesses. Every organization owns independent books; a user may have different roles in multiple organizations. There is no Entity or Business Center module, no Dubai/UAE restriction, and no MVP downgrade. Avoid redundant systems and features without a real user workflow.

Follow the user's latest instructions, applicable repository instructions, and `.specify/memory/constitution.md`. Read the plan and this guide before implementation. Preserve unrelated work. Do not copy secrets, customer data, or production databases from the CIA reference.

The plan's feature and operational requirements define completion. A simplified demo, a successful happy path, or passing unit tests alone does not satisfy the production contract. Equally, a request for production quality does not authorize extra ERP modules, arbitrary abstractions, or speculative integrations.

## 2. Establish the actual starting state

Before proposing changes, inspect repository status, installed dependencies, existing migrations, identity/tenancy models, API conventions, and relevant tests. The inspected UAP repository currently contains authentication/tenancy code and plans describing a frontend that is not present. Do not report that frontend as implemented. Recheck this at execution time; these notes may age.

Reuse Clerk identity and UAP Organization/Membership. Verify finance-ready authorization and PostgreSQL RLS rather than assuming authentication already proves tenant isolation. Do not create another login/session system. Test application-role behavior, not only database-superuser behavior: PostgreSQL documents owner and privileged-role bypass considerations. [PostgreSQL row security](https://www.postgresql.org/docs/17/ddl-rowsecurity.html)

Use Django/DRF, PostgreSQL, Redis and Celery already selected by the repository. For a new frontend, the existing identity plan proposes React/Vite; establish the actual frontend contract and lockfile in its first task. Use supported, pinned dependency versions and record necessary additions. No microservice split or separate message bus without a measured requirement.

## 3. Work-package map

Create independent Speckit feature directories for these packages. Choose directory numbers only after checking existing specifications. Each directory contains `spec.md`, `plan.md`, `tasks.md`, `data-model.md`, API contracts, and `verification.md`. Add ADRs only for consequential choices, not every implementation detail.

| Package | Required outcome | Depends on | Requirement coverage |
|---|---|---|---|
| A — Access and product shell | Organization lifecycle/invitations/switching, action permissions, finance setup, trusted request/job context, UI shell | Existing identity verified | FIN-01, FIN-14, part FIN-15 |
| B — Accounting kernel | Accounts, money/FX rules, posting, journal history/reversals, numbering, period locks, opening balances, ledger reports | A | FIN-02, foundation FIN-06/10/11 |
| C — Commercial documents | Contacts/items, tax calculations, quotes/orders, invoices, bills, expenses, complete draft/approval/posting UI | B | FIN-03/04/06/14 |
| D — Settlements | Customer/vendor payments, allocations, credits/refunds/advances, FX settlement, aging/control-account tie-out | C | FIN-03/04/06/10 |
| E — Banking | Imports, duplicate review, rules, bank/GL linking, splits/groups/transfers/fees, reconciliation | D | FIN-05/12 |
| F — Inventory and assets | Receipt/stock/return flows, warehouses, valuation/COGS, assets/depreciation/disposal | C, D, B | FIN-07/09, part FIN-04/10 |
| G — Reporting and close | Financial statements, formal cash flow, dated aging, inventory/assets/tax reports, tags, comparative periods, FX revaluation/year close, consistent exports | B–F | FIN-02/06/08/10 |
| H — Controls and automation | Approval levels/thresholds, recurring documents/adjusting entries, reminders, customer portal, durable jobs | C, D and B's controls | FIN-03/11/14 |
| I — Country/provider integrations | Selected country packs, required filing/e-invoicing, bank/rate feeds, gateway callbacks/settlements, API integration controls | Selected market/provider decisions; E, H, tax core | FIN-05/06/12/13 |
| J — Migration and release | Imports/cutover, user documentation, performance/security/accessibility evidence, restore/deployment/incident exercises | All packages for release; infrastructure work starts with A | FIN-12/14/15, final coverage of all |

This is a dependency map, not a waterfall requirement. Security, audit, migrations, UI, and meaningful tests travel with each feature. Final verification of the integrated product cannot be delegated away to an isolated module test.

## 4. Feature admission and completion

Before adding an item, answer:

1. Who uses it, for what specific financial task, and where does that task start/end?
2. Is it already covered by an existing model, service, permission, query, scheduler, or integration?
3. Which accepted FIN requirement does it satisfy? If none, record it as a proposal; do not implement it speculatively.
4. Which data and ledger entries does it create or change? What happens when it fails, retries, or is corrected?
5. How will a user access it, and what evidence proves the complete workflow works?

Do not add placeholder routes/pages, unused settings, generic plugin frameworks, separate role-specific accounting engines, or a second report calculation for export. If a feature is rejected, remove its planned navigation and scaffold as well. Before removing existing code, check all callers and tests; lack of a UI button alone does not establish that an API feature is dead.

For included features, complete the real vertical workflow: model/constraints → service → permissions/API → UI → audit → errors/recovery → tests → documentation. Record unfinished dependencies honestly. Do not satisfy a required gateway or bank connection with an always-success mock in production code.

## 5. How to specify and execute a task

Keep tasks independently reviewable and sized around one verifiable outcome. A package is not a single giant task. Specify exact repository files and callable contracts after exploring the implementation context. Avoid prematurely inventing a universal model or giant service file to connect unrelated flows.

Every task packet must include:

```text
Task ID and package:
FIN requirement IDs:
User outcome and entry point:
Preconditions / completed dependencies:
Files allowed to change:
Input/output API and service contracts:
Data ownership, constraints, and migration:
Required permissions:
Lifecycle and accounting entries (including correction):
Transaction/locking/idempotency rules:
Failure, retry, and user-visible error behavior:
Acceptance scenarios with concrete figures:
Tests and exact commands to run:
UI/document verification:
Observability and operational impact:
Evidence destination:
Explicit exclusions:
```

Fill every field with actual content when generating tasks. This template is an instruction, not an executable task. Do not mark a packet ready while interfaces, accounting rules, or expected results remain unspecified.

Task execution sequence:

1. Read the relevant specification, dependencies, code, and tests. Check the worktree for others' changes.
2. Write the behavioral regression/accounting scenario that defines correctness; verify it detects the missing behavior before implementation where applicable.
3. Implement through the shared services, with database protections for money and tenant boundaries.
4. Complete UI/API behavior and failure paths in the same deliverable or identify an explicit dependent task; an API-only task must not claim user-facing feature completion.
5. Run focused tests, then affected integrations and required package checks. Concurrency/RLS tests must use PostgreSQL and separate connections/processes where necessary.
6. Inspect the diff, migrations, generated schema, and UI/documents. Remove redundant helpers and unreachable scaffolding created by the task.
7. Record exact evidence and remaining risks in `verification.md`, update `tasks.md`, and report actual status.

Use task states `planned`, `ready`, `in_progress`, `blocked`, `verified`. `Blocked` requires a specific missing dependency and owner; it is never synonymous with complete. Preserve traceability from FIN ID to task to implementation to test evidence.

## 6. Accounting and isolation test contract

These tests are mandatory for relevant packages; adapt the fixtures to the final interfaces. Do not mirror implementation details instead of asserting financial outcomes.

| Risk | Required evidence |
|---|---|
| Organization leak | Same user with different roles in A/B, unrelated user, suspended membership, forged headers, cross-organization foreign keys, cached reads, exports, attachments, portal links and jobs all tested |
| RLS timing/bypass | Trusted context established inside the protected transaction, no pooled-connection leakage, both reads and writes tested as intended app role; missing context denies access |
| Duplicate posting | Simultaneous requests with same key create one source posting; same key/different payload fails; crash/retry does not double-post |
| Concurrent settlement | Two allocations compete for the same outstanding balance and cannot over-apply; locks/retries do not corrupt balances |
| Accidental financial mutation | Posted rows cannot be edited/deleted through API, ORM bulk paths or the app database role; correction preserves the original |
| Period-close race | Close versus posting, backdated correction, revaluation and reopen scenarios produce a consistent result |
| Money precision | Zero/two/three-decimal currencies, fractional quantity/price, discounts, inclusive tax, rounding residual, currency conversion direction and missing-rate behavior |
| Incomplete tax semantics | Compound order, withholding timing, reverse charge, partial recoverability, tax rate changes and country report mappings have explicit expected journal lines |
| Settlement/report history | Partial payment, advance, credits/refunds and later correction reproduce outstanding balances at earlier dates; AR/AP tie to GL |
| Foreign exchange | Invoice recognition, partial/full settlement, period-end revaluation, subsequent settlement and reversal avoid duplicated gains/losses |
| Bank duplication | Matching adds no cash posting; split/group allocations cannot exceed either side; transfers reconcile both sides; ambiguous duplicate imports remain reviewable |
| Stock/assets | Backdated receipt, sale, return, cost correction, transfer, blocked negative stock, depreciation/disposal and asset adjustments tie to valuation and GL |
| Jobs/providers | Duplicate/out-of-order callbacks, invalid signatures, dispatch failure, timeout after provider success, retry exhaustion and recovery do not duplicate money movement |
| Migration/recovery | Fresh install and upgrade from a representative snapshot; rerun-safe imports; trial balance/subledger tie-out; backup restoration with jobs safely resumed |
| Complete UX | Permission variants, org switching, keyboard/accessibility, empty/error/loading states, document previews, and full commercial workflows exercised in browser |

When testing a worker outage, assert the committed document survives and the delivery job can resume. Django's after-commit hooks coordinate transaction completion, but a durable job/outbox is still needed to recover dispatch failure. [Django transaction documentation](https://docs.djangoproject.com/en/dev/topics/db/transactions/)

An initial existing-code regression command, from the repository root, is:

```powershell
Set-Location backend
..\.venv\Scripts\python -m pytest apps\authentication\tests -q
```

After creating the finance test suite, run it and `python manage.py check`, `python manage.py makemigrations --check --dry-run`, fresh/upgrade migration checks, and relevant frontend build/browser checks using the repository's actual environment. Record exact commands and exit codes in each task; do not claim that the examples above were run during this planning task. Isolate test databases from production.

## 7. Coordination when multiple agents are authorized

A coordinator owns the dependency map, API/model contracts, requirement coverage, and integration branch. Each implementing agent receives one concrete task packet and a clear file boundary. Do not assign two agents concurrent edits to the same schema, migration sequence, shared posting engine, or permission contract.

Parallelize only independent work with agreed interfaces. For example, a report query and a document print template can proceed together after their data contracts exist. Settlement correctness cannot be completed against an unspecified posting engine.

Have a separate reviewer inspect money/security changes when agents or human reviewers are available. Reviewers verify evidence and rerun critical checks rather than trusting an implementer's completion statement. The coordinator checks the integrated diff and full requirement coverage before merging. No agent may invent accountant approval, production credentials, provider certification, market requirements, or operational sign-off.

This guide does not itself request spawning agents now. Follow the session's authorization and available tools at implementation time.

## 8. Decisions and blockers

Log choices with date, rationale, requirement impact, and decision owner. Routine implementation choices can be made within the accepted scope. Do not repeatedly ask for approval already given. Escalate actual missing product decisions, incompatible constraints, legal/regulatory validation, or production operations requiring user authorization.

Launch countries, bank/payment providers, retention requirements, and deployment capacity are genuine inputs. Work on independent packages while these are unresolved. Do not guess a country's compliance or declare a blocked integration complete. If changing production targets or deleting required scope becomes necessary, present the concrete trade-off and obtain the user's decision.

**Bank files (2026-09-17):** CSV and XLSX statement import is in. Do not add `.xls`, OFX/QIF, or live feeds until a named bank actually sends that format and support is requested. Extra parsers without a sender are speculative.

Task handoff must state: changed files, completed requirement IDs, executed tests and results, migration impact, user-visible outcome, unresolved blockers, and the next dependency-ready task. Keep task status aligned with that evidence.

## 9. Reusable implementation prompt

Use this text to initiate an implementation session after the product plan is accepted:

> Build the finance product described in `docs/superpowers/plans/2026-09-17-generalized-finance-system.md`. Read `docs/engineering/finance-agent-build-guide.md`, the linked research, repository instructions, and the constitution first. Reinspect the repository and preserve unrelated changes. This is a production product, not an MVP. Reuse Organization/Membership for isolated books and multi-organization users; do not add Entity, Business Center, or UAE-only assumptions. Follow the dependency map, create the next bounded Speckit specification/plan/tasks, and implement only ready tasks within the authorized scope. Use a shared posting engine, immutable posted history, explicit corrections, PostgreSQL-backed isolation/concurrency checks, and complete user workflows. Do not add speculative or redundant features. Do not replace required integrations with stubs or call unfinished modules production-ready. Record actual commands/results and requirement coverage; surface concrete external blockers while continuing independent work. Completion requires the production release gate, not merely passing a subset of tests.
