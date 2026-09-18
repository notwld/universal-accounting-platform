# Feature Specification: Finance Backend Production Remediation

**Feature Branch**: `014-production-remediation`

**Created**: 2026-09-18

**Status**: Implemented (P1 B0–B7 and named P2 B8/B10). Remaining B9/B11–B13 operational packages stay listed, not claimed complete.

**Input**: Implement `docs/engineering/finance-backend-production-remediation.md`. No frontend. Country-neutral core. One organization is one set of books.

**Requirement coverage**: Repair P1 book-corruption and isolation defects (B0–B7), then the two named P2 ledger defects (trial balance semantics, complete ISO 4217 catalogue). Remaining B9/B11–B13 operational packages stay listed, not claimed complete.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Isolation and atomic commands (Priority: P1)

An Accountant in organization A cannot attach B’s contacts, invoices, or accounts to A’s documents. A failed post leaves no draft, stock move, or payment. PostgreSQL tests prove row isolation when a database is available.

**Independent Test**: Valid ID from org B used on an A credit/payment/item is `cross_organization` and creates no row.

### User Story 2 - Credits return only what was credited (Priority: P1)

A partial credit against a tracked invoice restores only the credited quantity at original issue cost. A price-only credit moves AR/revenue and no stock.

**Independent Test**: Bill 10, sell 4, credit quantity 1 → stock 7 not 10.

### User Story 3 - Quantity, idempotency, refunds, bank evidence (Priority: P1)

Stock quantity is not rounded to currency decimals. Idempotency collisions remain queryable. Refunds lock the payment. Identical rows inside one statement are kept; a second overlapping import is reviewable. Reconciliation cannot complete while statement lines are still imported/unresolved.

**Independent Test**: 1.5 units on a JPY org remain 1.5; two same-day fees in one file both exist; unresolved recon fails.

## Requirements

- **FR-001**: Foreign keys from requests resolve with `organization=org` before insert.
- **FR-002**: Create-and-post commands run in one transaction; rejection leaves no command-owned rows.
- **FR-003**: Credit lines may reference a source invoice/bill line, quantity, and price-only flag; stock reverses only credited quantity.
- **FR-004**: Quantity uses an independent scale from money.
- **FR-005**: Idempotency insert uses a savepoint; the same key returns the original command result.
- **FR-006**: Refund/allocation capacity is recomputed under a payment lock inside the transaction.
- **FR-007**: Bank fingerprint uniqueness does not drop in-file repeats; cross-file matches are review candidates. Identical file bytes replay.
- **FR-008**: Reconciliation completes only when period statement lines are matched or categorized and opening + statement net equals closing; book balance is recorded.
- **FR-009**: Trial balance returns opening, period, and closing debit/credit.
- **FR-010**: Currency catalogue is a complete active ISO 4217 seed (not 20 rows).
- **FR-011**: No screens, SMS, live bank clients, Entity, or Location-as-books-owner.

## Success Criteria

- **SC-001**: Cross-org foreign IDs never persist a document.
- **SC-002**: Partial stock credit does not reverse the whole source document.
- **SC-003**: In-file duplicate bank rows both persist; unresolved reconciliation is rejected.
- **SC-004**: Trial balance closing equals opening plus period movement.

## Assumptions

- PostgreSQL isolation tests skip when the suite is not on PostgreSQL; the production gate requires Postgres.
- Year-close posting, FX revaluation packs, import dry-run, STRIDE expansion, and ops runbooks are follow-on packages in the same guide.

## Out of Scope

- UI, consolidation, country packs, Plaid, SMS.
