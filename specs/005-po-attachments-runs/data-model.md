# Data Model

### PurchaseOrder / PurchaseOrderLine
status draft|converted. contact, entry_date, currency. Lines: item, qty, unit_price, tax, description. `Bill.purchase_order` optional FK.

### FinanceAttachment
organization, object_type, object_id, original_name, content_type, size, file, uploaded_by. Unique enough by id.

### PaymentRun
status draft|posted, bank_account, entry_date, currency, number. Lines: bill, amount, vendor_payment FK after post.

### Vendor statement
Not stored. Query bills, vendor payments, vendor credits, allocations for contact in [from, to].
