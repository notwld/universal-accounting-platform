# Feature Specification: Organization Finance Foundation and Immutable Ledger

**Feature Branch**: `002-org-finance-foundation`

**Created**: 2026-09-17

**Status**: Draft

**Input**: User description: "Build Phase 1 of the generalized finance product: organization-scoped books, finance permissions, trusted isolation, finance setup, chart of accounts, immutable journals, reversals, opening balances, trial balance, and general ledger. Backend and API only — no frontend this slice. Reuse existing Organization and Membership. No Entity or Business Center. No country or UAE defaults. Production quality, not an MVP."

**Requirement coverage**: FIN-01 (access/isolation), FIN-02 (ledger/close foundation), foundation of FIN-06 (base currency), foundation of FIN-10 (trial balance and GL), foundation of FIN-11 (audit and idempotency). FIN-14 screens are explicitly deferred.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Open independent books for an organization (Priority: P1)

An owner of an organization configures that organization's finance books: country, base currency, fiscal calendar, timezone, language/format preferences, and whether tax registration applies. After setup, the organization has its own chart of accounts, document numbering, and period controls. A second organization owned or joined by the same person has completely separate books. Switching organizations changes the entire accounting context.

**Why this priority**: Nothing else in finance is valid until each organization owns an isolated set of books with a locked identity (base currency and calendar).

**Independent Test**: Create two organizations for one user; complete setup on each with different currencies and fiscal year starts; confirm each returns only its own settings and accounts.

**Acceptance Scenarios**:

1. **Given** an authenticated user who is Owner of organization A with no finance setup, **When** they complete finance setup with USD and a January fiscal year, **Then** A has independent books with that base currency and calendar, and no other organization's data is created or altered.
2. **Given** the same user is Owner of organization B, **When** they complete finance setup with EUR and a July fiscal year, **Then** B has its own books; A remains USD/January; each organization can independently use the same account codes and document numbers.
3. **Given** organization A already has at least one posted journal, **When** someone attempts to change A's base currency, **Then** the change is rejected and the original currency remains.
4. **Given** a user with no finance grant on organization C, **When** they request C's finance settings or chart, **Then** no finance data is returned.

---

### User Story 2 - Grant and enforce finance access (Priority: P1)

An owner (or Finance Admin) assigns organization-level finance roles and custom roles built from action permissions. A generic membership does not confer finance access. The same person may be Owner in one organization, Accountant in another, and Viewer in a third; those grants never transfer. Location-restricted membership does not imply organization-wide finance access.

**Why this priority**: Isolation and least privilege must exist before any journal can be written.

**Independent Test**: One user with different roles in A and B; a location-only member; a suspended member. Each permission variant is exercised against the same finance operations.

**Acceptance Scenarios**:

1. **Given** a user whose only membership role is a generic application member, **When** they attempt any finance read or write, **Then** access is denied.
2. **Given** a user who is Accountant in A and Viewer in B, **When** they post a journal while A is selected, **Then** the journal is stored only in A; **When** they attempt to post while B is selected, **Then** posting is denied and they may only read B's permitted reports.
3. **Given** a membership restricted to a location in organization A without an explicit organization-level finance grant, **When** they request A's journals or chart, **Then** access is denied.
4. **Given** an Owner changing another member's finance role, **When** the change requires additional authentication and succeeds, **Then** the new grants take effect immediately, prior grants no longer apply, and the change is audited.
5. **Given** a Sales Clerk, **When** they attempt to post a manual journal or reopen a period, **Then** those actions are denied.

---

### User Story 3 - Record, inspect, and reverse posted journals (Priority: P1)

An Accountant records a balanced manual journal against the selected organization's chart, including opening-balance journals. Once posted, the entry cannot be edited or deleted. A mistake is corrected by a linked reversal that preserves the original. Duplicate or retried submissions do not create a second posting.

**Why this priority**: The immutable ledger is the accounting kernel every later document must use.

**Independent Test**: Post a balanced journal, attempt mutation, reverse it, retry the original request, and inspect trial balance and general ledger.

**Acceptance Scenarios**:

1. **Given** a draft balanced journal (debits equal credits in base currency) in an open period, **When** an authorized Accountant posts it, **Then** a published journal exists, an audit event is recorded, and trial balance and general ledger reflect the lines.
2. **Given** a journal whose debits do not equal credits, **When** posting is attempted, **Then** nothing is written (no journal, no lines, no audit posting event) and a useful error is returned.
3. **Given** a posted journal, **When** anyone attempts to change or delete its posted fields or lines, **Then** the attempt is rejected and the original remains intact.
4. **Given** a posted journal, **When** an authorized Accountant reverses it with a reason, **Then** a new reversing journal is posted, it references the original, the original is unchanged, and a second reversal of the same original is rejected.
5. **Given** a posting request with an idempotency key that already succeeded, **When** the same content is submitted again, **Then** the original result is returned and no second journal is created. **When** different content uses that same key, **Then** the request is rejected.
6. **Given** two concurrent posting requests that would duplicate the same journal, **When** both complete, **Then** exactly one published journal exists.

---

### User Story 4 - Lock periods and keep history inspectable (Priority: P2)

An Accountant reviews trial balance and general ledger for a period, then locks that period. Posted activity cannot be backdated into a locked period until an authorized user reopens it with a reason. Reports show only published entries.

**Why this priority**: Close controls and inspectable history are required to trust the books before sales and purchases are added.

**Independent Test**: Post into an open period, lock it, attempt a backdated post, reopen with a reason, then confirm trial balance and GL agree.

**Acceptance Scenarios**:

1. **Given** an open period containing posted journals, **When** an Accountant locks it, **Then** further posts and reversals dated in that period are rejected.
2. **Given** a locked period, **When** an authorized user reopens it with a reason, **Then** the reopen is audited and posting into that period is allowed again.
3. **Given** a close in progress and a concurrent backdated post to the same period, **When** both complete, **Then** the books remain consistent: either the post is in an open period or the close succeeded and the post was rejected — never both.
4. **Given** draft journals, **When** trial balance or general ledger is requested, **Then** drafts are omitted and only published entries appear.

---

### User Story 5 - Operate through the finance API without a client app (Priority: P2)

Authorized integrators and internal operators complete organization finance setup, membership grants, chart maintenance, journal posting, reversals, period lock/reopen, and report retrieval through the versioned finance API. Resource endpoints edit drafts; named actions perform submit/post/reverse/close. Errors are stable and actionable.

**Why this priority**: This slice delivers no screens; the API is the user-facing product until a later frontend package.

**Independent Test**: Drive the P1/P2 stories solely via documented API requests with membership context, including permission-denied and cross-organization cases.

**Acceptance Scenarios**:

1. **Given** a valid membership and finance grant, **When** the caller performs setup, chart, post, reverse, and report operations, **Then** each succeeds or fails with a stable error code (closed period, imbalance, insufficient permission, idempotency conflict, cross-organization reference).
2. **Given** a stale document version, **When** the caller submits an update or post, **Then** the write is rejected and no partial posting occurs.
3. **Given** organization A selected, **When** the caller references an account, period, or journal that belongs to B, **Then** the operation fails and no B data is returned.

---

### Edge Cases

- Suspended or removed membership: all finance access for that organization is denied even if roles remain on the record.
- User belongs to A and B; cached or header-forged organization identifiers never grant the other organization's books.
- Missing trusted organization context: finance reads and writes are denied.
- Opening-balance journal in a new organization: allowed in an explicitly designated opening period; control accounts may be used only through that validated opening workflow.
- Zero-decimal, two-decimal, and three-decimal base currencies: amounts quantize to that currency's precision; unexplained residuals fail posting.
- Journal line with both debit and credit, negative amount, or neither: rejected; no partial save.
- Account inactive or missing from the selected organization: posting is rejected.
- Retry after a crash following a successful post: idempotency returns the original journal, not a duplicate.
- Background job touching finance data without trusted context inside the same unit of work: access is denied.
- Support or superuser paths: none in this slice; no cross-organization finance access for ordinary users.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Each organization MUST own an independent set of books, including finance settings, chart of accounts, numbering, periods, journals, reports, and audit trail. Server MUST assign organization identity from validated membership context; clients MUST NOT supply a trusted owner id.
- **FR-002**: Finance setup MUST capture country, base currency, fiscal year start, timezone, language/format preferences, and whether tax registration applies, without defaulting to a specific country, currency, or tax regime.
- **FR-003**: Base currency MUST NOT change after the organization has any posted journal. Fiscal calendar and timezone changes MUST NOT rewrite posted history.
- **FR-004**: A user MAY belong to multiple organizations with different finance roles in each; permissions MUST NOT transfer across organizations.
- **FR-005**: Preset organization-level roles MUST include Owner, Finance Admin, Accountant, Sales Clerk, Purchasing Clerk, Approver, and Viewer, plus configurable custom roles composed of action permissions. A generic application member role MUST grant no finance access by itself.
- **FR-006**: Action permissions MUST be enforced server-side for at least: manage finance access, configure finance settings, maintain chart of accounts, create journals, post documents/journals, reverse journals, view reports, lock periods, and reopen periods.
- **FR-007**: Location-restricted membership MUST NOT confer organization-wide finance access. Finance grants are organization-level and explicit.
- **FR-008**: Related finance records referenced together MUST belong to the same organization. Cross-organization references MUST fail without leaking the foreign record.
- **FR-009**: Trusted user and organization context MUST be established after authentication and inside the same unit of work as protected reads and writes, including background jobs. Missing or untrusted context MUST deny access.
- **FR-010**: Finance data isolation MUST protect both reads and writes, including exports and later attachments when those surfaces exist. Isolation MUST be proven with real multi-connection tests against the production-class database engine; a substitute engine does not satisfy this requirement.
- **FR-011**: Owners and Finance Admins MUST be able to invite or add members to the organization and assign finance roles. Privileged access changes and sensitive operations MUST require additional authentication using the existing identity provider. The preparer of an access change cannot silently grant themselves Owner.
- **FR-012**: Document and journal numbers MUST be unique within organization, document type, and series; issued numbers MUST NOT be reused; allocation MUST be safe under concurrent requests.
- **FR-013**: Authorized users MUST maintain a chart of accounts for the selected organization (code, name, type/classification, status). Accounts are never shared across organizations.
- **FR-014**: Authorized users MUST create draft journals and post balanced journals, including opening-balance journals, using only accounts of the selected organization.
- **FR-015**: Published journal debits MUST equal credits in base currency. Each line MUST have a valid nonnegative debit or credit, not both. Unexplained imbalance MUST reject the entire posting with no partial writes.
- **FR-016**: Posted journal headers and lines MUST NOT be updated or deleted. Corrections MUST use a linked reversal that carries actor and reason and MUST NOT be duplicated by retry.
- **FR-017**: Posting MUST be idempotent per organization, operation, and request key. Identical replay returns the existing result; changed content with the same key is rejected; concurrent duplicates yield one published journal.
- **FR-018**: Period close and posting MUST share a locking strategy so a close cannot race a backdated post. Reopening MUST be audited. Posting or reversing into a closed period MUST be rejected unless that period is explicitly reopened.
- **FR-019**: Monetary amounts MUST be exact decimal values quantized to each currency's precision. Approximate binary fractions and a universal two-decimal rule are forbidden.
- **FR-020**: Trial balance and general ledger MUST be available for the selected organization, using only published entries, with drill-through from a balance to the contributing journals.
- **FR-021**: Draft journals MAY show a posting preview but MUST contribute nothing to trial balance, general ledger, or any financial total.
- **FR-022**: Every successful post, reverse, period lock, period reopen, and privileged access change MUST write an audit event that records actor, organization, action, and enough identifiers to reconstruct the change. Audit events MUST NOT be editable by ordinary finance APIs.
- **FR-023**: Draft journals are updated separately from posting, reversing, locking, and reopening, which are explicit actions. Stale edits MUST be rejected. Failures MUST use stable, distinguishable reasons for closed period, imbalance, insufficient permission, conflicting retry, and cross-organization reference.
- **FR-024**: Direct manual postings to accounts designated as AR/AP control accounts MUST be restricted to validated opening or adjustment workflows.
- **FR-025**: This feature MUST be complete as an API and service vertical: persistence, permissions, business rules, errors, audit, and tests. It MUST NOT include end-user screens, empty navigation, placeholder pages, or mocked production integrations.

### Key Entities

- **Organization**: Existing tenant. One organization is one set of books. Not an Entity or Business Center.
- **Membership**: Existing participation record. Extended with organization-level finance grants; generic membership is not a finance role.
- **Finance role / permission grant**: Organization-scoped preset or custom role composed of action permissions.
- **Finance settings**: Per-organization country, base currency, fiscal calendar, timezone, format preferences, tax-registration flag.
- **Currency reference**: Shared read-only currency definitions (code, precision). User-owned rates and accounts are never shared.
- **Account**: Organization-owned chart entry used by journals.
- **Document sequence**: Organization-owned numbering series for journals and later document types.
- **Fiscal period lock**: Organization-owned open/locked state for a dated period, with reopen reason/history.
- **Journal entry and lines**: The authoritative general ledger. Posted snapshots are immutable; reversals are separate linked entries.
- **Opening balance journal**: A constrained journal used to start books; not a second ledger.
- **Idempotency record**: Organization-scoped key for posting and other sensitive writes.
- **Audit event**: Append-only record of security- and accounting-relevant actions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An Owner can take a new organization from no books to a posted opening-balance journal and a matching trial balance in one sitting (under 15 minutes) without using a graphical application.
- **SC-002**: In a two-organization test, a user with distinct roles in each cannot read or write the other organization's journals, accounts, settings, or reports in 100% of attempted cross-access cases (including forged identifiers, cached context, and jobs).
- **SC-003**: Duplicate concurrent posting with the same idempotency key produces exactly one published journal in 100% of trials; imbalanced posting produces zero persisted journal artifacts in 100% of trials.
- **SC-004**: After posting and reversing a sample set (including opening balances), trial balance debits equal credits, general ledger lines match the published journals, and the original posted entries remain byte-for-byte unchanged except for reversal linkage metadata allowed by the spec.
- **SC-005**: Period lock then backdated post is rejected in 100% of trials; concurrent close versus post never yields both a locked period and a new posted entry dated in that period.
- **SC-006**: Currency-precision fixtures for 0, 2, and 3 decimal currencies post and report using that currency's precision with no silent two-decimal rounding.
- **SC-007**: A Viewer or Sales Clerk cannot post or reverse journals, and a location-only member without an organization finance grant cannot read finance data, in 100% of permission tests.
- **SC-008**: Operators can retrieve trial balance and general ledger for a sample month and identify every contributing posted journal without using database consoles.

## Assumptions

- Existing identity, organization, membership, and context-switching capabilities remain the only tenancy system. This feature extends them for finance; it does not replace them.
- Accrual accounting is the bookkeeping basis. Cash-basis statutory reporting is out of scope for this slice.
- No frontend, native mobile app, or visual navigation shell ships in this feature. A later package will add screens against these APIs.
- Country packs, e-invoicing, filing, bank feeds, and payment gateways are out of scope. Geography and currency remain configurable without implying a supported filing regime.
- Sales, purchasing, banking, inventory, assets, recurring documents, approvals beyond access changes, customer portal, and imports of historical transactions are out of scope. Sequences and permission names may exist so later documents can reuse them, but those documents are not implemented here.
- Shared currency/country reference data may be read-only and global. Tax codes, accounts, and user-owned configuration are per organization.
- Opening balances are recorded as journals, not as a parallel balance store.
- Manual journals in this slice are recorded in the organization's base currency. Foreign-currency journals and realized/unrealized FX are a later package; the money precision rules still apply now.
- Support/cross-organization break-glass access is not introduced.
- Production launch of the overall finance product still requires later packages and the plan's general-availability gate. Completing this feature does not authorize calling the product generally available.

## Out of Scope

- Any user interface, including organization switcher chrome, setup wizards, chart/journal screens, and empty module navigation.
- Entity, Business Center, Location-as-books-owner, consolidation, and intercompany accounting.
- UAE/Dubai/AED/VAT defaults, mandatory TRN, or emirate selectors.
- Copying the CIA finance application or migrating CIA production data.
- Payroll, manufacturing, lending, crypto, budgeting suites, AI assistants, and universal custom-field engines.
