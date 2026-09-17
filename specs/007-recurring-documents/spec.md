# Feature Specification: Recurring Documents

**Feature Branch**: `007-recurring-documents`

**Created**: 2026-09-17

**Status**: Draft

**Input**: User description: "Phase 5 first slice, API only: recurring invoices, bills, and expenses. One occurrence per schedule date, month-end clamping, pause/resume, catch-up without duplicates. No screens. No reminders, approvals, gateways, or customer portal."

**Requirement coverage**: FIN-03/04 recurring billing and purchases, FIN-11 recurrence. Screens, reminders, bank rules, approvals, payment gateways, and portal deferred.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Recurring invoice drafts (Priority: P1)

An Accountant stores a monthly invoice schedule. Running due dates creates one draft invoice per scheduled day. January 31 then February produces 31 Jan and 28 Feb (or 29 in a leap year), not a missing or doubled February row. Running the same day again creates nothing new.

**Independent Test**: Schedule day 31 from 2026-01-31; run as-of 2026-03-01; two drafts; second run still two.

### User Story 2 - Pause and bills/expenses (Priority: P1)

A paused schedule produces no further documents. A bill schedule creates draft bills. An expense schedule posts one paid expense per date and does not post twice for the same date.

**Independent Test**: Pause before March run; no March invoice. One bill draft and one posted expense; replay is a no-op.

## Requirements

- **FR-001**: A schedule belongs to one organization and is invoice, bill, or expense.
- **FR-002**: Monthly recurrence uses a day-of-month; if that day is absent, use the last day of the month.
- **FR-003**: At most one document per schedule date (unique occurrence). Catch-up fills missed dates up to the run date, then stops.
- **FR-004**: Invoices and bills created from a schedule remain drafts (do not post). Expenses post once through the existing expense engine.
- **FR-005**: Pause stops generation; resume continues from the stored next date.
- **FR-006**: An optional end date stops generation after that date.
- **FR-007**: No screens.

## Success Criteria

- **SC-001**: Two runs on the same as-of date never create a second document for the same schedule date.
- **SC-002**: Day 31 in a 28-day month lands on the 28th.
- **SC-003**: Paused schedules create zero documents while paused.
- **SC-004**: Recurring expenses do not change the trial balance when replayed for an already-posted date.

## Assumptions

- Frequency in this slice is monthly only.
- Organization timezone is used only to interpret a default as-of date; tests pass an explicit as-of.
- Approvals, reminders, email, weekly/yearly cadences, and auto-post of invoices/bills are later.

## Out of Scope

- UI, payment gateways, customer portal, bank rules, multilevel approval, `.xls`/OFX/QIF/live bank feeds.
