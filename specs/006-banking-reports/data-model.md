# Data Model

### BankStatement
organization, account (GL), imported_at, original_name

### BankLine
organization, statement, account, entry_date, amount, description, fingerprint unique (org, account, fingerprint), status imported|matched|categorized, customer_payment FK, vendor_payment FK, journal FK

### BankReconciliation
organization, account, start_on, end_on, opening, closing, status open|complete, reopen_reason
