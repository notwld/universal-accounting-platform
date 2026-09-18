from decimal import Decimal

import pytest
from django.test import override_settings

from apps.finance.models import Bill, JournalLine, PaidExpense
from apps.finance.tests.test_setup_isolation import CLERK, auth_headers, create_books, make_token

pytest_plugins = ["apps.finance.tests.test_setup_isolation"]


def _h(token, org_id, **extra):
    return auth_headers(token, org_id, **extra)


def _purchase_setup(api, token, org, cash, income):
    tax_pay = api.post(
        "/api/v1/finance/accounts",
        {"code": "2200", "name": "Tax", "classification": "liability"},
        format="json", **_h(token, org["id"]),
    ).json()["data"]
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
    fxg = api.post(
        "/api/v1/finance/accounts",
        {"code": "7100", "name": "FX gain", "classification": "income"},
        format="json", **_h(token, org["id"]),
    ).json()["data"]
    fxl = api.post(
        "/api/v1/finance/accounts",
        {"code": "8100", "name": "FX loss", "classification": "expense"},
        format="json", **_h(token, org["id"]),
    ).json()["data"]
    settings = api.put(
        "/api/v1/finance/settings",
        {
            "country_code": "US",
            "base_currency": "USD",
            "fiscal_year_start_month": 1,
            "timezone": "UTC",
            "locale": "en",
            "tax_registration_applies": False,
            "ap_account_id": ap["id"],
            "vendor_advance_account_id": vadv["id"],
            "fx_gain_account_id": fxg["id"],
            "fx_loss_account_id": fxl["id"],
        },
        format="json", **_h(token, org["id"]),
    )
    assert settings.status_code == 200, settings.content
    tax = api.post(
        "/api/v1/finance/tax-rates",
        {"name": "Input 10", "rate": "0.10", "method": "exclusive", "payable_account_id": tax_pay["id"], "valid_from": "2026-01-01"},
        format="json", **_h(token, org["id"]),
    ).json()["data"]
    contact = api.post(
        "/api/v1/finance/contacts", {"name": "VendorCo", "is_vendor": True}, format="json", **_h(token, org["id"])
    ).json()["data"]
    item = api.post(
        "/api/v1/finance/items",
        {
            "sku": "PART", "name": "Parts", "unit_price": "100",
            "income_account_id": income["id"], "expense_account_id": expense["id"], "tax_rate_id": tax["id"],
        },
        format="json", **_h(token, org["id"]),
    ).json()["data"]
    return tax, contact, item, tax_pay, expense, ap, cash


@pytest.mark.django_db
def test_bill_payment_expense_refund(api, rsa_keys, auth_user, other_user):
    private_pem, public_pem = rsa_keys
    token = make_token(private_pem)
    with override_settings(CLERK_JWT_KEY=public_pem, **CLERK):
        org, cash, equity, income, ar = create_books(api, token, name="BuyCo", currency="USD", month=1, country="US")
        tax, contact, item, tax_pay, expense, ap, cash = _purchase_setup(api, token, org, cash, income)
        bill = api.post(
            "/api/v1/finance/bills",
            {
                "contact_id": contact["id"], "entry_date": "2026-03-01", "currency": "USD",
                "lines": [{"item_id": item["id"], "quantity": "1", "unit_price": "100", "tax_rate_id": tax["id"]}],
            },
            format="json", **_h(token, org["id"]),
        )
        assert bill.status_code == 201, bill.content
        bill_id = bill.json()["data"]["id"]
        preview = api.get(f"/api/v1/finance/bills/{bill_id}/preview", **_h(token, org["id"]))
        assert preview.status_code == 200
        assert JournalLine.objects.count() == 0
        posted = api.post(
            f"/api/v1/finance/bills/{bill_id}/post", format="json",
            **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="bill1"),
        )
        assert posted.status_code == 200, posted.content
        data = posted.json()["data"]
        assert Decimal(data["total"]) == Decimal("110.00")
        replay = api.post(
            f"/api/v1/finance/bills/{bill_id}/post", format="json",
            **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="bill1"),
        )
        assert replay.json()["data"]["id"] == data["id"]
        row = Bill.objects.get(id=bill_id)
        lines = {ln.account.code: (ln.debit, ln.credit) for ln in row.journal.lines.select_related("account")}
        assert lines["5000"][0] == Decimal("100.00")
        assert lines["2200"][0] == Decimal("10.00")
        assert lines["2100"][1] == Decimal("110.00")

        pay1 = api.post(
            "/api/v1/finance/vendor-payments",
            {
                "contact_id": contact["id"], "bank_account_id": cash["id"], "entry_date": "2026-03-10",
                "currency": "USD", "amount": "60",
                "allocations": [{"bill_id": bill_id, "amount": "60"}],
            },
            format="json", **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="vp1"),
        )
        assert pay1.status_code == 201, pay1.content
        aging_mid = api.get(
            "/api/v1/finance/reports/ap-aging?as_of=2026-03-05", **_h(token, org["id"])
        ).json()["data"]["items"]
        assert aging_mid and Decimal(aging_mid[0]["outstanding"]) == Decimal("110.00")
        pay2 = api.post(
            "/api/v1/finance/vendor-payments",
            {
                "contact_id": contact["id"], "bank_account_id": cash["id"], "entry_date": "2026-03-12",
                "currency": "USD", "amount": "80",
                "allocations": [{"bill_id": bill_id, "amount": "50"}],
            },
            format="json", **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="vp2"),
        )
        assert pay2.status_code == 201, pay2.content
        aging_now = api.get(
            "/api/v1/finance/reports/ap-aging?as_of=2026-03-31", **_h(token, org["id"])
        ).json()["data"]["items"]
        assert aging_now == []
        over = api.post(
            "/api/v1/finance/vendor-payments",
            {
                "contact_id": contact["id"], "bank_account_id": cash["id"], "entry_date": "2026-03-13",
                "currency": "USD", "amount": "1",
                "allocations": [{"bill_id": bill_id, "amount": "1"}],
            },
            format="json", **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="vp3"),
        )
        assert over.json()["error"]["code"] == "over_allocation"
        refund = api.post(
            "/api/v1/finance/vendor-refunds",
            {
                "payment_id": pay2.json()["data"]["id"], "amount": "30",
                "bank_account_id": cash["id"], "entry_date": "2026-03-20",
            },
            format="json", **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="vr1"),
        )
        assert refund.status_code == 201, refund.content

        exp = api.post(
            "/api/v1/finance/expenses",
            {
                "contact_id": contact["id"], "bank_account_id": cash["id"], "entry_date": "2026-03-21",
                "currency": "USD",
                "lines": [{
                    "expense_account_id": expense["id"], "net": "50", "tax_amount": "5",
                    "tax_payable_account_id": tax_pay["id"], "description": "cogs",
                }],
            },
            format="json", **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="exp1"),
        )
        assert exp.status_code == 201, exp.content
        pe = PaidExpense.objects.get(id=exp.json()["data"]["id"])
        by_code = {ln.account.code: (ln.debit, ln.credit) for ln in pe.journal.lines.select_related("account")}
        assert by_code["5000"][0] == Decimal("50.00")
        assert by_code["2200"][0] == Decimal("5.00")
        assert by_code["1000"][1] == Decimal("55.00")
        assert Decimal(exp.json()["data"]["total"]) == Decimal("55.00")

        bill2 = api.post(
            "/api/v1/finance/bills",
            {
                "contact_id": contact["id"], "entry_date": "2026-03-22", "currency": "USD",
                "lines": [{"item_id": item["id"], "quantity": "1", "unit_price": "100", "tax_rate_id": tax["id"]}],
            },
            format="json", **_h(token, org["id"]),
        )
        assert bill2.status_code == 201, bill2.content
        posted2 = api.post(
            f"/api/v1/finance/bills/{bill2.json()['data']['id']}/post", format="json",
            **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="bill-vc"),
        )
        assert posted2.status_code == 200, posted2.content
        vc = api.post(
            "/api/v1/finance/vendor-credits",
            {
                "contact_id": contact["id"], "bill_id": bill2.json()["data"]["id"],
                "entry_date": "2026-03-23", "currency": "USD", "total": "110", "base_total": "110",
                "lines": [{
                    "expense_account_id": expense["id"], "net": "100", "tax_amount": "10", "total": "110",
                    "base_net": "100", "base_tax": "10", "base_total": "110",
                    "tax_payable_account_id": tax_pay["id"], "description": "credit",
                }],
            },
            format="json", **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="vc1"),
        )
        assert vc.status_code == 201, vc.content
        aging_credit = api.get(
            "/api/v1/finance/reports/ap-aging?as_of=2026-03-23", **_h(token, org["id"])
        ).json()["data"]["items"]
        assert all(row["bill_id"] != bill2.json()["data"]["id"] for row in aging_credit)

        api.put(
            f"/api/v1/finance/grants/{other_user.id}", {"role_slug": "purchasing_clerk"},
            format="json", **_h(token, org["id"]),
        )
        clerk = make_token(private_pem, sub="user_clerk_2", sid="sess_2")
        draft = api.post(
            "/api/v1/finance/bills",
            {
                "contact_id": contact["id"], "entry_date": "2026-03-22", "currency": "USD",
                "lines": [{"item_id": item["id"], "quantity": "1", "unit_price": "10", "tax_rate_id": tax["id"]}],
            },
            format="json", **_h(clerk, org["id"]),
        )
        assert draft.status_code == 201, draft.content
        denied = api.post(
            f"/api/v1/finance/bills/{draft.json()['data']['id']}/post", format="json",
            **_h(clerk, org["id"], HTTP_IDEMPOTENCY_KEY="clerk-bill"),
        )
        assert denied.status_code == 403
        api.put(
            f"/api/v1/finance/grants/{other_user.id}", {"role_slug": "sales_clerk"},
            format="json", **_h(token, org["id"]),
        )
        sales_denied = api.post(
            "/api/v1/finance/bills",
            {
                "contact_id": contact["id"], "entry_date": "2026-03-23", "currency": "USD",
                "lines": [{"item_id": item["id"], "quantity": "1", "unit_price": "10"}],
            },
            format="json", **_h(clerk, org["id"]),
        )
        assert sales_denied.status_code == 403


@pytest.mark.django_db
def test_fx_bill_and_settlement(api, rsa_keys, auth_user):
    private_pem, public_pem = rsa_keys
    token = make_token(private_pem)
    with override_settings(CLERK_JWT_KEY=public_pem, **CLERK):
        org, cash, equity, income, ar = create_books(api, token, name="FXBuy", currency="USD", month=1, country="US")
        tax, contact, item, tax_pay, expense, ap, cash = _purchase_setup(api, token, org, cash, income)
        item_fx = api.post(
            "/api/v1/finance/items",
            {"sku": "EURP", "name": "EU parts", "unit_price": "100", "income_account_id": income["id"], "expense_account_id": expense["id"]},
            format="json", **_h(token, org["id"]),
        ).json()["data"]
        rate = api.post(
            "/api/v1/finance/exchange-rates",
            {"currency": "EUR", "rate": "1.10", "as_of": "2026-04-01"},
            format="json", **_h(token, org["id"]),
        )
        assert rate.status_code == 201, rate.content
        bill = api.post(
            "/api/v1/finance/bills",
            {
                "contact_id": contact["id"], "entry_date": "2026-04-01", "currency": "EUR",
                "lines": [{"item_id": item_fx["id"], "quantity": "1", "unit_price": "100"}],
            },
            format="json", **_h(token, org["id"]),
        )
        assert bill.status_code == 201, bill.content
        posted = api.post(
            f"/api/v1/finance/bills/{bill.json()['data']['id']}/post", format="json",
            **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="fx-bill"),
        )
        assert posted.status_code == 200, posted.content
        assert Decimal(posted.json()["data"]["base_total"]) == Decimal("110.00")
        pay = api.post(
            "/api/v1/finance/vendor-payments",
            {
                "contact_id": contact["id"], "bank_account_id": cash["id"], "entry_date": "2026-04-10",
                "currency": "EUR", "fx_rate": "1.15", "amount": "100",
                "allocations": [{"bill_id": bill.json()["data"]["id"], "amount": "100"}],
            },
            format="json", **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="fx-vpay"),
        )
        assert pay.status_code == 201, pay.content
        from apps.finance.models import VendorPayment
        p = VendorPayment.objects.get(id=pay.json()["data"]["id"])
        by_code = {ln.account.code: (ln.debit, ln.credit) for ln in p.journal.lines.select_related("account")}
        assert by_code["2100"][0] == Decimal("110.00")
        assert by_code["8100"][0] == Decimal("5.00")
        assert by_code["1000"][1] == Decimal("115.00")
        missing = api.post(
            "/api/v1/finance/bills",
            {
                "contact_id": contact["id"], "entry_date": "2026-05-01", "currency": "GBP",
                "lines": [{"item_id": item_fx["id"], "quantity": "1", "unit_price": "100"}],
            },
            format="json", **_h(token, org["id"]),
        )
        assert missing.status_code == 422
        assert missing.json()["error"]["code"] == "missing_rate"
