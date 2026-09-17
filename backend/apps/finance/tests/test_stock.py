from decimal import Decimal

import pytest
from django.db.models import Sum
from django.test import override_settings

from apps.finance.models import JournalLine, StockBalance
from apps.finance.tests.test_purchases import _purchase_setup
from apps.finance.tests.test_setup_isolation import CLERK, auth_headers, create_books, make_token

pytest_plugins = ["apps.finance.tests.test_setup_isolation"]


def _h(token, org_id, **extra):
    return auth_headers(token, org_id, **extra)


@pytest.mark.django_db
def test_moving_average_issue_transfer_adjust(api, rsa_keys, auth_user):
    private_pem, public_pem = rsa_keys
    token = make_token(private_pem)
    with override_settings(CLERK_JWT_KEY=public_pem, **CLERK):
        org, cash, equity, income, ar = create_books(api, token, name="StockCo", currency="USD", month=1, country="US")
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
        settings = api.put(
            "/api/v1/finance/settings",
            {
                "country_code": "US", "base_currency": "USD", "fiscal_year_start_month": 1,
                "timezone": "UTC", "locale": "en", "tax_registration_applies": False,
                "ar_account_id": ar["id"], "ap_account_id": ap["id"],
                "inventory_account_id": inv_acct["id"], "cogs_account_id": cogs["id"],
            },
            format="json", **_h(token, org["id"]),
        )
        assert settings.status_code == 200, settings.content
        widget = api.post(
            "/api/v1/finance/items",
            {
                "sku": "WID", "name": "Widget", "kind": "good", "tracked": True, "unit_price": "20",
                "income_account_id": income["id"], "expense_account_id": expense["id"], "tax_rate_id": tax["id"],
            },
            format="json", **_h(token, org["id"]),
        )
        assert widget.status_code == 201, widget.content
        item = widget.json()["data"]
        assert item["tracked"] is True
        bill = api.post(
            "/api/v1/finance/bills",
            {
                "contact_id": contact["id"], "entry_date": "2026-06-01", "currency": "USD",
                "lines": [{"item_id": item["id"], "quantity": "10", "unit_price": "8", "tax_rate_id": tax["id"]}],
            },
            format="json", **_h(token, org["id"]),
        )
        assert bill.status_code == 201, bill.content
        posted_bill = api.post(
            f"/api/v1/finance/bills/{bill.json()['data']['id']}/post", format="json",
            **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="st-bill"),
        )
        assert posted_bill.status_code == 200, posted_bill.content
        bal = StockBalance.objects.get(item_id=item["id"])
        assert bal.qty == Decimal("10")
        assert bal.value == Decimal("80.00")
        debit = JournalLine.objects.filter(account_id=inv_acct["id"]).aggregate(s=Sum("debit"))["s"]
        assert Decimal(debit) == Decimal("80.00")

        invoice = api.post(
            "/api/v1/finance/invoices",
            {
                "contact_id": contact["id"], "entry_date": "2026-06-10", "currency": "USD",
                "lines": [{"item_id": item["id"], "quantity": "4", "unit_price": "20", "tax_rate_id": tax["id"]}],
            },
            format="json", **_h(token, org["id"]),
        )
        sold = api.post(
            f"/api/v1/finance/invoices/{invoice.json()['data']['id']}/post", format="json",
            **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="st-inv"),
        )
        assert sold.status_code == 200, sold.content
        bal.refresh_from_db()
        assert bal.qty == Decimal("6")
        assert bal.value == Decimal("48.00")
        cogs_amt = JournalLine.objects.filter(account_id=cogs["id"], debit__gt=0).aggregate(s=Sum("debit"))["s"]
        assert Decimal(cogs_amt) == Decimal("32.00")

        over = api.post(
            "/api/v1/finance/invoices",
            {
                "contact_id": contact["id"], "entry_date": "2026-06-11", "currency": "USD",
                "lines": [{"item_id": item["id"], "quantity": "7", "unit_price": "20", "tax_rate_id": tax["id"]}],
            },
            format="json", **_h(token, org["id"]),
        )
        blocked = api.post(
            f"/api/v1/finance/invoices/{over.json()['data']['id']}/post", format="json",
            **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="st-over"),
        )
        assert blocked.json()["error"]["code"] == "negative_stock"
        bal.refresh_from_db()
        assert bal.qty == Decimal("6")

        warehouses = api.get("/api/v1/finance/warehouses", **_h(token, org["id"]))
        assert warehouses.status_code == 200, warehouses.content
        main = next(w for w in warehouses.json()["data"]["items"] if w["name"] == "Main")
        other = api.post(
            "/api/v1/finance/warehouses", {"name": "West"}, format="json", **_h(token, org["id"])
        )
        assert other.status_code == 201, other.content
        moved = api.post(
            "/api/v1/finance/stock/transfer",
            {
                "from_warehouse_id": main["id"], "to_warehouse_id": other.json()["data"]["id"],
                "item_id": item["id"], "quantity": "2", "entry_date": "2026-06-12",
            },
            format="json", **_h(token, org["id"]),
        )
        assert moved.status_code == 200, moved.content
        west = StockBalance.objects.get(warehouse_id=other.json()["data"]["id"])
        assert west.qty == Decimal("2")
        assert west.value == Decimal("16.00")
        main_bal = StockBalance.objects.get(warehouse_id=main["id"])
        assert main_bal.qty == Decimal("4")

        adj = api.post(
            "/api/v1/finance/stock/adjust",
            {
                "warehouse_id": main["id"], "item_id": item["id"], "quantity": "-1",
                "entry_date": "2026-06-13",
            },
            format="json", **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="st-adj"),
        )
        assert adj.status_code == 200, adj.content
        val = api.get("/api/v1/finance/reports/inventory-valuation", **_h(token, org["id"]))
        assert val.status_code == 200, val.content
        assert Decimal(val.json()["data"]["stock_total"]) == Decimal(val.json()["data"]["gl_inventory"])
        assert Decimal(val.json()["data"]["stock_total"]) == Decimal("40.00")
