# Research

## Attachments
- **Decision**: `FileField` on `FinanceAttachment`; download via authenticated view; never rely on `/media/` as the ACL.
- **Rationale**: Django storage is already installed. Public MEDIA_URL would bypass org checks.
- **Alternatives**: S3 now — no bucket chosen.

## Purchase orders
- **Decision**: Mirror `Quote`/`convert_quote` → `Bill`. No stock movement.
- **Rationale**: Phase 6 owns receipts/warehouses. Commercial PO is the buy-side quote.
- **Alternatives**: Wait for inventory — user asked for POs now.

## Payment runs
- **Decision**: Group run lines by vendor; call `post_vendor_payment` per vendor; store `PaymentRun` + payment FKs.
- **Rationale**: One cash engine. No second posting path.
- **Alternatives**: Single mega-journal — would skip AP allocations.

## Statements / credits
- **Decision**: Derived GET; reuse credit post that already allocates.
- **Rationale**: Tests were the gap, not the service.
