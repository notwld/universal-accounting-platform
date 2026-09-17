# Feature Specification: Phase 5 Controls and Statement Formats

**Feature Branch**: `010-phase5-controls`

**Created**: 2026-09-17

**Status**: Draft

**Input**: User description: "Implement email, regex/amount-range rules, auto-apply on import, .xls/OFX/QIF/feeds (no frontend). Next Phase 5 leftovers: saved filters, exception queue, multilevel/threshold approvals."

**Requirement coverage**: FIN-03 reminders email, FIN-05 statement formats and file feeds, FIN-11 filters/exceptions/approvals. Screens, Plaid/TrueLayer, payment gateways, and portal deferred.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reminder email (Priority: P1)

When a reminder is created for an unpaid posted invoice and the customer has an email address, the organization sends one reminder email. Missing address or send failure is recorded in the exception queue; the reminder row still exists. Replay does not send a second email.

**Independent Test**: Contact with email; run reminders → one message; run again → still one message. Contact without email → one open exception, no message.

### User Story 2 - Richer bank rules and auto-apply (Priority: P1)

Rules may use regex or contains-text and optional signed amount min/max. Importing a statement auto-applies rules to unmatched new lines.

**Independent Test**: Regex `fee$` with amount −20..−10 auto-categorizes −15 "Bank fee" on import; −60 "Vendor pay" is untouched.

### User Story 3 - Extra statement files and URL feeds (Priority: P1)

The accountant imports `.xls`, OFX, or QIF into the same bank lines as CSV/XLSX. A feed is a stored HTTPS URL of one of those files; fetching it imports through the same path. Private/loopback URLs are rejected.

**Independent Test**: OFX with one −15 line imports; QIF same; `.xls` same columns; feed fetch of OFX creates the line once; second fetch reports duplicate.

### User Story 4 - Saved filters (Priority: P2)

An Accountant saves a named filter (resource + params) and lists invoices using that saved filter id.

**Independent Test**: Save invoice filter `status=posted`; GET invoices with that id returns only posted invoices.

### User Story 5 - Exception queue (Priority: P2)

Failed reminder mail, failed feed fetch, and failed rule categorize appear as open exceptions. Resolving one with a reason closes it.

**Independent Test**: Reminder with no email creates an open exception; resolve → status resolved.

### User Story 6 - Threshold and two-level approval (Priority: P1)

When approval is required, documents below the amount threshold post without approval. Documents at or above it need `approval_levels` distinct approvers (default 1). Same-user double approve does not satisfy two levels.

**Independent Test**: Threshold 200: total 110 posts without submit. Levels 2: first approver leaves pending; second distinct approver approves; then post.

## Requirements

- **FR-001**: Reminder run sends at most one email per reminder to the contact email; failures enqueue exceptions.
- **FR-002**: Bank rules support contains or regex, optional signed amount range, and auto-apply on import/feed fetch.
- **FR-003**: Statement import accepts CSV, XLSX, XLS, OFX, QIF into the same line rows. Duplicate fingerprint unchanged.
- **FR-004**: Bank feed stores an HTTPS URL + bank account; fetch imports; SSRF (private/loopback/link-local) is rejected. No card-network/open-banking provider client.
- **FR-005**: Saved filters are org-scoped name + resource + params; list endpoints honor `saved_filter_id` for invoice, bill, and bank-line.
- **FR-006**: Exception queue is org-scoped open/resolved records with kind and reason.
- **FR-007**: `approval_threshold` (0 = all) and `approval_levels` (≥1). Distinct approvers required per level. SoD unchanged.
- **FR-008**: No screens.

## Success Criteria

- **SC-001**: A reminder with an email address produces exactly one outbound message; replay produces zero more.
- **SC-002**: Auto-apply on import categorizes a matching fee once and does not recategorize on re-import.
- **SC-003**: OFX, QIF, and XLS each produce the same line fingerprint as the equivalent CSV.
- **SC-004**: A private feed URL is rejected; a public HTTPS fetch imports through the shared parser.
- **SC-005**: Saved filter returns only matching invoices.
- **SC-006**: Below-threshold invoice posts without approval; two-level invoice needs two distinct approvers.

## Assumptions

- Email uses the existing application SMTP (not Clerk).
- Amount range compares the signed statement amount.
- Regex is case-insensitive search; invalid patterns are rejected at save.
- Feeds are file URLs, not Plaid/TrueLayer/Yodlee.

## Out of Scope

- UI, payment gateways, customer portal, open-banking aggregators, split/group matching, SMS.
