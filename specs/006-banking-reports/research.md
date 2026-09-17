# Research

## Bank master
- **Decision**: Reuse `Account` (asset). No BankAccount table.
- **Rationale**: Chart already has cash. A second master would duplicate GL links.

## Import
- **Decision**: CSV `date,amount,description`; fingerprint sha256 of those fields + org + account.
- **Rationale**: Stdlib csv. Duplicate review is unique constraint + import summary.

## Match vs categorize
- **Decision**: Match points at CustomerPayment or VendorPayment; amount abs-equal; no journal. Categorize posts `source_type=bank`.
- **Rationale**: Product rule: matching must not double cash.

## Reports
- **Decision**: P&L/BS fold trial-balance rows by classification. BS is cumulative through `as_of`.
- **Rationale**: One calculation path.
