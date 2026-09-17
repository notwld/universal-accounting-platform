# Feature Specification: Cadences, Auto-Post, Reminders, Approvals

**Feature Branch**: `008-automation-approvals`

**Created**: 2026-09-17

**Status**: Draft

**Input**: User description: "Do not skip APIs for weekly/yearly cadences, auto-posting invoices/bills, reminders, and approvals. Leave screens. Then next task."

**Requirement coverage**: FIN-03/04/11 recurrence cadences, auto-post, reminders, document approval with separation of duties. Screens, email delivery, gateways, and portal deferred.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Weekly and yearly schedules; auto-post (Priority: P1)

An Accountant creates a weekly invoice schedule and a yearly bill schedule. Running due dates creates one document per occurrence date. Auto-post on an invoice schedule posts the invoice (no second document on replay).

**Independent Test**: Weekly from a Monday, run 8 days later → two invoices. Yearly 29 Feb from 2024-02-29, run 2025-03-01 → 2024-02-29 and 2025-02-28. Auto-post invoice has a journal; replay does not add another.

### User Story 2 - Approval then post (Priority: P1)

When document approval is required, posting a draft invoice is rejected until another user with approve permission approves it. The preparer cannot approve their own invoice unless self-approve is enabled. Rejection returns the invoice to draft.

**Independent Test**: Require approval; clerk submits; clerk approve fails; approver rejects then clerk resubmits; approver approves; post succeeds.

### User Story 3 - Reminders for open invoices (Priority: P1)

An Accountant defines a reminder rule (days before due, including 0 = due date). Running reminders for that as-of date creates one reminder per matching unpaid posted invoice and does not duplicate on replay.

**Independent Test**: Posted invoice due 10 Jun, rule 0 days; run 10 Jun creates one; run again still one.

## Requirements

- **FR-001**: Recurring frequency is monthly, weekly, or yearly. Weekly uses weekday; yearly uses month and day with last-day clamping; monthly keeps day-of-month clamping.
- **FR-002**: Auto-post on invoice/bill schedules posts through the existing engine with the same one-occurrence uniqueness.
- **FR-003**: Optional organization setting requires invoice/bill approval before post. Approver cannot be the preparer unless self-approve is enabled.
- **FR-004**: Submit, approve, and reject are recorded. Editing lines after submit returns the document to draft.
- **FR-005**: Reminder rules select unpaid posted invoices/bills by due date offset. Run is idempotent per rule+document+due date.
- **FR-006**: No screens. No email send.

## Success Criteria

- **SC-001**: Weekly and yearly runs never create two documents for the same schedule date.
- **SC-002**: Auto-post replay does not change the trial balance.
- **SC-003**: With approval required, an unapproved draft cannot post.
- **SC-004**: A reminder run for the same as-of date is a no-op the second time.

## Assumptions

- Weekday uses Monday=0 … Sunday=6.
- Auto-post is standing authorization and does not wait for per-document approval.
- Reminders are API queue records, not mail.

## Out of Scope

- UI, email/SMS, payment gateways, customer portal, bank feeds, multilevel approval chains beyond one approver, `.xls`/OFX/QIF.
