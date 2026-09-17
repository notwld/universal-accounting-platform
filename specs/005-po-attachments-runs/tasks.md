# Tasks: PO, Attachments, Payment Runs

**Input**: `/specs/005-po-attachments-runs/`

- [x] T001 MEDIA settings + attachment model in `backend/apps/finance/models/attachments.py`; PO/PaymentRun in `backend/apps/finance/models/purchases.py`; `Bill.purchase_order`; migrate + RLS
- [x] T002 `convert_po`, `post_payment_run`, `vendor_statement` in `backend/apps/finance/services/purchases.py`; attachment upload/download helpers
- [x] T003 HTTP in `backend/apps/finance/api/purchase_views.py` + urls
- [x] T004 Tests in `backend/apps/finance/tests/test_purchases_extra.py`; credit paths in existing sales/purchases tests
- [x] T005 pytest finance+auth, check, verification.md

No screens, stock receipts, or bank import in this feature.
