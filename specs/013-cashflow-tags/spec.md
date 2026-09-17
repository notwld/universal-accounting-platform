# Feature Specification: Cash Flow, Tags, and Comparative Reports

**Feature Branch**: `013-cashflow-tags`

**Created**: 2026-09-17

**Status**: Implemented

**Input**: User description: "yea" — next package is cash-flow / tags / close reports, API only. No screens, SMS, or live bank.

**Requirement coverage**: FIN-08 flat reporting tags; FIN-10 formal cash-flow and comparative periods on existing statements. Year-close posting, FX revaluation, tax packs, and file exports deferred.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Label activity for a department (Priority: P1)

An Accountant creates a reporting tag and puts it on a journal line. Profit and loss and the general ledger can be asked for that tag only. Tags are labels, not a second set of books.

**Why this priority**: FIN-08 is the reporting-organization slice; cash flow reuses the same ledger.

**Independent Test**: Tag one income line; tagged P&L shows that income; untagged P&L still shows the full period.

**Acceptance Scenarios**:

1. **Given** a posted journal with one line tagged and one not, **When** P&L is requested with that tag, **Then** only the tagged line’s accounts appear.
2. **Given** the same books, **When** P&L is requested without a tag, **Then** totals include every posted line in the period.

---

### User Story 2 - Read a cash-flow statement (Priority: P1)

Each account can be classified as cash, operating, investing, or financing. For a period, the statement starts from net income, adjusts for classified balance-sheet movements, and the net change equals the movement in cash-classified accounts.

**Why this priority**: Close cannot finish without a cash-flow that ties to the bank/cash ledger.

**Independent Test**: Opening cash 1,000 vs equity; earn 100 on receivable; collect 80; buy equipment 200 for cash. Operating 80, investing −200, financing 1,000, net change 880 equals cash change.

**Acceptance Scenarios**:

1. **Given** classified accounts and those postings, **When** cash flow is requested for the year, **Then** operating, investing, and financing sum to the change in cash-classified accounts.
2. **Given** an unclassified balance-sheet account, **When** cash flow is requested, **Then** that account is omitted from adjustments (the cash change is still reported so a gap is visible).

---

### User Story 3 - Compare this period to last (Priority: P2)

P&L and the balance sheet accept a comparison period and return the prior figures beside the current ones without a second report type.

**Why this priority**: Close packs include comparative statements; the queries already exist.

**Independent Test**: Current year has income; comparison year is empty; prior net income is 0 and current is unchanged.

**Acceptance Scenarios**:

1. **Given** activity only in 2026, **When** P&L for 2026 is requested with a 2025 comparison, **Then** current net income is unchanged and prior net income is 0.
2. **Given** a balance sheet as of year-end with a prior as-of, **When** both dates are returned, **Then** each side still balances on its own date.

---

### Edge Cases

- A tag from another organization is rejected.
- Cash-flow uses posted journals only.
- Missing from/to on cash flow is rejected like other period reports.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: An organization can create named reporting tags unique per organization.
- **FR-002**: A journal line may carry at most one tag. Posted history is not rewritten.
- **FR-003**: Trial balance, general ledger, and P&L accept an optional tag filter.
- **FR-004**: Accounts may carry a cash-flow class: cash, operating, investing, financing, or none.
- **FR-005**: Cash flow for a period equals net income plus classified non-cash balance-sheet movements (asset increases use cash; liability and equity increases provide cash). Income and expense accounts are not adjusted a second time. Net of sections is reported next to the change in cash-classified accounts.
- **FR-006**: P&L accepts a comparison from/to; balance sheet accepts a comparison as-of. Current figures keep today’s field names; prior figures are nested.
- **FR-007**: No screens. No SMS. No live bank APIs.

### Key Entities

- **Reporting tag**: Org-scoped label on journal lines.
- **Account cash-flow class**: How the account participates in the cash-flow statement.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A tagged P&L excludes untagged activity; the unfiltered P&L still includes it.
- **SC-002**: For the fixture (cash 1,000 opening, 100 earned on receivable, 80 collected, 200 equipment purchased), cash-flow net change equals cash-account change (880).
- **SC-003**: Comparative P&L returns prior net income 0 when the comparison period has no postings, without changing current net income.

## Assumptions

- Indirect cash flow from account classes. Direct method deferred.
- Tags are flat; no tag groups or allocations across tags.
- Year-end close journal, FX revaluation, tax reports, and PDF/CSV/XLSX downloads are later packages.
- Existing P&L/BS JSON keys stay stable; comparison is additive.

## Out of Scope

- UI, SMS, live bank, year-close posting, FX reval, tax packs, report file export, project accounting.
