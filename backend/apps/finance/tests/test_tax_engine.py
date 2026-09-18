from decimal import Decimal

import pytest
from django.test import override_settings

from apps.finance.models import JournalLine, TaxRate
from apps.finance.tests.test_purchases import _purchase_setup
from apps.finance.tests.test_setup_isolation import CLERK, auth_headers, create_books, make_token

pytest_plugins = ["apps.finance.tests.test_setup_isolation"]


def _h(token, org_id, **extra):
    return auth_headers(token, org_id, **extra)


@pytest.mark.django_db
def test_compound_reverse_withholding_and_country_pack(api, rsa_keys, auth_user):
    private_pem, public_pem = rsa_keys
    token = make_token(private_pem)
    with override_settings(CLERK_JWT_KEY=public_pem, **CLERK):
        org, cash, equity, income, ar = create_books(api, token, name="TaxCo", currency="USD", month=1, country="US")
        tax, contact, item, tax_pay, expense, ap, cash = _purchase_setup(api, token, org, cash, income)
        recv = api.post(
            "/api/v1/finance/accounts",
            {"code": "1300", "name": "Input VAT", "classification": "asset"},
            format="json", **_h(token, org["id"]),
        ).json()["data"]
        gst = TaxRate.objects.get(id=tax["id"])
        compound = api.post(
            "/api/v1/finance/tax-rates",
            {
                "name": "PST", "rate": "0.02", "method": "exclusive", "kind": "standard",
                "payable_account_id": tax_pay["id"], "compound_on_id": gst.id, "compound_base": "running",
                "valid_from": "2026-01-01",
            },
            format="json", **_h(token, org["id"]),
        )
        assert compound.status_code == 201, compound.content
        item_c = api.post(
            "/api/v1/finance/items",
            {
                "sku": "C", "name": "Compound", "unit_price": "200",
                "income_account_id": income["id"], "expense_account_id": expense["id"],
                "tax_rate_id": compound.json()["data"]["id"],
            },
            format="json", **_h(token, org["id"]),
        ).json()["data"]
        bill = api.post(
            "/api/v1/finance/bills",
            {
                "contact_id": contact["id"], "entry_date": "2026-06-01", "currency": "USD",
                "lines": [{"item_id": item_c["id"], "quantity": "1", "unit_price": "200"}],
            },
            format="json", **_h(token, org["id"]),
        )
        assert bill.status_code == 201, bill.content
        # 200 + 10% = 220; 2% of 220 = 4.40; total 224.40
        assert Decimal(bill.json()["data"]["total"]) == Decimal("224.40")
        posted = api.post(
            f"/api/v1/finance/bills/{bill.json()['data']['id']}/post", format="json",
            **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="tax-comp"),
        )
        assert posted.status_code == 200, posted.content

        rc = api.post(
            "/api/v1/finance/tax-rates",
            {
                "name": "RC 19", "rate": "0.19", "kind": "reverse_charge",
                "payable_account_id": tax_pay["id"], "recoverable_account_id": recv["id"],
                "valid_from": "2026-01-01",
            },
            format="json", **_h(token, org["id"]),
        ).json()["data"]
        item_rc = api.post(
            "/api/v1/finance/items",
            {
                "sku": "RC", "name": "Import service", "unit_price": "10000",
                "income_account_id": income["id"], "expense_account_id": expense["id"],
                "tax_rate_id": rc["id"],
            },
            format="json", **_h(token, org["id"]),
        ).json()["data"]
        rc_bill = api.post(
            "/api/v1/finance/bills",
            {
                "contact_id": contact["id"], "entry_date": "2026-07-01", "currency": "USD",
                "lines": [{"item_id": item_rc["id"], "quantity": "1", "unit_price": "10000"}],
            },
            format="json", **_h(token, org["id"]),
        )
        assert Decimal(rc_bill.json()["data"]["total"]) == Decimal("10000.00")
        rc_posted = api.post(
            f"/api/v1/finance/bills/{rc_bill.json()['data']['id']}/post", format="json",
            **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="tax-rc"),
        )
        assert rc_posted.status_code == 200, rc_posted.content
        by_acct = {}
        for ln in JournalLine.objects.filter(journal_id=rc_posted.json()["data"]["journal_id"]):
            by_acct.setdefault(ln.account_id, Decimal("0"))
            by_acct[ln.account_id] += ln.debit - ln.credit
        assert by_acct[ap["id"]] == Decimal("-10000.00")
        assert by_acct[recv["id"]] == Decimal("1900.00")
        assert by_acct[tax_pay["id"]] == Decimal("-1900.00")

        wht = api.post(
            "/api/v1/finance/tax-rates",
            {
                "name": "WHT 1", "rate": "0.01", "kind": "withholding",
                "payable_account_id": tax_pay["id"], "valid_from": "2026-01-01",
            },
            format="json", **_h(token, org["id"]),
        ).json()["data"]
        item_w = api.post(
            "/api/v1/finance/items",
            {
                "sku": "W", "name": "Contractor", "unit_price": "100000",
                "income_account_id": income["id"], "expense_account_id": expense["id"],
                "tax_rate_id": wht["id"],
            },
            format="json", **_h(token, org["id"]),
        ).json()["data"]
        wbill = api.post(
            "/api/v1/finance/bills",
            {
                "contact_id": contact["id"], "entry_date": "2026-08-01", "currency": "USD",
                "lines": [{"item_id": item_w["id"], "quantity": "1", "unit_price": "100000"}],
            },
            format="json", **_h(token, org["id"]),
        )
        assert Decimal(wbill.json()["data"]["total"]) == Decimal("99000.00")
        w_posted = api.post(
            f"/api/v1/finance/bills/{wbill.json()['data']['id']}/post", format="json",
            **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="tax-wht"),
        )
        assert w_posted.status_code == 200, w_posted.content
        by_acct = {}
        for ln in JournalLine.objects.filter(journal_id=w_posted.json()["data"]["journal_id"]):
            by_acct.setdefault(ln.account_id, Decimal("0"))
            by_acct[ln.account_id] += ln.debit - ln.credit
        assert by_acct[ap["id"]] == Decimal("-99000.00")
        assert by_acct[tax_pay["id"]] == Decimal("-1000.00")
        assert by_acct[expense["id"]] == Decimal("100000.00")

        blocked = api.post("/api/v1/finance/country-packs", {"country_code": "generic"}, format="json", **_h(token, org["id"]))
        assert blocked.json()["error"]["code"] == "validation_error"
        enabled = api.post(
            "/api/v1/finance/country-packs",
            {"country_code": "generic", "reviewed": True},
            format="json", **_h(token, org["id"]),
        )
        assert enabled.status_code == 201, enabled.content
        listed = api.get("/api/v1/finance/country-packs", **_h(token, org["id"])).json()["data"]["items"]
        assert any(x["code"] == "generic" and x["enabled"] for x in listed)
        ae = api.post(
            "/api/v1/finance/country-packs",
            {"country_code": "AE", "reviewed": True},
            format="json", **_h(token, org["id"]),
        )
        assert ae.json()["error"]["code"] == "validation_error"
