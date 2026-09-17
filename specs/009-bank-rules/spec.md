# Feature Specification: Bank Rules

**Feature Branch**: `009-bank-rules`

**Created**: 2026-09-17

**Status**: Draft

**Input**: User description: "Next Phase 5 task after cadences/auto-post/reminders/approvals: configurable bank rules API. Leave screens. Do not add .xls, OFX/QIF, or live feeds."

**Requirement coverage**: FIN-05 bank rules, FIN-11 automation. Screens, split/group matching, transfers, feeds deferred.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Save a description rule (Priority: P1)

An Accountant stores a rule: if an unmatched statement line's description contains a phrase, categorize it to a chosen expense or income account. Inactive rules do nothing.

**Independent Test**: Create a rule for "bank fee" to purchases; list returns it.

### User Story 2 - Apply rules to unmatched lines (Priority: P1)

The Accountant runs rules after matching payments. Matching leftover lines are categorized through the existing categorize path (one journal per line). Already matched or categorized lines are skipped. Running apply again posts nothing extra.

**Independent Test**: Import "Bank fee" −15 unmatched and a matched −60 payment; apply categorizes only the fee; replay leaves journal count unchanged.

### User Story 3 - First matching rule wins (Priority: P1)

When two active rules match the same line, the lower priority number is used. An outflow-only rule does not match an inflow.

**Independent Test**: Priority 1 "fee"→purchases and priority 2 "fee"→another expense; apply uses purchases. An inflow "fee refund" is ignored by an outflow rule.

## Requirements

- **FR-001**: A rule is organization-scoped: contains-text (case-insensitive), target account, optional direction (any/inflow/outflow), integer priority (lower first), active flag.
- **FR-002**: Apply categorizes unmatched imported lines only, using the existing categorize posting (no second cash journal, no control accounts).
- **FR-003**: Apply is idempotent: already matched/categorized lines and replay create no extra journals.
- **FR-004**: Target account must belong to the organization, be active, and not be a control account.
- **FR-005**: No screens. No auto-apply on import (match payments first).

## Success Criteria

- **SC-001**: One apply of a matching rule categorizes the unmatched fee once.
- **SC-002**: A second apply does not change the trial balance.
- **SC-003**: A matched payment line is never recategorized by a rule.
- **SC-004**: When two rules match, the lower priority number determines the account.

## Assumptions

- Contains-text is a case-insensitive substring of the statement description.
- Direction: inflow = amount > 0, outflow = amount < 0, any = both.
- Apply is an explicit run, like reminders/run, not an import side effect.

## Out of Scope

- UI, regex, amount ranges, contact/tax on rules, split/group matching, auto-apply on import, `.xls`/OFX/QIF/live feeds, gateways.
