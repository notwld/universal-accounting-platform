# Feature Specification: Period close tails, cutover, webhooks, ops

**Feature Branch**: `015-close-cutover-ops`

**Created**: 2026-09-18

**Status**: Implemented

**Input**: Implement leftover close (accruals/deferrals, unrealized FX reval, close vs backdated post), PDF + accountant golden fixtures, ordered cutover import with openings XOR history, signed outbound webhooks (outbox/retry/DLQ), and CI/ops (owner migrate + `uap_app` tests, two-connection lock tests, load tests, SLO alerts, backup/restore evidence).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Close adjustments and FX reval (Priority: P1)

An accountant posts a reversing accrual or deferral, revalues open foreign AR/AP at period-end, and cannot post into a locked period.

**Independent Test**: Accrual 50 reverses on the next date. EUR invoice 100 at 1.00 revalued at 1.10 moves AR by 10. Locked period rejects a backdated journal.

### User Story 2 - Cutover import (Priority: P1)

A new org imports in order. Openings and historical activity cannot both be posted.

**Independent Test**: Openings mode posts an opening journal; a history journal in that org is rejected. Dry-run writes nothing.

### User Story 3 - Signed webhooks (Priority: P2)

Posted journals enqueue signed deliveries. Failures retry then dead-letter.

**Independent Test**: Delivery body HMAC matches secret. Three failures then dead.

### User Story 4 - Reports and ops (Priority: P2)

Trial balance exports PDF. A reviewed golden month matches expected closings. CI migrates as owner and tests as `uap_app`. SLOs and backup/restore steps are written.

**Independent Test**: `export=pdf` starts `%PDF`. Golden fixture amounts match posted TB. Postgres job file exists with two roles.

### Edge Cases

- Zero outstanding foreign documents: reval posts nothing material.
- Cutover stage out of order is rejected.
- Webhook URL must be http(s).
- Same FX `as_of` replays the existing reval.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Accountant can post an accrual or deferral with a reverse-on date; a reverse command posts the opposite journal.
- **FR-002**: Unrealized FX reval restates open AR/AP to the rate on `as_of`, using FX gain/loss accounts, and reverses the prior open reval first.
- **FR-003**: Posting into a locked period is `period_closed`; a test covers lock then backdated post (Postgres two-connection when available).
- **FR-004**: Trial balance (and other table exports) support PDF.
- **FR-005**: A golden fixture file records expected TB amounts for a canned month and a test asserts them.
- **FR-006**: Cutover import runs stages in order, supports dry-run, and forbids openings XOR history once a mode is chosen.
- **FR-007**: Outbound webhooks store HMAC-signed outbox rows with retry then dead-letter; posting does not HTTP-call the subscriber.
- **FR-008**: CI migrates as the table owner and runs finance tests as `uap_app`; load test asserts a query ceiling; SLO alert rules and backup/restore evidence live in repo docs.

### Key Entities

- **Adjustment**: reversing accrual/deferral tied to two journals.
- **FX revaluation**: one per `as_of`, optional reversal journal.
- **Cutover state**: org mode (openings or history) and last completed stage.
- **Webhook endpoint / delivery**: URL, secret, event, attempts, status.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A reversing accrual nets to zero after reverse-on.
- **SC-002**: Open foreign AR at a higher close rate increases AR by the documented difference.
- **SC-003**: Cutover cannot post both opening balances and history for one org.
- **SC-004**: Failed webhook deliveries reach dead-letter after the documented retry limit.

## Assumptions

- Realized FX on payment already exists; this work is unrealized period-end only.
- Accrual and deferral are the same reversing journal with a kind label (no amortization schedule).
- Golden fixtures are a synthetic reviewed pack, not a live accountant signature.
- SLO alerting is repo alert rules plus a metrics snapshot, not a hosted Grafana stack.
- Backup/restore evidence is a runbook plus a scripted exercise, not a live production restore.

## Out of Scope

- UI, SMS, live bank, jurisdiction tax packs, payment-time WHT, e-invoicing XML, Celery worker farm for webhooks.
