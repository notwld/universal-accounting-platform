# Research

## Costing

- Decision: perpetual moving weighted average on `StockBalance.value / qty`.
- Rationale: plan’s recommended first method; one number per item/warehouse.
- Alternatives: FIFO layers (deferred).

## GL

- Decision: tracked bill lines debit inventory; invoice journals include COGS/inventory; transfers no journal.
- Rationale: one posting engine; match does not double cash, stock should not double expense.
- Alternatives: separate stock journals always (noisier).
