# Tasks: Sales and Collection

**Input**: `/specs/003-sales-collection/`

**Tests**: Required (accounting + allocation). No frontend.

- [x] T001 Extend permissions in `backend/apps/finance/permissions.py` and error catalogue in `backend/apps/authentication/constants.py`
- [x] T002 Extend `JournalEntry.Source` and control-account allowlist in `backend/apps/finance/models/ledger.py` + `backend/apps/finance/services/posting.py`; add `post_generated`
- [x] T003 Add sales models in `backend/apps/finance/models/sales.py` and settings account FKs in `backend/apps/finance/models/config.py`; migrate
- [x] T004 Tax + FX helpers in `backend/apps/finance/services/tax.py` and `backend/apps/finance/services/money.py`
- [x] T005 Invoice/quote/credit/payment/refund services in `backend/apps/finance/services/sales.py`
- [x] T006 AR aging in `backend/apps/finance/selectors/aging.py`
- [x] T007 HTTP routes in `backend/apps/finance/api/sales_views.py` + `backend/apps/finance/api/urls.py`
- [x] T008 Tests in `backend/apps/finance/tests/test_sales.py` for 110/60/80, quote isolation, clerk cannot post, FX 1.10/1.15, historical aging, over-allocation
- [x] T009 Run pytest finance+auth, `manage.py check`; record `specs/003-sales-collection/verification.md`

No screens, PDF, email, bills, or approval engine.
