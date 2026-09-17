# Data Model: Sales and Collection

## Reuse

Organization, Account (`control_kind` ar, plus `advance`, `tax`), JournalEntry/Line, DocumentSequence, FinanceGrant, FinanceSettings, finance_tx, posting.

## New / extended

### Contact

organization, name, is_customer (true in this slice), email optional, billing address lines, status active/inactive, version. Unique name not required.

### Item

organization, sku unique per org, name, kind good|service, unit_price Decimal, income_account FK, default_tax optional, status, version.

### PaymentTerm

organization, name, days (0 = due on receipt).

### TaxRate

organization, name, rate (e.g. 0.10), method exclusive|inclusive, payable_account FK, valid_from date, status.

### ExchangeRate

organization, currency (FK, not base), rate Decimal, as_of date, unique (org, currency, as_of). Direction: base = foreign × rate.

### Quote / QuoteLine

status draft|converted. No journal. Lines: item, description, qty, unit_price, tax_rate optional. Convert copies into invoice draft.

### Invoice / InvoiceLine

status draft|posted. number at post. contact, entry_date, due_date, currency, fx_rate, fx_rate_date, term, quote FK optional, version, journal FK after post. Lines snapshot item id/name, qty, unit_price, tax_rate_id, tax_rate_value, tax_method, tax_amount, net, total, base_net, base_tax, base_total. posted fields immutable.

### CreditNote / CreditNoteLine

status draft|posted. optional invoice FK. Same snapshot/tax/FX rules. Application via Allocation (source credit).

### CustomerPayment

status draft|posted. bank_account FK (ordinary asset, not AR control), currency, fx_rate, amount, entry_date, journal FK. Allocations to invoices. Unallocated remainder after post is advance (credit advance control, debit bank already includes full cash).

### Allocation

organization, invoice, payment XOR credit_note, amount (invoice currency), base_amount, entry_date. Sum per invoice ≤ invoice total. Sum per payment ≤ payment amount.

### CustomerRefund

posted outflow: debit advance or unapplied credit, credit bank. Links payment or credit. Original rows unchanged.

### FinanceSettings (add optional FKs)

ar_account, advance_account, fx_gain_account, fx_loss_account — required when first needed; may be set via settings PUT extras.

### JournalEntry.source_type

Add invoice, payment, credit, refund. Control-account guard allows these plus opening.

## Outstanding

`outstanding(invoice, as_of)` = posted_total − allocations with entry_date ≤ as_of. Historical aging uses this, never today's remaining.
