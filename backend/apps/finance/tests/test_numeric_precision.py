from decimal import Decimal

import pytest
from django.test import override_settings

from apps.finance.models import Currency, StockBalance
from apps.finance.models.config import ISO_CURRENCIES
from apps.finance.tests.test_setup_isolation import CLERK, auth_headers, create_books, make_token

pytest_plugins = ["apps.finance.tests.test_setup_isolation"]


def _h(token, org_id, **extra):
    return auth_headers(token, org_id, **extra)


@pytest.mark.django_db
def test_iso_catalogue_is_complete():
    assert len(ISO_CURRENCIES) > 100
    assert Currency.objects.filter(pk="JPY").exists()
    assert Currency.objects.get(pk="JPY").exponent == 0
    assert Currency.objects.get(pk="KWD").exponent == 3
    assert Currency.objects.count() >= 100


@pytest.mark.django_db
def test_jpy_keeps_fractional_quantity(api, rsa_keys, auth_user):
    private_pem, public_pem = rsa_keys
    token = make_token(private_pem)
    with override_settings(CLERK_JWT_KEY=public_pem, **CLERK):
        org, cash, _equity, income, ar = create_books(api, token, name="YenCo", currency="JPY", month=1, country="JP")
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
        inv_acct = api.post(
            "/api/v1/finance/accounts",
            {"code": "1400", "name": "Inventory", "classification": "asset"},
            format="json", **_h(token, org["id"]),
        ).json()["data"]
        cogs = api.post(
            "/api/v1/finance/accounts",
            {"code": "5001", "name": "COGS", "classification": "expense"},
            format="json", **_h(token, org["id"]),
        ).json()["data"]
        api.put(
            "/api/v1/finance/settings",
            {
                "country_code": "JP", "base_currency": "JPY", "fiscal_year_start_month": 1,
                "timezone": "UTC", "locale": "en", "tax_registration_applies": False,
                "ar_account_id": ar["id"], "ap_account_id": ap["id"],
                "inventory_account_id": inv_acct["id"], "cogs_account_id": cogs["id"],
            },
            format="json", **_h(token, org["id"]),
        )
        contact = api.post(
            "/api/v1/finance/contacts", {"name": "YenVendor", "is_vendor": True},
            format="json", **_h(token, org["id"]),
        ).json()["data"]
        item = api.post(
            "/api/v1/finance/items",
            {
                "sku": "BOLT", "name": "Bolt", "kind": "good", "tracked": True, "unit_price": "100",
                "income_account_id": income["id"], "expense_account_id": expense["id"],
            },
            format="json", **_h(token, org["id"]),
        ).json()["data"]
        bill = api.post(
            "/api/v1/finance/bills",
            {
                "contact_id": contact["id"], "entry_date": "2026-06-01", "currency": "JPY",
                "lines": [{"item_id": item["id"], "quantity": "1.5", "unit_price": "100"}],
            },
            format="json", **_h(token, org["id"]),
        )
        posted = api.post(
            f"/api/v1/finance/bills/{bill.json()['data']['id']}/post", format="json",
            **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="jpy-bill"),
        )
        assert posted.status_code == 200, posted.content
        bal = StockBalance.objects.get(item_id=item["id"])
        assert bal.qty == Decimal("1.5")
        from apps.finance.services.stock import audit_qty_currency_rounding
        from apps.tenancy.models import Organization

        hits = audit_qty_currency_rounding(org=Organization.objects.get(id=org["id"]))
        assert any(h["item_id"] == item["id"] for h in hits)
