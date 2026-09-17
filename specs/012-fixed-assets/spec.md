# Feature Specification: Fixed Assets

**Feature Branch**: `012-fixed-assets`

**Created**: 2026-09-17

**Status**: Implemented

**Input**: User description: "yea do it" — next package is FIN-09 fixed assets (API only): register, capitalization, straight-line depreciation, write-down, disposal, ledger tie-out. No screens, SMS, or live bank.

**Requirement coverage**: FIN-09 asset register, capitalization, depreciation, impairment/adjustment, disposal, register agrees with asset/depreciation accounts. Screens, SMS, live bank, declining-balance, component accounting deferred.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Put an asset on the books (Priority: P1)

An Accountant records a machine that cost 1,200, residual 0, twelve-month life, in service 1 January. Capitalizing posts the cost against cash (or another non-inventory funding account). The register shows cost 1,200 and net book value 1,200.

**Why this priority**: Nothing else works without a capitalized register row.

**Independent Test**: Capitalize 1,200; register NBV 1,200; cost account net 1,200.

**Acceptance Scenarios**:

1. **Given** books with a cost account, accumulated depreciation account, expense account, and cash, **When** the accountant capitalizes a 1,200 asset with a 12-month life, **Then** the register lists it as active with cost 1,200 and NBV 1,200, and the cost account increases by 1,200 with cash decreasing by 1,200.
2. **Given** a capitalized asset, **When** capitalize is retried with the same idempotency key, **Then** no second journal is posted.

---

### User Story 2 - Charge monthly depreciation (Priority: P1)

The same machine is depreciated straight-line: 100 per month. Running depreciation through 28 February posts January and February. A second run through the same date posts nothing extra. Net book value is 1,000.

**Why this priority**: The register is useless unless it wears down on a schedule.

**Independent Test**: After capitalization, depreciate through February; accum 200; NBV 1,000; rerun is silent.

**Acceptance Scenarios**:

1. **Given** the 1,200 / 12-month asset in service 1 January, **When** depreciation is run through 28 February, **Then** expense 200 and accumulated depreciation 200 are posted, NBV is 1,000.
2. **Given** that run already succeeded, **When** it is run again through 28 February, **Then** no additional charge is posted.
3. **Given** remaining depreciable amount is smaller than a full month (last period), **When** that month is charged, **Then** the charge equals the remainder so NBV does not fall below residual.

---

### User Story 3 - Write down, dispose, and tie out (Priority: P2)

The accountant can write the asset down (extra accumulated depreciation). Disposing on 1 March for proceeds 950 against cash posts the loss (or gain) and clears cost and accum so the register NBV of active assets equals the ledger net of those accounts. A second dispose is rejected.

**Why this priority**: Disposal and tie-out are the accountant’s close check; write-down covers impairment without a second module.

**Independent Test**: After two months charged, dispose 1 March proceeds 950; loss 50; active NBV 0; register NBV equals ledger net; second dispose rejected.

**Acceptance Scenarios**:

1. **Given** NBV 1,000 after February, **When** the asset is disposed on 1 March for 950, **Then** March is not charged (no partial months), cost and accum clear, cash increases 950, and a 50 loss is posted.
2. **Given** an active asset, **When** a write-down of 100 is posted, **Then** NBV falls by 100 via extra accumulated depreciation and expense.
3. **Given** a disposed asset, **When** dispose or depreciate is requested again, **Then** the request is rejected and no journal is added.
4. **Given** active assets, **When** the asset register is requested, **Then** the sum of active NBVs equals cost-account net minus accumulated-depreciation-account net (credits on accum).

---

### Edge Cases

- Depreciation does not reduce NBV below residual.
- Zero or negative cost, life, or proceeds-without-an-account is rejected.
- Disposed assets are omitted from the active NBV total.
- Write-down larger than NBV minus residual is rejected.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: An organization can capitalize a named asset with cost, residual, useful life in whole months, in-service date, cost account, accumulated depreciation account, expense account, and a credit/funding account.
- **FR-002**: Capitalization posts cost versus the funding account once; retries with the same key do not double-post.
- **FR-003**: Depreciation is straight-line by calendar month. A month is charged only when that month has fully elapsed relative to the requested through-date (no partial months). Charges are unique per asset per month.
- **FR-004**: Monthly amount is (cost − residual) / life, with the final month taking any remainder. NBV never falls below residual.
- **FR-005**: A write-down posts extra accumulated depreciation and expense without changing the monthly schedule remaining life, and cannot exceed NBV minus residual.
- **FR-006**: Disposal catch-up-charges complete months before the disposal date, then removes cost and accum, records proceeds if any, and posts the difference as gain or loss. Disposed assets cannot be charged or disposed again.
- **FR-007**: The asset register lists each asset’s cost, accum, NBV, and status, plus a total of active NBVs that agrees with the related ledger accounts.
- **FR-008**: No screens. No SMS. No live bank APIs.

### Key Entities

- **Fixed asset**: One register row for one capitalized item in one organization.
- **Depreciation charge**: One month’s (or write-down’s) amount linked to that asset and a journal.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A 1,200 cost, 12-month, zero-residual asset charges 100 for each of the first two complete months (accum 200, NBV 1,000).
- **SC-002**: Disposing that asset on 1 March for 950 records a 50 loss and leaves active register NBV at 0, matching the ledger.
- **SC-003**: Repeating the same depreciation run or a second dispose does not create another journal.

## Assumptions

- Straight-line monthly only; declining-balance and units-of-production wait.
- No component/split assets; one row is one asset.
- Capitalization is an explicit register action, not inferred from a bill.
- Partial-month proration is out; a month counts only if its last day is on or before the through-date, and for disposal only months that end before the disposal date.
- Write-down is the impairment/adjustment workflow.
- Accounts live on the asset, not as new organization-wide settings.

## Out of Scope

- UI, SMS, Plaid/live bank, FIFO/stock, country tax depreciation methods, revaluation surplus, lease accounting.
