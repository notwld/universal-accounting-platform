from decimal import Decimal

import pytest
from django.test import override_settings

from apps.finance.models import InvoiceLine, StockBalance
from apps.finance.tests.test_purchases import _purchase_setup
from apps.finance.tests.test_setup_isolation import CLERK, auth_headers, create_books, make_token

pytest_plugins = ["apps.finance.tests.test_setup_isolation"]


def _h(token, org_id, **extra):
    return auth_headers(token, org_id, **extra)


@pytest.mark.django_db
def test_partial_credit_restores_only_credited_qty(api, rsa_keys, auth_user):
    private_pem, public_pem = rsa_keys
    token = make_token(private_pem)
    with override_settings(CLERK_JWT_KEY=public_pem, **CLERK):
        org, cash, equity, income, ar = create_books(api, token, name="CreditCo", currency="USD", month=1, country="US")
        tax, contact, _part, tax_pay, expense, ap, cash = _purchase_setup(api, token, org, cash, income)
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
                "country_code": "US", "base_currency": "USD", "fiscal_year_start_month": 1,
                "timezone": "UTC", "locale": "en", "tax_registration_applies": False,
                "ar_account_id": ar["id"], "ap_account_id": ap["id"],
                "inventory_account_id": inv_acct["id"], "cogs_account_id": cogs["id"],
            },
            format="json", **_h(token, org["id"]),
        )
        item = api.post(
            "/api/v1/finance/items",
            {
                "sku": "RET", "name": "Returnable", "kind": "good", "tracked": True, "unit_price": "20",
                "income_account_id": income["id"], "expense_account_id": expense["id"], "tax_rate_id": tax["id"],
            },
            format="json", **_h(token, org["id"]),
        ).json()["data"]
        bill = api.post(
            "/api/v1/finance/bills",
            {
                "contact_id": contact["id"], "entry_date": "2026-06-01", "currency": "USD",
                "lines": [{"item_id": item["id"], "quantity": "10", "unit_price": "8", "tax_rate_id": tax["id"]}],
            },
            format="json", **_h(token, org["id"]),
        )
        api.post(
            f"/api/v1/finance/bills/{bill.json()['data']['id']}/post", format="json",
            **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="cr-bill"),
        )
        invoice = api.post(
            "/api/v1/finance/invoices",
            {
                "contact_id": contact["id"], "entry_date": "2026-06-10", "currency": "USD",
                "lines": [{"item_id": item["id"], "quantity": "4", "unit_price": "20", "tax_rate_id": tax["id"]}],
            },
            format="json", **_h(token, org["id"]),
        )
        posted = api.post(
            f"/api/v1/finance/invoices/{invoice.json()['data']['id']}/post", format="json",
            **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="cr-inv"),
        )
        assert posted.status_code == 200, posted.content
        src = InvoiceLine.objects.get(invoice_id=invoice.json()["data"]["id"])
        cn = api.post(
            "/api/v1/finance/credit-notes",
            {
                "contact_id": contact["id"], "invoice_id": invoice.json()["data"]["id"],
                "entry_date": "2026-06-11", "currency": "USD", "total": "22", "base_total": "22",
                "lines": [{
                    "invoice_line_id": src.id, "item_id": item["id"], "quantity": "1",
                    "income_account_id": income["id"], "net": "20", "tax_amount": "2", "total": "22",
                    "base_net": "20", "base_tax": "2", "base_total": "22",
                    "tax_payable_account_id": tax_pay["id"], "description": "return",
                }],
            },
            format="json", **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="cr-cn"),
        )
        assert cn.status_code == 201, cn.content
        bal = StockBalance.objects.get(item_id=item["id"])
        assert bal.qty == Decimal("7")
        price_only = api.post(
            "/api/v1/finance/credit-notes",
            {
                "contact_id": contact["id"], "invoice_id": invoice.json()["data"]["id"],
                "entry_date": "2026-06-12", "currency": "USD", "total": "5", "base_total": "5",
                "lines": [{
                    "invoice_line_id": src.id, "item_id": item["id"], "quantity": "0", "price_only": True,
                    "income_account_id": income["id"], "net": "5", "total": "5",
                    "base_net": "5", "base_total": "5", "description": "price",
                }],
            },
            format="json", **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="cr-price"),
        )
        assert price_only.status_code == 201, price_only.content
        bal.refresh_from_db()
        assert bal.qty == Decimal("7")
        second = api.post(
            "/api/v1/finance/credit-notes",
            {
                "contact_id": contact["id"], "invoice_id": invoice.json()["data"]["id"],
                "entry_date": "2026-06-12", "currency": "USD", "total": "22", "base_total": "22",
                "lines": [{
                    "invoice_line_id": src.id, "item_id": item["id"], "quantity": "1",
                    "income_account_id": income["id"], "net": "20", "tax_amount": "2", "total": "22",
                    "base_net": "20", "base_tax": "2", "base_total": "22",
                    "tax_payable_account_id": tax_pay["id"], "description": "return2",
                }],
            },
            format="json", **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="cr-cn2"),
        )
        assert second.status_code == 201, second.content
        bal.refresh_from_db()
        assert bal.qty == Decimal("8")
        over = api.post(
            "/api/v1/finance/credit-notes",
            {
                "contact_id": contact["id"], "invoice_id": invoice.json()["data"]["id"],
                "entry_date": "2026-06-13", "currency": "USD", "total": "22", "base_total": "22",
                "lines": [{
                    "invoice_line_id": src.id, "item_id": item["id"], "quantity": "4",
                    "income_account_id": income["id"], "net": "20", "total": "22",
                    "base_net": "20", "base_total": "22", "description": "over",
                }],
            },
            format="json", **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="cr-over"),
        )
        assert over.json()["error"]["code"] == "over_allocation"

        other, _c, _e, other_income, _ar = create_books(api, token, name="OtherCo", currency="USD", month=1, country="US")
        stolen_item = api.post(
            "/api/v1/finance/items",
            {"sku": "X", "name": "X", "income_account_id": other_income["id"]},
            format="json", **_h(token, other["id"]),
        ).json()["data"]
        stolen = api.post(
            "/api/v1/finance/credit-notes",
            {
                "contact_id": contact["id"], "entry_date": "2026-06-14", "currency": "USD",
                "total": "1", "base_total": "1",
                "lines": [{
                    "item_id": stolen_item["id"], "income_account_id": income["id"],
                    "net": "1", "total": "1", "base_net": "1", "base_total": "1",
                }],
            },
            format="json", **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="cr-xitem"),
        )
        assert stolen.json()["error"]["code"] == "cross_organization"
