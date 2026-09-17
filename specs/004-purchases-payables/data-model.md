# Data Model: Purchases and Payables

## Reuse

Organization, Account (`control_kind` ap, plus `vadv` or `advance` distinguished by settings FK), JournalEntry/Line, DocumentSequence, FinanceGrant, FinanceSettings, Contact, Item, TaxRate, ExchangeRate, finance_tx, posting, `line_tax`, `resolve_rate`.

## New / extended

### Contact

Add `is_vendor` boolean (default false). Existing `is_customer` unchanged. A contact may be both.

### Item

Add optional `expense_account` FK. Required on bill lines (from item or explicit line account).

### FinanceSettings

Optional FKs: `ap_account`, `vendor_advance_account`. Reuse `fx_gain_account` / `fx_loss_account`.

### Bill / BillLine

status draft|posted. number at post. contact, entry_date, due_date, currency, fx_rate, contact_name snapshot, total, base_total, version, journal FK after post. Lines snapshot item, description, qty, unit_price, tax id/rate/method/name, net/tax/total and base amounts, expense_account.

### VendorCredit / VendorCreditLine

status draft|posted. optional bill FK. Same snapshot/tax/FX rules. Application via BillAllocation.

### VendorPayment

status draft|posted. bank_account FK, currency, fx_rate, amount, entry_date, journal FK. Allocations to bills. Unallocated remainder after post is vendor advance (debit advance asset, credit bank includes full cash).

### BillAllocation

organization, bill, vendor_payment XOR vendor_credit, amount (bill currency), base_amount, entry_date. Sum per bill ≤ bill total. Sum per payment ≤ payment amount.

### VendorRefund

posted inflow: debit bank, credit vendor advance. Links payment. Original rows unchanged.

### PaidExpense / PaidExpenseLine

posted immediately. bank_account, currency, fx_rate, entry_date, journal. Lines: expense_account, net/tax/total, base amounts, tax account optional. No AP.

### JournalEntry.source_type

Add bill, expense, vendor_payment, vendor_credit, vendor_refund. Control-account guard allows these plus existing sales/opening types.

## Outstanding

`outstanding(bill, as_of)` = posted_total − bill allocations with entry_date ≤ as_of.
