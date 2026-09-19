# Feature Specification: Items master-detail workspace

**Feature Branch**: `024-items-master-detail`

**Created**: 2026-09-19

**Status**: Ready for planning

**Input**: Create Items module pages (Items, Warehouses, Stock Balances, Stock Adjustments, Stock Transfers) with CRUD, reusable two-panel layout (thin left list + right preview), search, toggleable filters, bottom pagination, list rows scroll only.

## User Scenarios & Testing

### User Story 1 - Reusable master-detail shell (Priority: P1)

Users see a consistent workspace: thinner left list pane (search, optional filters, paginated rows that scroll inside the pane) and a right preview/detail pane.

**Acceptance Scenarios**:

1. **Given** a module page using the workspace, **When** the list has many rows, **Then** only the list body scrolls; search and pagination stay visible.
2. **Given** the filter icon is clicked, **When** filters open, **Then** filter controls appear under search without leaving the page.
3. **Given** a narrow viewport, **When** a row is selected, **Then** detail is shown with a way back to the list.

### User Story 2 - Items & Warehouses CRUD-lite (Priority: P1)

Users can list and create Items and Warehouses via finance APIs and preview a selected record.

**Acceptance Scenarios**:

1. **Given** an org context, **When** opening Items, **Then** existing items load and selecting one shows preview fields.
2. **Given** create form on Items, **When** valid data is submitted, **Then** the item appears in the list and is selected.
3. Same for Warehouses (name create).

### User Story 3 - Stock views & mutations (Priority: P2)

Users browse stock balances; adjust and transfer forms operate on a selected balance/item via POST endpoints.

**Acceptance Scenarios**:

1. Stock Balances lists qty/value per item/warehouse with preview.
2. Stock Adjustments / Transfers show a form in the detail pane after selecting context from the list.

## Requirements

- **FR-001**: Shared `MasterDetailWorkspace` used by all five Items routes.
- **FR-002**: Left pane thinner than right; fixed chrome (search/filter/pagination); scrolling list body only.
- **FR-003**: Filter panel revealed by control next to search.
- **FR-004**: Client pagination with “X–Y of Z” until APIs paginate.
- **FR-005**: Wire to `/finance/items`, `/warehouses`, `/stock/balances`, `/stock/adjust`, `/stock/transfer`.
- **FR-006**: No fake amounts; empty/error/loading states honest.
- **FR-007**: Update/delete only where backend supports (today: create+read for items/warehouses; adjust/transfer as create actions).

## Assumptions

- Backend list endpoints return full arrays; filter/search/page client-side for now.
- Item create requires `income_account_id` from chart of accounts.
- RBAC UI gates deferred; API still enforces grants.
