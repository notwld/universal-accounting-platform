from decimal import Decimal

import pytest
from django.test import override_settings

from apps.finance.models import Invoice, JournalLine
from apps.finance.tests.test_setup_isolation import CLERK, auth_headers, create_books, make_token

pytest_plugins = ["apps.finance.tests.test_setup_isolation"]


def _h(token, org_id, **extra):
    return auth_headers(token, org_id, **extra)


def _sales_setup(api, token, org, cash, income, ar):
    tax_pay = api.post(
        "/api/v1/finance/accounts",
        {"code": "2200", "name": "Tax payable", "classification": "liability"},
        format="json", **_h(token, org["id"]),
    ).json()["data"]
    advance = api.post(
        "/api/v1/finance/accounts",
        {"code": "2300", "name": "Customer advances", "classification": "liability", "is_control": True, "control_kind": "advance"},
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
            "ar_account_id": ar["id"],
            "advance_account_id": advance["id"],
            "fx_gain_account_id": fxg["id"],
            "fx_loss_account_id": fxl["id"],
        },
        format="json", **_h(token, org["id"]),
    )
    assert settings.status_code == 200, settings.content
    tax = api.post(
        "/api/v1/finance/tax-rates",
        {"name": "Output 10", "rate": "0.10", "method": "exclusive", "payable_account_id": tax_pay["id"], "valid_from": "2024-01-01"},
        format="json", **_h(token, org["id"]),
    ).json()["data"]
    contact = api.post(
        "/api/v1/finance/contacts", {"name": "Acme"}, format="json", **_h(token, org["id"])
    ).json()["data"]
    item = api.post(
        "/api/v1/finance/items",
        {"sku": "SVC", "name": "Work", "unit_price": "100", "income_account_id": income["id"], "tax_rate_id": tax["id"]},
        format="json", **_h(token, org["id"]),
    ).json()["data"]
    return tax, contact, item, tax_pay, advance, cash


@pytest.mark.django_db
def test_invoice_payment_credit_refund(api, rsa_keys, auth_user, other_user):
    private_pem, public_pem = rsa_keys
    token = make_token(private_pem)
    with override_settings(CLERK_JWT_KEY=public_pem, **CLERK):
        org, cash, equity, income, ar = create_books(api, token, name="SalesCo", currency="USD", month=1, country="US")
        tax, contact, item, tax_pay, advance, cash = _sales_setup(api, token, org, cash, income, ar)
        quote = api.post(
            "/api/v1/finance/quotes",
            {
                "contact_id": contact["id"],
                "entry_date": "2026-03-01",
                "currency": "USD",
                "lines": [{"item_id": item["id"], "quantity": "1", "unit_price": "100", "tax_rate_id": tax["id"]}],
            },
            format="json", **_h(token, org["id"]),
        )
        assert quote.status_code == 201, quote.content
        tb = api.get(
            "/api/v1/finance/reports/trial-balance?from=2026-01-01&to=2026-12-31", **_h(token, org["id"])
        ).json()["data"]["items"]
        assert tb == []
        converted = api.post(
            f"/api/v1/finance/quotes/{quote.json()['data']['id']}/convert", format="json", **_h(token, org["id"])
        )
        assert converted.status_code == 201, converted.content
        invoice_id = converted.json()["data"]["id"]
        preview = api.get(f"/api/v1/finance/invoices/{invoice_id}/preview", **_h(token, org["id"]))
        assert preview.status_code == 200
        assert JournalLine.objects.count() == 0
        posted = api.post(
            f"/api/v1/finance/invoices/{invoice_id}/post", format="json",
            **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="inv1"),
        )
        assert posted.status_code == 200, posted.content
        data = posted.json()["data"]
        assert Decimal(data["total"]) == Decimal("110.00")
        replay = api.post(
            f"/api/v1/finance/invoices/{invoice_id}/post", format="json",
            **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="inv1"),
        )
        assert replay.json()["data"]["id"] == data["id"]
        inv = Invoice.objects.get(id=invoice_id)
        lines = {row.account.code: (row.debit, row.credit) for row in inv.journal.lines.select_related("account")}
        assert lines["1100"][0] == Decimal("110.00000000")
        assert lines["4000"][1] == Decimal("100.00000000")
        assert lines["2200"][1] == Decimal("10.00000000")

        pay1 = api.post(
            "/api/v1/finance/payments",
            {
                "contact_id": contact["id"], "bank_account_id": cash["id"], "entry_date": "2026-03-10",
                "currency": "USD", "amount": "60",
                "allocations": [{"invoice_id": invoice_id, "amount": "60"}],
            },
            format="json", **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="p1"),
        )
        assert pay1.status_code == 201, pay1.content
        aging_mid = api.get(
            "/api/v1/finance/reports/ar-aging?as_of=2026-03-05", **_h(token, org["id"])
        ).json()["data"]["items"]
        assert aging_mid and Decimal(aging_mid[0]["outstanding"]) == Decimal("110.00")
        pay2 = api.post(
            "/api/v1/finance/payments",
            {
                "contact_id": contact["id"], "bank_account_id": cash["id"], "entry_date": "2026-03-12",
                "currency": "USD", "amount": "80",
                "allocations": [{"invoice_id": invoice_id, "amount": "50"}],
            },
            format="json", **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="p2"),
        )
        assert pay2.status_code == 201, pay2.content
        aging_now = api.get(
            "/api/v1/finance/reports/ar-aging?as_of=2026-03-31", **_h(token, org["id"])
        ).json()["data"]["items"]
        assert aging_now == []
        over = api.post(
            "/api/v1/finance/payments",
            {
                "contact_id": contact["id"], "bank_account_id": cash["id"], "entry_date": "2026-03-13",
                "currency": "USD", "amount": "1",
                "allocations": [{"invoice_id": invoice_id, "amount": "1"}],
            },
            format="json", **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="p3"),
        )
        assert over.json()["error"]["code"] == "over_allocation"

        refund = api.post(
            "/api/v1/finance/refunds",
            {
                "payment_id": pay2.json()["data"]["id"], "amount": "30",
                "bank_account_id": cash["id"], "entry_date": "2026-03-20",
            },
            format="json", **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="r1"),
        )
        assert refund.status_code == 201, refund.content

        inv2 = api.post(
            "/api/v1/finance/invoices",
            {
                "contact_id": contact["id"], "entry_date": "2026-03-21", "currency": "USD",
                "lines": [{"item_id": item["id"], "quantity": "1", "unit_price": "100", "tax_rate_id": tax["id"]}],
            },
            format="json", **_h(token, org["id"]),
        )
        assert inv2.status_code == 201, inv2.content
        posted2 = api.post(
            f"/api/v1/finance/invoices/{inv2.json()['data']['id']}/post", format="json",
            **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="inv-cn"),
        )
        assert posted2.status_code == 200, posted2.content
        cn = api.post(
            "/api/v1/finance/credit-notes",
            {
                "contact_id": contact["id"], "invoice_id": inv2.json()["data"]["id"],
                "entry_date": "2026-03-22", "currency": "USD", "total": "110", "base_total": "110",
                "lines": [{
                    "income_account_id": income["id"], "net": "100", "tax_amount": "10", "total": "110",
                    "base_net": "100", "base_tax": "10", "base_total": "110",
                    "tax_payable_account_id": tax_pay["id"], "description": "credit",
                }],
            },
            format="json", **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="cn1"),
        )
        assert cn.status_code == 201, cn.content
        from apps.finance.models import Allocation
        assert Allocation.objects.filter(invoice_id=inv2.json()["data"]["id"]).exists()

        api.put(
            f"/api/v1/finance/grants/{other_user.id}", {"role_slug": "sales_clerk"},
            format="json", **_h(token, org["id"]),
        )
        clerk = make_token(private_pem, sub="user_clerk_2", sid="sess_2")
        denied = api.post(
            f"/api/v1/finance/invoices/{invoice_id}/post", format="json",
            **_h(clerk, org["id"], HTTP_IDEMPOTENCY_KEY="clerk"),
        )
        assert denied.status_code == 403


@pytest.mark.django_db
def test_fx_invoice_and_settlement(api, rsa_keys, auth_user):
    private_pem, public_pem = rsa_keys
    token = make_token(private_pem)
    with override_settings(CLERK_JWT_KEY=public_pem, **CLERK):
        org, cash, equity, income, ar = create_books(api, token, name="FXCo", currency="USD", month=1, country="US")
        tax, contact, item, tax_pay, advance, cash = _sales_setup(api, token, org, cash, income, ar)
        item_fx = api.post(
            "/api/v1/finance/items",
            {"sku": "EUR", "name": "EU work", "unit_price": "100", "income_account_id": income["id"]},
            format="json", **_h(token, org["id"]),
        ).json()["data"]
        rate = api.post(
            "/api/v1/finance/exchange-rates",
            {"currency": "EUR", "rate": "1.10", "as_of": "2026-04-01"},
            format="json", **_h(token, org["id"]),
        )
        assert rate.status_code == 201, rate.content
        inv = api.post(
            "/api/v1/finance/invoices",
            {
                "contact_id": contact["id"], "entry_date": "2026-04-01", "currency": "EUR",
                "lines": [{"item_id": item_fx["id"], "quantity": "1", "unit_price": "100"}],
            },
            format="json", **_h(token, org["id"]),
        )
        assert inv.status_code == 201, inv.content
        posted = api.post(
            f"/api/v1/finance/invoices/{inv.json()['data']['id']}/post", format="json",
            **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="fx-inv"),
        )
        assert posted.status_code == 200, posted.content
        assert Decimal(posted.json()["data"]["base_total"]) == Decimal("110.00")
        pay = api.post(
            "/api/v1/finance/payments",
            {
                "contact_id": contact["id"], "bank_account_id": cash["id"], "entry_date": "2026-04-10",
                "currency": "EUR", "fx_rate": "1.15", "amount": "100",
                "allocations": [{"invoice_id": inv.json()["data"]["id"], "amount": "100"}],
            },
            format="json", **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="fx-pay"),
        )
        assert pay.status_code == 201, pay.content
        from apps.finance.models import CustomerPayment
        p = CustomerPayment.objects.get(id=pay.json()["data"]["id"])
        by_code = {ln.account.code: (ln.debit, ln.credit) for ln in p.journal.lines.select_related("account")}
        assert by_code["1000"][0] == Decimal("115.00000000")
        assert by_code["1100"][1] == Decimal("110.00000000")
        assert by_code["7100"][1] == Decimal("5.00000000")
        missing = api.post(
            "/api/v1/finance/invoices",
            {
                "contact_id": contact["id"], "entry_date": "2026-05-01", "currency": "GBP",
                "lines": [{"item_id": item_fx["id"], "quantity": "1", "unit_price": "100"}],
            },
            format="json", **_h(token, org["id"]),
        )
        assert missing.status_code == 422
        assert missing.json()["error"]["code"] == "missing_rate"
        zero = api.post(
            "/api/v1/finance/exchange-rates",
            {"currency": "EUR", "rate": "0", "as_of": "2026-06-01"},
            format="json", **_h(token, org["id"]),
        )
        assert zero.json()["error"]["code"] == "validation_error"
