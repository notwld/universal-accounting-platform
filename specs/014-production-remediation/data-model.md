# Data Model

CreditNoteLine / VendorCreditLine: optional source line FK, item, quantity, price_only.
BankLine.status += `review`. BankStatement.file_hash.
Drop `uniq_finance_bank_line_fingerprint`.
FinanceIdempotency: resource_type, resource_id.
Account/stock qty quantization uses quantity scale 8, not currency exponent.
Currency: expanded ISO 4217 seed via data migration.
