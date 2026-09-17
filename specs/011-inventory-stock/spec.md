# Feature Specification: Inventory Stock and Valuation

**Feature Branch**: `011-inventory-stock`

**Created**: 2026-09-17

**Status**: Implemented

**Input**: User description: "No SMS or live bank for now, move to next task." Next package is Phase 6 inventory (API only).

**Requirement coverage**: FIN-07 tracked stock, warehouses as locations, moving-average costing, COGS tie-out. Screens, SMS, live bank feeds, assets, FIFO deferred.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Buy tracked goods onto the shelf (Priority: P1)

An Accountant marks an item as tracked, sets inventory and COGS accounts, and posts a bill for 10 units at 8. Quantity 10 and value 80 sit in the default warehouse. The bill debits inventory, not expense.

**Independent Test**: Post bill 10×8; stock qty 10 value 80; inventory GL 80.

### User Story 2 - Sell using moving average (Priority: P1)

Posting an invoice for 4 units issues stock at the current average (8). COGS is 32; remaining qty 6 value 48. A sale of 7 more is rejected (negative stock blocked).

**Independent Test**: After the bill, invoice 4 → COGS 32; invoice 7 fails `negative_stock`.

### User Story 3 - Transfer, adjust, valuation (Priority: P2)

Stock can move between two warehouses without a GL posting. An adjustment changes quantity at average cost and posts to COGS vs inventory. Valuation equals the inventory GL.

**Independent Test**: Transfer 2 to a second warehouse; adjust −1 on Main; valuation total equals inventory account balance.

## Requirements

- **FR-001**: Items may be tracked (goods only). Untracked items do not move stock.
- **FR-002**: Warehouses are org-scoped locations, not a second books owner. A default warehouse exists.
- **FR-003**: Bill post of tracked lines receives stock and debits the inventory account at line net (moving-average receipt).
- **FR-004**: Invoice post of tracked lines issues stock at current average; Dr COGS Cr inventory. Negative quantity is rejected.
- **FR-005**: Transfer moves quantity and value between warehouses with no journal.
- **FR-006**: Adjustment posts quantity change at average (or supplied unit cost for increases) through inventory and COGS.
- **FR-007**: Valuation lists qty/value per item/warehouse and the inventory GL balance.
- **FR-008**: No screens. No SMS. No live bank APIs.

## Success Criteria

- **SC-001**: 10 received at 8 then 4 sold → qty 6, value 48, COGS 32.
- **SC-002**: Issue beyond on-hand quantity posts nothing.
- **SC-003**: Stock valuation total equals the inventory account’s net posted balance.

## Assumptions

- Costing is perpetual moving weighted average in base currency.
- One default warehouse named Main until others are created.
- Customer/vendor credit stock reversal is document-level when the credit links a posted invoice/bill.

## Out of Scope

- UI, SMS, Plaid/live bank, FIFO, lots/serials, assets, country packs.
