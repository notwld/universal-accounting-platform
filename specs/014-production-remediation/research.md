# Research

## Idempotency

- Decision: inner `transaction.atomic()` savepoint around insert so IntegrityError does not poison the outer `finance_tx`.
- Alternatives: `select_for_update` on a lock row (heavier).

## Bank duplicates

- Decision: drop unique fingerprint; in-file repeats insert; cross-statement fingerprint matches insert as `review` and surface in `duplicates`.
- Alternatives: keep unique and add a suffix (hides evidence).

## Credits

- Decision: optional `invoice_line_id`/`bill_line_id` + `quantity` + `price_only`; reverse only that qty at original issue/receipt unit cost.
- Alternatives: always reverse whole source (current defect).
