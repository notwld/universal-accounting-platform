# Feature Specification: Banking and Financial Reports

**Feature Branch**: `006-banking-reports`

**Created**: 2026-09-17

**Status**: Draft

**Input**: User description: "Phase 4 banking and reports, API only: CSV bank-statement import with duplicate review, match statement lines to existing customer/vendor payments without a second cash journal, categorize unmatched lines, record a reconciliation, and expose P&L and balance sheet from the ledger. No screens. No inventory, country packs, or FX closing revaluation in this slice."

**Requirement coverage**: FIN-05 (import, duplicate review, 1:1 match, categorization), FIN-10 (P&L, balance sheet). Screens, feeds, grouped/split matching, transfers, and period-end FX revaluation deferred.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Import a statement without duplicating cash (Priority: P1)

An Accountant imports a CSV or XLSX of bank lines against a cash/bank GL account. Duplicate rows (same date, amount, description for that organization) are rejected or skipped as duplicates. Import does not post.

**Independent Test**: Import three lines; re-import the same file; second import reports duplicates and does not add rows.

### User Story 2 - Match or categorize (Priority: P1)

A statement inflow matching a customer receipt is matched: no new journal. An unmatched outflow is categorized to an expense account: one journal Dr expense Cr bank. Matching twice is rejected.

**Independent Test**: Pay a vendor 60, import -60, match; import a -15 fee, categorize to expense; GL bank equals statement activity.

### User Story 3 - Reconcile and read P&L / balance sheet (Priority: P1)

After matches/categories, the Accountant completes a reconciliation with opening and closing statement balances. P&L for a period and a balance sheet as-of are produced from posted journals only.

**Independent Test**: Opening 0, lines net to 45, closing 45 completes; P&L shows the categorized expense; BS cash matches the bank GL.

## Requirements

- **FR-001**: Statement lines are organization-scoped and tied to one GL cash/bank account.
- **FR-002**: Duplicate fingerprint (org + account + date + amount + description) MUST not create a second line.
- **FR-003**: Matching MUST NOT post. Categorization MUST post through the shared engine and MUST NOT hit control accounts.
- **FR-004**: Completed reconciliation records opening, closing, and that they agree with imported lines; reopen requires a reason.
- **FR-005**: P&L and balance sheet MUST reuse posted journal lines (same source as trial balance).
- **FR-006**: No screens.
- **FR-007**: Import MUST accept CSV and XLSX with columns `date`, `amount`, `description` (amount signed; positive = inflow).

## Success Criteria

- **SC-001**: Re-importing an identical CSV or XLSX does not duplicate lines.
- **SC-002**: A matched payment does not change the trial balance; a categorized fee does, once.
- **SC-003**: Reconciliation complete only when opening + line net = closing.
- **SC-004**: P&L and BS agree with trial balance classifications for the same dates.

## Assumptions

- CSV or XLSX columns: `date,amount,description` (amount signed; positive = inflow). First worksheet for XLSX.
- Bank account is an existing finance Account (asset), not a second bank master.
- Split/group matching, live feeds, FX revaluation, `.xls`, OFX/QIF, and CSV export of reports are later. Add `.xls`, OFX/QIF, or live feeds only when a named bank actually sends that format.

## Out of Scope

- UI, payment gateways, OFX/QIF, transfers as a special document type, year-end FX reval, migration cutover.
