from decimal import Decimal

import pytest
from django.test import override_settings

from apps.finance.models import JournalEntry
from apps.finance.tests.test_reports import _post_je
from apps.finance.tests.test_setup_isolation import CLERK, auth_headers, create_books, make_token

pytest_plugins = ["apps.finance.tests.test_setup_isolation"]


def _h(token, org_id, **extra):
    return auth_headers(token, org_id, **extra)


@pytest.mark.django_db
def test_year_end_close_zeros_income_to_retained_earnings(api, rsa_keys, auth_user):
    private_pem, public_pem = rsa_keys
    token = make_token(private_pem)
    with override_settings(CLERK_JWT_KEY=public_pem, **CLERK):
        org, cash, equity, income, _ar = create_books(
            api, token, name="CloseCo", currency="USD", month=1, country="US"
        )
        oid = org["id"]
        api.put(
            "/api/v1/finance/settings",
            {
                "country_code": "US", "base_currency": "USD", "fiscal_year_start_month": 1,
                "timezone": "UTC", "locale": "en", "tax_registration_applies": False,
                "retained_earnings_account_id": equity["id"],
            },
            format="json", **_h(token, oid),
        )
        leftover = api.post(
            "/api/v1/finance/journals",
            {
                "entry_date": "2026-06-01",
                "lines": [
                    {"account_id": cash["id"], "debit": "1", "credit": "0"},
                    {"account_id": income["id"], "debit": "0", "credit": "1"},
                ],
            },
            format="json", **_h(token, oid),
        )
        period = api.post(
            "/api/v1/finance/periods",
            {"start_on": "2026-01-01", "end_on": "2026-12-31"},
            format="json", **_h(token, oid),
        ).json()["data"]
        blocked = api.post(
            f"/api/v1/finance/periods/{period['id']}/lock",
            {"year_end": True},
            format="json", **_h(token, oid, HTTP_IDEMPOTENCY_KEY="close-draft"),
        )
        assert blocked.json()["error"]["code"] == "close_blocked"
        JournalEntry.objects.filter(id=leftover.json()["data"]["id"]).delete()
        _post_je(api, token, oid, "close-rev", "2026-06-15", [
            {"account_id": cash["id"], "debit": "100", "credit": "0"},
            {"account_id": income["id"], "debit": "0", "credit": "100"},
        ])
        locked = api.post(
            f"/api/v1/finance/periods/{period['id']}/lock",
            {"year_end": True},
            format="json", **_h(token, oid, HTTP_IDEMPOTENCY_KEY="year-end"),
        )
        assert locked.status_code == 200, locked.content
        pnl = api.get(
            "/api/v1/finance/reports/profit-loss?from=2026-01-01&to=2026-12-31", **_h(token, oid)
        ).json()["data"]
        assert Decimal(pnl["net_income"]) == Decimal("0.00")
        income_row = next(x for x in pnl["income"] if x["code"] == "4000")
        assert Decimal(income_row["amount"]) == Decimal("0.00")
        bs = api.get("/api/v1/finance/reports/balance-sheet?as_of=2026-12-31", **_h(token, oid)).json()["data"]
        eq = next(x for x in bs["equity"] if x["code"] == "3000")
        assert Decimal(eq["amount"]) == Decimal("100.00")
        assert bs["asset_total"] == bs["liability_and_equity_total"]
        closed = api.post(
            "/api/v1/finance/journals",
            {
                "entry_date": "2026-12-31",
                "lines": [
                    {"account_id": cash["id"], "debit": "1", "credit": "0"},
                    {"account_id": income["id"], "debit": "0", "credit": "1"},
                ],
            },
            format="json", **_h(token, oid),
        ).json()["data"]
        fail = api.post(
            f"/api/v1/finance/journals/{closed['id']}/post",
            {"version": 1},
            format="json", **_h(token, oid, HTTP_IDEMPOTENCY_KEY="after-close"),
        )
        assert fail.json()["error"]["code"] == "period_closed"
