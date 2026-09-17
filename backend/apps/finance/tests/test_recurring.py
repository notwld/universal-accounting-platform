from decimal import Decimal

import pytest
from django.test import override_settings

from apps.finance.models import Bill, Invoice, JournalLine, PaidExpense
from apps.finance.tests.test_sales import _sales_setup
from apps.finance.tests.test_setup_isolation import CLERK, auth_headers, create_books, make_token

pytest_plugins = ["apps.finance.tests.test_setup_isolation"]


def _h(token, org_id, **extra):
    return auth_headers(token, org_id, **extra)


@pytest.mark.django_db
def test_recurring_month_end_pause_and_replay(api, rsa_keys, auth_user):
    private_pem, public_pem = rsa_keys
    token = make_token(private_pem)
    with override_settings(CLERK_JWT_KEY=public_pem, **CLERK):
        org, cash, equity, income, ar = create_books(
            api, token, name="RecurCo", currency="USD", month=1, country="US"
        )
        tax, contact, item, tax_pay, advance, cash = _sales_setup(api, token, org, cash, income, ar)
        sched = api.post(
            "/api/v1/finance/recurring",
            {
                "kind": "invoice",
                "contact_id": contact["id"],
                "currency": "USD",
                "start_on": "2026-01-31",
                "day_of_month": 31,
                "lines": [{"item_id": item["id"], "quantity": "1", "unit_price": "100", "tax_rate_id": tax["id"]}],
            },
            format="json", **_h(token, org["id"]),
        )
        assert sched.status_code == 201, sched.content
        run = api.post(
            "/api/v1/finance/recurring/run",
            {"as_of": "2026-03-01"},
            format="json", **_h(token, org["id"]),
        )
        assert run.status_code == 200, run.content
        assert len(run.json()["data"]["created"]) == 2
        invoices = list(Invoice.objects.filter(organization_id=org["id"]).order_by("entry_date"))
        assert [i.entry_date.isoformat() for i in invoices] == ["2026-01-31", "2026-02-28"]
        assert all(i.status == Invoice.Status.DRAFT for i in invoices)
        assert JournalLine.objects.count() == 0
        again = api.post(
            "/api/v1/finance/recurring/run",
            {"as_of": "2026-03-01"},
            format="json", **_h(token, org["id"]),
        )
        assert again.json()["data"]["created"] == []
        assert Invoice.objects.filter(organization_id=org["id"]).count() == 2
        paused = api.post(
            f"/api/v1/finance/recurring/{sched.json()['data']['id']}/pause",
            format="json", **_h(token, org["id"]),
        )
        assert paused.json()["data"]["status"] == "paused"
        march = api.post(
            "/api/v1/finance/recurring/run",
            {"as_of": "2026-03-31"},
            format="json", **_h(token, org["id"]),
        )
        assert march.json()["data"]["created"] == []

        expense = api.post(
            "/api/v1/finance/accounts",
            {"code": "5000", "name": "Purchases", "classification": "expense"},
            format="json", **_h(token, org["id"]),
        ).json()["data"]
        ap = api.post(
            "/api/v1/finance/accounts",
            {"code": "2100", "name": "AP", "classification": "liability", "is_control": True, "control_kind": "ap"},
            format="json", **_h(token, org["id"]),
        ).json()["data"]
        vadv = api.post(
            "/api/v1/finance/accounts",
            {"code": "1500", "name": "Vendor advances", "classification": "asset", "is_control": True, "control_kind": "advance"},
            format="json", **_h(token, org["id"]),
        ).json()["data"]
        settings = api.put(
            "/api/v1/finance/settings",
            {
                "country_code": "US", "base_currency": "USD", "fiscal_year_start_month": 1,
                "timezone": "UTC", "locale": "en", "tax_registration_applies": False,
                "ap_account_id": ap["id"], "vendor_advance_account_id": vadv["id"],
            },
            format="json", **_h(token, org["id"]),
        )
        assert settings.status_code == 200, settings.content
        vendor = api.post(
            "/api/v1/finance/contacts", {"name": "VendorCo", "is_vendor": True}, format="json", **_h(token, org["id"])
        ).json()["data"]
        part = api.post(
            "/api/v1/finance/items",
            {
                "sku": "PART", "name": "Parts", "unit_price": "100",
                "income_account_id": income["id"], "expense_account_id": expense["id"], "tax_rate_id": tax["id"],
            },
            format="json", **_h(token, org["id"]),
        ).json()["data"]
        tax_p, tax_pay_p = tax, tax_pay
        bill_s = api.post(
            "/api/v1/finance/recurring",
            {
                "kind": "bill",
                "contact_id": vendor["id"],
                "currency": "USD",
                "start_on": "2026-04-01",
                "day_of_month": 1,
                "lines": [{"item_id": part["id"], "quantity": "1", "unit_price": "100", "tax_rate_id": tax_p["id"]}],
            },
            format="json", **_h(token, org["id"]),
        )
        assert bill_s.status_code == 201, bill_s.content
        exp_s = api.post(
            "/api/v1/finance/recurring",
            {
                "kind": "expense",
                "contact_id": vendor["id"],
                "currency": "USD",
                "start_on": "2026-04-01",
                "day_of_month": 1,
                "bank_account_id": cash["id"],
                "lines": [{
                    "expense_account_id": expense["id"], "net": "50", "tax_amount": "5",
                    "tax_payable_account_id": tax_pay_p["id"], "description": "rent",
                }],
            },
            format="json", **_h(token, org["id"]),
        )
        assert exp_s.status_code == 201, exp_s.content
        mixed = api.post(
            "/api/v1/finance/recurring/run",
            {"as_of": "2026-04-01"},
            format="json", **_h(token, org["id"]),
        )
        assert mixed.status_code == 200, mixed.content
        assert Bill.objects.filter(organization_id=org["id"], status=Bill.Status.DRAFT).count() == 1
        assert PaidExpense.objects.filter(organization_id=org["id"]).count() == 1
        before = JournalLine.objects.count()
        replay = api.post(
            "/api/v1/finance/recurring/run",
            {"as_of": "2026-04-01"},
            format="json", **_h(token, org["id"]),
        )
        assert replay.json()["data"]["created"] == []
        assert JournalLine.objects.count() == before
        assert Decimal(PaidExpense.objects.get().total) == Decimal("55.00")
