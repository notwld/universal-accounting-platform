# Tasks: Purchases and Payables

**Input**: `/specs/004-purchases-payables/`

**Tests**: Required (accounting + allocation). No frontend.

- [x] T001 Add `finance.bill.create` in `backend/apps/finance/permissions.py`; give purchasing_clerk bill/contact/item; keep sales_clerk without bill.create
- [x] T002 Extend `JournalEntry.Source` and `CONTROL_SOURCES` in `backend/apps/finance/models/ledger.py` + `backend/apps/finance/services/posting.py`
- [x] T003 Add purchase models in `backend/apps/finance/models/purchases.py`; Contact.is_vendor, Item.expense_account, settings AP FKs; migrate + RLS
- [x] T004 Bill/expense/credit/payment/refund services in `backend/apps/finance/services/purchases.py`
- [x] T005 AP aging in `backend/apps/finance/selectors/aging.py`
- [x] T006 HTTP routes in `backend/apps/finance/api/purchase_views.py` + `backend/apps/finance/api/urls.py`; contacts/items/settings accept vendor fields
- [x] T007 Tests in `backend/apps/finance/tests/test_purchases.py` for 110/60/80, paid expense, clerks, FX 1.10/1.15 loss, historical aging, over-allocation
- [x] T008 Run pytest finance+auth, `manage.py check`; record `specs/004-purchases-payables/verification.md`

No screens, PDF, email, PO, attachments, or approval engine.
