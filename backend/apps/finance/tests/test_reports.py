from decimal import Decimal

import pytest
from django.test import override_settings

from apps.finance.tests.test_setup_isolation import CLERK, auth_headers, create_books, make_token

pytest_plugins = ["apps.finance.tests.test_setup_isolation"]


def _h(token, org_id, **extra):
    return auth_headers(token, org_id, **extra)


def _post_je(api, token, org_id, key, entry_date, lines, source="manual"):
    draft = api.post(
        "/api/v1/finance/journals",
        {"entry_date": entry_date, "source_type": source, "lines": lines},
        format="json", **_h(token, org_id),
    )
    assert draft.status_code == 201, draft.content
    posted = api.post(
        f"/api/v1/finance/journals/{draft.json()['data']['id']}/post",
        {"version": 1},
        format="json", **_h(token, org_id, HTTP_IDEMPOTENCY_KEY=key),
    )
    assert posted.status_code == 200, posted.content
    return posted


@pytest.mark.django_db
def test_cash_flow_tags_comparative(api, rsa_keys, auth_user):
    private_pem, public_pem = rsa_keys
    token = make_token(private_pem)
    with override_settings(CLERK_JWT_KEY=public_pem, **CLERK):
        org, cash, equity, income, _ar = create_books(
            api, token, name="ReportCo", currency="USD", month=1, country="US"
        )
        oid = org["id"]
        api.patch(
            f"/api/v1/finance/accounts/{cash['id']}",
            {"cashflow_kind": "cash", "version": 1},
            format="json", **_h(token, oid),
        )
        api.patch(
            f"/api/v1/finance/accounts/{equity['id']}",
            {"cashflow_kind": "financing", "version": 1},
            format="json", **_h(token, oid),
        )
        recv = api.post(
            "/api/v1/finance/accounts",
            {"code": "1200", "name": "Receivable", "classification": "asset", "cashflow_kind": "operating"},
            format="json", **_h(token, oid),
        ).json()["data"]
        ppe = api.post(
            "/api/v1/finance/accounts",
            {"code": "1600", "name": "PPE", "classification": "asset", "cashflow_kind": "investing"},
            format="json", **_h(token, oid),
        ).json()["data"]
        expense = api.post(
            "/api/v1/finance/accounts",
            {"code": "5000", "name": "Other", "classification": "expense"},
            format="json", **_h(token, oid),
        ).json()["data"]
        tag = api.post("/api/v1/finance/tags", {"name": "sales"}, format="json", **_h(token, oid))
        assert tag.status_code == 201, tag.content
        tag_id = tag.json()["data"]["id"]

        _post_je(api, token, oid, "cf-open", "2026-01-01", [
            {"account_id": cash["id"], "debit": "1000", "credit": "0"},
            {"account_id": equity["id"], "debit": "0", "credit": "1000"},
        ], source="opening")
        _post_je(api, token, oid, "cf-sale", "2026-02-01", [
            {"account_id": recv["id"], "debit": "100", "credit": "0"},
            {"account_id": income["id"], "debit": "0", "credit": "100", "tag_id": tag_id},
        ])
        _post_je(api, token, oid, "cf-collect", "2026-03-01", [
            {"account_id": cash["id"], "debit": "80", "credit": "0"},
            {"account_id": recv["id"], "debit": "0", "credit": "80"},
        ])
        _post_je(api, token, oid, "cf-ppe", "2026-04-01", [
            {"account_id": ppe["id"], "debit": "200", "credit": "0"},
            {"account_id": cash["id"], "debit": "0", "credit": "200"},
        ])

        cfs = api.get("/api/v1/finance/reports/cash-flow?from=2026-01-01&to=2026-12-31", **_h(token, oid))
        assert cfs.status_code == 200, cfs.content
        data = cfs.json()["data"]
        assert Decimal(data["operating"]) == Decimal("80.00")
        assert Decimal(data["investing"]) == Decimal("-200.00")
        assert Decimal(data["financing"]) == Decimal("1000.00")
        assert Decimal(data["net_change"]) == Decimal(data["cash_change"]) == Decimal("880.00")

        pnl = api.get(
            "/api/v1/finance/reports/profit-loss?from=2026-01-01&to=2026-12-31&compare_from=2025-01-01&compare_to=2025-12-31",
            **_h(token, oid),
        )
        assert pnl.status_code == 200, pnl.content
        assert Decimal(pnl.json()["data"]["net_income"]) == Decimal("100.00")
        assert Decimal(pnl.json()["data"]["prior"]["net_income"]) == Decimal("0.00")

        _post_je(api, token, oid, "cf-exp", "2026-05-01", [
            {"account_id": expense["id"], "debit": "10", "credit": "0"},
            {"account_id": cash["id"], "debit": "0", "credit": "10"},
        ])
        tagged = api.get(
            f"/api/v1/finance/reports/profit-loss?from=2026-01-01&to=2026-12-31&tag_id={tag_id}",
            **_h(token, oid),
        ).json()["data"]
        full = api.get(
            "/api/v1/finance/reports/profit-loss?from=2026-01-01&to=2026-12-31", **_h(token, oid)
        ).json()["data"]
        assert Decimal(tagged["income_total"]) == Decimal("100.00")
        assert Decimal(tagged["expense_total"]) == Decimal("0.00")
        assert Decimal(full["expense_total"]) == Decimal("10.00")

        bs = api.get(
            "/api/v1/finance/reports/balance-sheet?as_of=2026-12-31&compare_as_of=2025-12-31",
            **_h(token, oid),
        )
        assert bs.status_code == 200, bs.content
        assert bs.json()["data"]["asset_total"] == bs.json()["data"]["liability_and_equity_total"]
        assert Decimal(bs.json()["data"]["prior"]["asset_total"]) == Decimal("0.00")

        tb = api.get(
            "/api/v1/finance/reports/trial-balance?from=2026-02-01&to=2026-12-31", **_h(token, oid)
        ).json()["data"]["items"]
        cash_tb = next(x for x in tb if x["code"] == "1000")
        assert Decimal(cash_tb["opening_debit"]) == Decimal("1000.00")
        assert Decimal(cash_tb["debit"]) - Decimal(cash_tb["credit"]) + Decimal(cash_tb["opening_debit"]) - Decimal(cash_tb["opening_credit"]) == Decimal(cash_tb["closing_debit"]) - Decimal(cash_tb["closing_credit"])
        tax = api.get(
            "/api/v1/finance/reports/tax-summary?from=2026-01-01&to=2026-12-31", **_h(token, oid)
        )
        assert tax.status_code == 200, tax.content
        assert "total" in tax.json()["data"]
        assert "line_count" in cash_tb
        csv_tb = api.get(
            "/api/v1/finance/reports/trial-balance?from=2026-02-01&to=2026-12-31&export=csv", **_h(token, oid)
        )
        assert csv_tb.status_code == 200
        assert b"opening_debit" in csv_tb.content
        eq = api.get(
            "/api/v1/finance/reports/equity-movement?from=2026-01-01&to=2026-12-31", **_h(token, oid)
        )
        assert eq.status_code == 200, eq.content
        assert "closing_equity" in eq.json()["data"]
        dumped = api.get("/api/v1/finance/export", **_h(token, oid))
        assert dumped.status_code == 200, dumped.content
        assert dumped.json()["data"]["settings"]["base_currency"] == "USD"
