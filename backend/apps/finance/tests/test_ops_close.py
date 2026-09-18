import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext

from apps.finance.models import FinanceWebhookDelivery, JournalLine
from apps.finance.services.webhooks import sign
from apps.finance.tests.test_reports import _post_je
from apps.finance.tests.test_sales import _sales_setup
from apps.finance.tests.test_setup_isolation import CLERK, auth_headers, create_books, make_token

pytest_plugins = ["apps.finance.tests.test_setup_isolation"]
GOLDEN = json.loads((Path(__file__).parent / "golden" / "month.json").read_text(encoding="utf-8"))


def _h(token, org_id, **extra):
    return auth_headers(token, org_id, **extra)


@pytest.mark.django_db
def test_accrual_fx_cutover_webhooks_pdf_golden(api, rsa_keys, auth_user):
    private_pem, public_pem = rsa_keys
    token = make_token(private_pem)
    with override_settings(CLERK_JWT_KEY=public_pem, **CLERK):
        org, cash, equity, income, ar = create_books(api, token, name="OpsCo", currency="USD", month=1, country="US")
        oid = org["id"]
        tax, contact, item, tax_pay, advance, cash = _sales_setup(api, token, org, cash, income, ar)
        expense = api.post(
            "/api/v1/finance/accounts",
            {"code": "5100", "name": "Accrued exp", "classification": "expense"},
            format="json", **_h(token, oid),
        ).json()["data"]
        liab = api.post(
            "/api/v1/finance/accounts",
            {"code": "2500", "name": "Accrued liab", "classification": "liability"},
            format="json", **_h(token, oid),
        ).json()["data"]
        adj = api.post(
            "/api/v1/finance/adjustments",
            {
                "kind": "accrual", "debit_account_id": expense["id"], "credit_account_id": liab["id"],
                "amount": "50", "entry_date": "2026-01-31", "reverse_on": "2026-02-01",
            },
            format="json", **_h(token, oid, HTTP_IDEMPOTENCY_KEY="adj-1"),
        )
        assert adj.status_code == 201, adj.content
        rev = api.post(
            "/api/v1/finance/adjustments/reverse",
            {"as_of": "2026-02-01"},
            format="json", **_h(token, oid, HTTP_IDEMPOTENCY_KEY="adj-rev"),
        )
        assert rev.status_code == 200, rev.content
        net = Decimal("0")
        for ln in JournalLine.objects.filter(account_id=expense["id"]):
            net += ln.debit - ln.credit
        assert net == Decimal("0")

        item_fx = api.post(
            "/api/v1/finance/items",
            {"sku": "EU", "name": "EU", "unit_price": "100", "income_account_id": income["id"]},
            format="json", **_h(token, oid),
        ).json()["data"]
        api.post(
            "/api/v1/finance/exchange-rates",
            {"currency": "EUR", "rate": "1.00", "as_of": "2026-06-01"},
            format="json", **_h(token, oid),
        )
        api.post(
            "/api/v1/finance/exchange-rates",
            {"currency": "EUR", "rate": "1.10", "as_of": "2026-06-30"},
            format="json", **_h(token, oid),
        )
        inv = api.post(
            "/api/v1/finance/invoices",
            {
                "contact_id": contact["id"], "entry_date": "2026-06-01", "currency": "EUR",
                "lines": [{"item_id": item_fx["id"], "quantity": "1", "unit_price": "100"}],
            },
            format="json", **_h(token, oid),
        )
        assert inv.status_code == 201, inv.content
        posted = api.post(
            f"/api/v1/finance/invoices/{inv.json()['data']['id']}/post",
            format="json", **_h(token, oid, HTTP_IDEMPOTENCY_KEY="fx-open"),
        )
        assert posted.status_code == 200, posted.content
        reval = api.post(
            "/api/v1/finance/fx/revalue",
            {"as_of": "2026-06-30"},
            format="json", **_h(token, oid, HTTP_IDEMPOTENCY_KEY="fx-reval"),
        )
        assert reval.status_code == 200, reval.content
        assert Decimal(reval.json()["data"]["amount"]) == Decimal("10.00")
        by_acct = {}
        for ln in JournalLine.objects.filter(journal_id=reval.json()["data"]["journal_id"]):
            by_acct.setdefault(ln.account_id, Decimal("0"))
            by_acct[ln.account_id] += ln.debit - ln.credit
        assert by_acct[ar["id"]] == Decimal("10.00")

        org2, cash2, equity2, *_ = create_books(api, token, name="CutCo", currency="USD", month=1, country="US")
        oid2 = org2["id"]
        dry = api.post(
            "/api/v1/finance/cutover",
            {
                "mode": "openings", "stage": "settings_chart", "dry_run": True,
                "rows": [{"code": "1200", "name": "Other", "classification": "asset"}],
            },
            format="json", **_h(token, oid2),
        )
        assert dry.json()["data"]["dry_run"] is True
        assert api.get("/api/v1/finance/accounts", **_h(token, oid2)).json()["data"]["items"]
        codes = {x["code"] for x in api.get("/api/v1/finance/accounts", **_h(token, oid2)).json()["data"]["items"]}
        assert "1200" not in codes
        applied = api.post(
            "/api/v1/finance/cutover",
            {
                "mode": "openings", "stage": "settings_chart", "dry_run": False,
                "rows": [{"code": "1200", "name": "Other", "classification": "asset"}],
            },
            format="json", **_h(token, oid2),
        )
        assert applied.status_code == 201, applied.content
        blocked = api.post(
            "/api/v1/finance/cutover",
            {"mode": "history", "stage": "masters", "rows": []},
            format="json", **_h(token, oid2),
        )
        assert blocked.json()["error"]["code"] == "validation_error"

        org3, *_ = create_books(api, token, name="HistCo", currency="USD", month=1, country="US")
        api.post(
            "/api/v1/finance/cutover",
            {"mode": "history", "stage": "settings_chart", "rows": []},
            format="json", **_h(token, org3["id"]),
        )
        api.post(
            "/api/v1/finance/cutover",
            {"mode": "history", "stage": "masters", "rows": []},
            format="json", **_h(token, org3["id"]),
        )
        hist_open = api.post(
            "/api/v1/finance/cutover",
            {
                "mode": "history", "stage": "balances",
                "rows": [{"account_code": "1000", "debit": "10", "credit": "0"}],
            },
            format="json", **_h(token, org3["id"]),
        )
        assert hist_open.json()["error"]["code"] == "validation_error"

        hook = api.post(
            "/api/v1/finance/webhooks",
            {"url": "https://example.test/hook", "secret": "s" * 32, "events": ["invoice.posted"]},
            format="json", **_h(token, oid),
        )
        assert hook.status_code == 201, hook.content
        inv2 = api.post(
            "/api/v1/finance/invoices",
            {
                "contact_id": contact["id"], "entry_date": "2026-07-01", "currency": "USD",
                "lines": [{"item_id": item["id"], "quantity": "1", "unit_price": "10"}],
            },
            format="json", **_h(token, oid),
        )
        api.post(
            f"/api/v1/finance/invoices/{inv2.json()['data']['id']}/post",
            format="json", **_h(token, oid, HTTP_IDEMPOTENCY_KEY="wh-inv"),
        )
        fail = MagicMock(status_code=500)
        with patch("httpx.post", return_value=fail) as mocked:
            from django.utils import timezone as tz

            for _ in range(3):
                FinanceWebhookDelivery.objects.filter(organization_id=oid, status="pending").update(next_attempt=tz.now())
                api.post("/api/v1/finance/webhooks/deliver", format="json", **_h(token, oid))
            assert mocked.call_count == 3
            body = mocked.call_args.kwargs["content"]
            headers = mocked.call_args.kwargs["headers"]
            assert headers["X-Finance-Signature"] == sign("s" * 32, body)
        assert FinanceWebhookDelivery.objects.filter(organization_id=oid, status="dead").exists()

        pdf = api.get(
            "/api/v1/finance/reports/trial-balance?from=2026-01-01&to=2026-12-31&export=pdf",
            **_h(token, oid),
        )
        assert pdf.status_code == 200
        assert pdf.content.startswith(b"%PDF")

        org_g, cash_g, equity_g, *_ = create_books(api, token, name="GoldCo", currency="USD", month=1, country="US")
        _post_je(api, token, org_g["id"], "gold-open", "2026-01-01", [
            {"account_id": cash_g["id"], "debit": "1000", "credit": "0"},
            {"account_id": equity_g["id"], "debit": "0", "credit": "1000"},
        ], source="opening")
        tb = api.get(
            f"/api/v1/finance/reports/trial-balance?from={GOLDEN['from']}&to={GOLDEN['to']}",
            **_h(token, org_g["id"]),
        ).json()["data"]["items"]
        by_code = {x["code"]: x for x in tb}
        for code, expected in GOLDEN["trial_balance"].items():
            assert Decimal(by_code[code]["closing_debit"]) == Decimal(expected["closing_debit"])
            assert Decimal(by_code[code]["closing_credit"]) == Decimal(expected["closing_credit"])

        with CaptureQueriesContext(connection) as ctx:
            api.get(
                "/api/v1/finance/reports/trial-balance?from=2026-01-01&to=2026-12-31",
                **_h(token, oid),
            )
        assert len(ctx) < 80

        metrics = api.get("/api/v1/finance/ops/metrics", **_h(token, oid))
        assert metrics.status_code == 200
        assert "webhooks_dead" in metrics.json()["data"]
