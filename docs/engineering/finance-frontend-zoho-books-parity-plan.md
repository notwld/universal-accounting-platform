# Finance Frontend Product and Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Build a route only after the backend release gates for its workflow pass. The target is a Zoho Books-familiar accounting experience with UAP branding, organization isolation, accessible interaction, and no dead navigation.

**Goal:** Deliver a production web application with Zoho Books-familiar navigation, header, dashboard, accounting workflows, and reporting without exposing incomplete features.

**Architecture:** Use one React application shell around independently owned finance feature areas. The backend remains authoritative for tenant context, permissions, calculations, state transitions, and report snapshots; the browser owns presentation, draft interaction, and organization-safe server-state caching.

**Tech Stack:** Node 20+, React, TypeScript in strict mode, Vite, React Router, TanStack Query, TanStack Table, React Hook Form, Zod, Radix UI primitives, Recharts, Vitest, Testing Library, Playwright, and axe-core.

**Spec:** `docs/superpowers/plans/2026-09-17-generalized-finance-system.md`

**Backend readiness source:** `docs/engineering/finance-backend-production-remediation.md`. If the backend guide and a frontend route conflict, the stricter backend release gate wins.

## Global constraints

- One selected organization is one set of books and is always visible.
- Do not add Entity or Business Center concepts.
- Do not show navigation, buttons, panels, or settings for an incomplete workflow.
- Never perform financial calculations with JavaScript floating-point numbers.
- Meet WCAG 2.2 AA and support responsive, keyboard, screen-reader, and locale-aware use.

**Status:** Future frontend specification  
**Target:** Production web application for small and midsize businesses across industries  
**Stack direction:** Node 20+, React, TypeScript, Vite, a typed API client generated from the backend OpenAPI contract, and a focused component/test stack selected when implementation starts  
**Backend dependency:** `docs/engineering/finance-backend-production-remediation.md`

## 1. Design intent

The frontend should feel immediately familiar to a Zoho Books user: a persistent dark left sidebar, a slim white global header, dense but readable accounting tables, white dashboard cards, blue primary actions, clear orange/red overdue states, and drill-through from every financial summary.

Use the same information hierarchy and dashboard content patterns, while using UAP names, icons, copy, and implementation. Do not copy Zoho trademarks, logos, proprietary illustrations, source code, or exact assets. Independently defined design tokens keep the product maintainable and accessible while preserving the requested visual character.

Official Zoho references used for this plan:

- [Zoho Books Home and dashboard panels](https://www.zoho.com/us/books/help/home/)
- [How Zoho Books Works and module inventory](https://www.zoho.com/us/books/help/getting-started/zoho-books.html)
- [Zoho Books Accountant module](https://www.zoho.com/us/books/help/accountant/accountant.html)
- [Zoho Books reports catalogue](https://www.zoho.com/us/books/help/reports/)
- [Zoho Books module preferences](https://www.zoho.com/en-fr/books/help/settings/preferences.html)
- [Zoho Books custom dashboards](https://www.zoho.com/us/books/help/home/custom-dashboards.html)
- [Official Zoho Books comparison PDF with application shell screenshots](https://www.zoho.com/books/pdf/zohobooks-vs-xero.pdf)

The official dashboard documents Total Receivables, Total Payables, Cash Flow, Income and Expense, Top Expenses, Projects, Bank and Credit Cards, and Account Watchlist. It also provides direct creation actions and report drill-through. These behaviors define the target dashboard below.

## 2. Product and tenancy rules

1. One selected `Organization` is one set of books.
2. A user can switch among organizations they are authorized to access.
3. The selected organization is always visible in the global header.
4. Changing organizations invalidates organization-scoped caches, closes unsafe drafts, and refetches permissions before rendering financial data.
5. Location never selects the books and is not shown as Entity or Business Center.
6. Permission checks come from the backend. Hiding a control is a usability measure, not an authorization control.
7. A module appears in navigation only after its complete backend workflow and UI acceptance gate pass.
8. There are no empty pages, decorative buttons, mocked production amounts, or always-success integration controls.

## 3. Application shell

### 3.1 Desktop layout

- **Left sidebar:** fixed, 224 px expanded and 64 px collapsed; dark navy background; product mark at top; vertical scrolling only inside navigation; collapse control persists per user.
- **Global header:** fixed, 56 px; white background; subtle bottom border; organization switcher on the left; global search centered; quick-create, help, notifications, settings, and user menu on the right.
- **Content canvas:** light gray page background; maximum useful width around 1600 px; responsive gutters of 24–32 px; page title and local actions remain separate from the global header.
- **Drawers and modals:** use right drawers for quick view/quick create and full routes for complex documents. Confirmation dialogs are reserved for irreversible or high-impact actions.

### 3.2 Tablet and mobile

- Under 1024 px, collapse the sidebar and open it as a modal navigation drawer.
- Under 768 px, stack dashboard cards, use responsive tables with a deliberate column priority, and keep primary actions reachable without horizontal scrolling.
- Financial document editing remains a full-page flow. Do not compress complex line-entry grids into unusable card forms; provide a mobile-safe reduced workflow and state unsupported high-complexity editing explicitly if necessary.

## 4. Visual system

These tokens reproduce the current Zoho Books visual character observed in official screenshots without copying brand assets.

```css
:root {
  --shell-sidebar: #1f2937;
  --shell-sidebar-hover: #2b3646;
  --shell-sidebar-active: #344256;
  --shell-header: #ffffff;
  --page-background: #f5f7fa;
  --surface: #ffffff;
  --surface-subtle: #f8fafc;
  --border: #e1e6eb;
  --text-primary: #17212b;
  --text-secondary: #65717d;
  --text-on-dark: #f8fafc;
  --primary: #2498e3;
  --primary-hover: #167fc4;
  --primary-soft: #e8f4fc;
  --positive: #2e9d67;
  --warning: #ffb72b;
  --danger: #ef6b4a;
  --danger-soft: #fff0ec;
  --focus: #65b9ee;
  --shadow-card: 0 1px 3px rgba(20, 34, 50, 0.08);
  --radius-card: 8px;
  --radius-control: 4px;
}
```

### Typography and density

- Use a neutral system sans-serif stack until product typography is selected.
- Default body size: 14 px; table metadata: 12–13 px; page title: 22–24 px; dashboard amount: 28–34 px.
- Use tabular numerals for money, quantity, rates, and report columns.
- Right-align numeric columns and align decimal precision.
- Default table row height: 44 px, with a user-selectable compact 36 px mode for accounting teams.
- Use color plus text/icon; never communicate overdue, success, or exceptions by color alone.

### Component appearance

- Cards use white surfaces, one-pixel neutral borders, small radius, and restrained shadow.
- Primary buttons are solid blue; secondary actions are white with a neutral border; destructive actions are red and require contextual confirmation.
- Statuses use compact semantic badges with text.
- Charts use the primary blue series first, amber for warnings/overdue, green for positive cash/income, and red-orange for expenses or exceptions.

## 5. Target sidebar information architecture

The expanded target mirrors the practical Zoho Books module grouping. Child items are permission-filtered and module-gated.

```text
Home

Items
  Items
  Inventory Adjustments
  Warehouses
  Stock Transfers

Banking
  Bank and Card Accounts
  Imported Statements
  Unmatched Transactions
  Reconciliations
  Bank Rules

Sales
  Customers
  Quotes
  Sales Orders
  Invoices
  Recurring Invoices
  Payments Received
  Credit Notes

Purchases
  Vendors
  Expenses
  Bills
  Recurring Bills
  Purchase Orders
  Payments Made
  Vendor Credits
  Payment Runs

Accountant
  Chart of Accounts
  Manual Journals
  Recurring Journals
  Currency Adjustments
  Period Close
  Fixed Assets
  Exceptions

Reports

Documents

Settings
```

### Navigation rules

- Keep top-level order stable across organizations.
- Hide a whole module when it is disabled or incomplete; do not leave a disabled placeholder.
- Preserve the user's last expanded groups, but automatically reveal the active route.
- Show count badges only for actionable queues such as unmatched bank lines, approval tasks, overdue items, or exceptions. Counts come from one backend summary endpoint.
- `Home`, `Reports`, and `Settings` remain top-level destinations. `Accountant` contains operational accounting workflows rather than every report.
- Projects/Timesheets, customer portal, payment gateways, e-invoicing, and country tax filing appear only after their backend packages and end-to-end workflows pass production gates.

## 6. Global header

From left to right:

1. Sidebar toggle.
2. Organization switcher with organization name, base currency, and role summary. Search supports users with many organizations.
3. Global command/search field with `/` keyboard focus. It searches authorized contacts, documents, accounts, and navigation commands within the selected organization.
4. `+ New` button with permission-filtered actions: invoice, customer payment, bill, expense, vendor payment, journal, bank import, and stock adjustment.
5. Help/documentation menu.
6. Notification/approval queue with unread count.
7. Settings shortcut when permitted.
8. User avatar menu for profile, organization memberships, security sessions, theme, and sign out.

The header must never cache or display data from the previous organization after a switch. During context change, render a clear loading boundary and block financial commands.

## 7. Home dashboard

### 7.1 Header and filters

- Page title `Dashboard`.
- Dashboard selector for `Default Dashboard` and future saved dashboards.
- Date range selector, defaulting to the organization's current fiscal year.
- Cash/accrual selector where the backend supports both bases.
- Configure action visible only when dashboard configuration is functional and permissioned.
- Data freshness timestamp and a refresh action.

### 7.2 Default panel order

1. **Total Receivables**
   - Total unpaid invoices.
   - Current and overdue amounts.
   - Horizontal proportion bar using blue for current and amber/red-orange for overdue.
   - `+ New` menu: invoice, recurring invoice, customer payment.
   - Clicking an amount opens the corresponding AR aging drill-through with the dashboard filters preserved.

2. **Total Payables**
   - Total unpaid bills.
   - Current and overdue amounts.
   - `+ New` menu: bill, recurring bill, vendor payment.
   - Clicking an amount opens AP aging drill-through.

3. **Cash Flow**
   - Beginning cash, incoming, outgoing, and ending cash.
   - Direct-method line or area chart for the selected period.
   - Link to the formal cash-flow statement, which may use the indirect method and must be labeled accordingly.

4. **Income and Expense**
   - Total income and total expenses.
   - Monthly grouped bars or lines.
   - Cash/accrual basis selector when supported.
   - Drill-through to Profit and Loss with matching period and basis.

5. **Top Expenses**
   - Donut chart and ranked legend by expense account.
   - Amount and percentage.
   - Click a segment to open the filtered expense report.

6. **Bank and Credit Cards**
   - Each account's book balance, statement balance, unreconciled count, last import, and last reconciliation.
   - Clear attention state for stale feeds/imports or unexplained differences.
   - Click an account to open its banking workspace.

7. **Account Watchlist**
   - User-selected accounts with current balance, comparison, and cash/accrual basis when meaningful.
   - Manage action routes to Chart of Accounts only after watchlist persistence exists.

8. **Projects**
   - Target parity panel: project, customer, unbilled hours, and unbilled expenses.
   - Keep this panel absent until a complete projects/timesheets backend exists.

### 7.3 Production additions

Add these UAP panels because they expose operational risk without adding a separate module:

- **Tasks requiring attention:** documents awaiting approval, unresolved exceptions, failed recurring runs, import errors, and close blockers.
- **Inventory alerts:** negative-stock attempts, low stock if configured, and inventory-to-GL difference.
- **Close readiness:** current open period, unreconciled accounts, draft documents, and unresolved subledger differences.

Every dashboard number must provide a drill-through route or a plain explanation of how it is calculated. Dashboard APIs return compact aggregates, comparison values, freshness timestamps, permission-aware actions, and drill-through filter descriptors.

## 8. Page patterns

### 8.1 List pages

- Page title, primary create action, saved views, search, filters, export, and column settings.
- Server-side pagination, sorting, filtering, and totals.
- Tabs for meaningful states such as Draft, Awaiting Approval, Posted, Overdue, Paid, and All.
- Bulk actions only when their backend command is atomic, permissioned, and audited.
- Empty states provide one valid next action; they do not advertise unavailable features.
- Row click opens detail. Checkboxes do not compete with row navigation.

### 8.2 Document editor

- Header fields first: counterparty, dates, number/series, currency/rate, reference, terms, warehouse where needed.
- Spreadsheet-like line table: item, description, quantity, unit price, discount, tax, reporting tag, amount.
- Totals panel: subtotal, discount, tax, adjustments, total, base-currency equivalent for foreign documents.
- Attachment area and internal notes.
- Save Draft, Submit, Approve/Reject, Post, and More actions reflect the exact current state and permission.
- Preview shows the journal and stock effect before posting when supported.
- Stale-version conflicts preserve local input and offer a controlled reload/compare path.

### 8.3 Detail page

- Document identity, status, counterparty, amount, outstanding balance, dates, and action bar.
- Tabs: Overview, Payments/Allocations, Journal, Attachments, Activity.
- Immutable posted snapshot and clear linked reversal/credit history.
- Every journal amount drills into the journal entry; every allocation drills into payment and source document.

### 8.4 Banking workspace

- Account rail or selector, statement summary, and tabs for All, Unmatched, Matched, Categorized, Excluded, and Duplicate Review.
- Side-by-side statement line and suggested book matches.
- One-to-one, split, and grouped matching appear only when the backend supports each combination.
- Reconciliation screen shows statement balance, book balance, cleared amounts, outstanding items, and live difference. Complete is disabled until the difference is zero and all required evidence is resolved.

### 8.5 Reports

- Report title, organization, period/as-of date, basis, currency, comparison, and reporting-tag filters.
- Sticky account/description columns and right-aligned numeric columns.
- Expandable drill-through from totals to accounts to journal lines.
- Export and print actions use a server-generated report snapshot so the screen and file agree.
- Saved report views are permissioned and organization-scoped.

## 9. Frontend architecture

Proposed file ownership:

```text
frontend/
  src/
    app/
      router.tsx              # route tree and protected boundaries
      providers.tsx           # auth, query, theme, error boundary
      shell/
        AppShell.tsx
        Sidebar.tsx
        GlobalHeader.tsx
        OrganizationSwitcher.tsx
        QuickCreate.tsx
    api/
      generated/              # generated OpenAPI client; never hand edit
      client.ts               # auth, request ID, org header, errors
      keys.ts                 # organization-safe cache keys
    auth/
      routes/                 # Clerk custom login/signup/recovery
      useAuthorization.ts
    design-system/
      tokens.css
      components/             # buttons, fields, tables, cards, dialogs
    finance/
      home/
      contacts/
      items/
      sales/
      purchases/
      banking/
      accountant/
      reports/
      settings/
    test/
      factories/              # typed API response builders for tests only
      server/                 # request handlers for deterministic tests
```

### State rules

- Server state uses organization-aware keys beginning with `organizationId`.
- Authentication/context state is separate from financial server state.
- Local editor state remains local to the route until save.
- Do not mirror the entire API into a global client store.
- Clear organization-scoped caches on context change, sign out, permission-version change, and membership revocation.
- Money remains a decimal string in TypeScript. Never convert financial values to JavaScript floating-point numbers for calculation.

## 10. Error and loading behavior

- Initial routes use page skeletons matching final layout.
- Background refresh retains current content and shows a subtle freshness indicator.
- Stable backend error codes map to clear user actions: permission denied, stale version, period closed, idempotency conflict, cross-organization reference, over-allocation, negative stock, unresolved reconciliation, and validation errors.
- Field errors render next to the field and are summarized at the top for keyboard/screen-reader navigation.
- Unknown and server errors show the request ID and a retry option when safe.
- Never retry non-idempotent commands automatically without an idempotency key.
- Offline or interrupted submission preserves the draft and tells the user whether the server confirmed success.

## 11. Accessibility and internationalization

- Meet WCAG 2.2 AA for keyboard access, focus visibility, contrast, semantics, errors, and responsive reflow.
- Use real buttons, links, headings, tables, labels, and dialogs before custom ARIA.
- All charts have a textual summary and accessible data table.
- Focus returns predictably after drawers/dialogs and moves to the first error on failed submit.
- Format dates, numbers, currencies, names, and addresses from organization/user locale while sending canonical API values.
- Support right-to-left layout at the shell and component level before claiming an RTL locale.
- Long translations must not clip navigation or financial headers.

## 12. Security and privacy

- Treat route guards as presentation; the API remains authoritative.
- Never store access tokens, financial exports, or sensitive drafts in persistent browser storage unless the authentication design explicitly requires protected storage.
- Sanitize user-authored rich text or avoid rich text entirely in financial documents.
- Prevent organization data from appearing in analytics, error reports, logs, or cache keys beyond approved identifiers.
- Require step-up authentication UI when the backend requests it.
- Downloads use authorized, expiring URLs or authenticated streaming and clearly identify organization and report parameters.

## 13. Frontend work packages

### F0: Contract and design-system foundation

- [ ] Establish React/TypeScript/Vite with strict TypeScript, linting, formatting, unit tests, component tests, and browser tests.
- [ ] Generate the typed client from the backend OpenAPI schema and fail CI on unreviewed contract drift.
- [ ] Implement tokens, typography, icons, buttons, fields, money/date inputs, status badges, cards, tables, drawers, dialogs, toasts, and skeletons.
- [ ] Add an accessible component showcase covering default, hover, focus, disabled, loading, error, and high-contrast states.

### F1: Authentication, organization context, and shell

- [ ] Implement custom Clerk login, sign-up, recovery, bootstrap, and security-session flows described by the auth spec.
- [ ] Build the sidebar and global header exactly once and use them for every authenticated route.
- [ ] Implement organization switching with cache isolation and permission refresh.
- [ ] Add permission-driven navigation and quick create.
- [ ] Add browser tests for authorized A/B switching and prove no stale A data appears after selecting B.

### F2: Setup and accounting foundation

- [ ] Organization finance setup, base currency, fiscal year, chart import/create, account management, finance users/roles, and opening balances.
- [ ] Manual journal list/editor/detail, posting preview, explicit posting, reversal, period lock/reopen, and audit timeline.
- [ ] Trial balance and general ledger with drill-through.
- [ ] Gate completion on backend packages B0, B1, B4, B8, and the relevant close controls.

### F3: Sales and receivables

- [ ] Customers, items, payment terms, taxes, quotes, invoices, approvals, payments received, allocations, advances, refunds, credits, recurring invoices, and AR aging.
- [ ] Provide document preview/print when the backend snapshot renderer is complete.
- [ ] Gate credits and stock returns on backend package B2 and payments/refunds on B4/B5.

### F4: Purchases and payables

- [ ] Vendors, bills, expenses, purchase orders, approvals, payments made, advances, refunds, vendor credits, payment runs, recurring bills, attachments, vendor statements, and AP aging.
- [ ] Gate every direct money workflow on B4/B5 and every stock purchase return on B2/B3.

### F5: Banking and reconciliation

- [ ] Bank/card account overview, statement import preview/mapping, row errors, duplicate review, matching/categorization, rules, transfers, and reconciliation.
- [ ] Do not expose automatic feeds until provider authorization, callback, failure, and operating workflows are complete.
- [ ] Gate release on B6 and B7.

### F6: Inventory and assets

- [ ] Items, warehouses, balances, adjustments, transfers, stock movement history, valuation, and inventory/GL tie-out.
- [ ] Fixed asset register, capitalization, depreciation preview/run, write-down, disposal, and GL tie-out.
- [ ] Gate inventory on B2/B3 and assets on accountant-reviewed backend fixtures.

### F7: Dashboard and reports

- [ ] Implement the complete default dashboard panel set defined in section 7 using production aggregate endpoints.
- [ ] Implement P&L, balance sheet, cash flow, trial balance, GL, AR/AP aging, tax, inventory, asset, bank reconciliation, and movement-of-equity reports as backend support becomes complete.
- [ ] Add comparison, saved views, drill-through, CSV/XLSX/PDF/print, and accessibility data tables.
- [ ] Exclude Projects until its backend exists; do not render a fake panel.

### F8: Settings and controlled customization

- [ ] Organization profile, currencies/rates, fiscal periods, numbering, taxes, templates, reminders, reporting tags, approvals, automation, users/roles, module visibility, data import/export, and backup request surfaces.
- [ ] Module settings may hide completed modules per organization. They cannot reveal unfinished routes.
- [ ] Custom dashboards ship only after panel permissions, persistence, reorder/resize, and accessibility work end to end.

## 14. Frontend testing strategy

| Layer | Required coverage |
|---|---|
| Unit | decimal display helpers, permissions, route builders, reducers, validation adapters |
| Component | states, keyboard interaction, focus, errors, responsive behavior, semantic queries |
| Contract | generated client compiles against checked-in schema; error mapping is exhaustive |
| Integration | lists, editors, state transitions, organization switching, cache invalidation |
| Browser end to end | setup, monthly sales/purchase cycle, banking/reconciliation, close, reports, exports |
| Visual regression | shell, sidebar states, header, dashboard panels, core document/report pages at agreed viewports |
| Accessibility | automated WCAG checks plus manual keyboard and screen-reader review of critical flows |
| Performance | route bundles, dashboard load, large tables, editor input latency, organization switch |

Use deterministic factories only in tests. Production screens never fall back to mock data.

## 15. Definition of done for each route

- [ ] Backend capability and production gate are complete.
- [ ] Permission and organization behavior are defined and tested.
- [ ] Loading, empty, populated, error, stale-version, and forbidden states are implemented.
- [ ] All actions are real, audited backend commands; there are no dead controls.
- [ ] Keyboard, responsive, contrast, and screen-reader checks pass.
- [ ] Money/date/currency localization is correct and decimal-safe.
- [ ] Browser test covers the primary workflow and at least one rejected workflow.
- [ ] Analytics and logging contain no sensitive financial payload.
- [ ] Help text explains calculations and links to drill-through where applicable.

## 16. Frontend production release gate

- [ ] The application shell, sidebar, header, organization switcher, search, and quick create are consistent across all routes.
- [ ] The default dashboard contains every enabled panel from section 7 with correct drill-through and no mocked values.
- [ ] No navigation item or button leads to an unfinished or always-success path.
- [ ] Organization-switch browser tests prove cache and visual isolation.
- [ ] Critical accounting workflows pass end-to-end against PostgreSQL using the restricted application role.
- [ ] WCAG 2.2 AA review, responsive review, visual regression, and representative performance budgets pass.
- [ ] Printed/exported reports and documents match reviewed server snapshots.
- [ ] Product, accounting, design, accessibility, security, engineering, and operations reviews are recorded.
