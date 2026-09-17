from decimal import Decimal

import pytest
from django.test import override_settings

from apps.finance.models import FixedAsset, JournalEntry, JournalLine
from apps.finance.tests.test_setup_isolation import CLERK, auth_headers, create_books, make_token

pytest_plugins = ["apps.finance.tests.test_setup_isolation"]


def _h(token, org_id, **extra):
    return auth_headers(token, org_id, **extra)


@pytest.mark.django_db
def test_capitalize_depreciate_dispose(api, rsa_keys, auth_user):
    private_pem, public_pem = rsa_keys
    token = make_token(private_pem)
    with override_settings(CLERK_JWT_KEY=public_pem, **CLERK):
        org, cash, equity, income, ar = create_books(api, token, name="AssetCo", currency="USD", month=1, country="US")
        ppe = api.post(
            "/api/v1/finance/accounts",
            {"code": "1600", "name": "PPE", "classification": "asset"},
            format="json", **_h(token, org["id"]),
        ).json()["data"]
        accum = api.post(
            "/api/v1/finance/accounts",
            {"code": "1601", "name": "Accum dep", "classification": "asset"},
            format="json", **_h(token, org["id"]),
        ).json()["data"]
        exp = api.post(
            "/api/v1/finance/accounts",
            {"code": "6100", "name": "Depreciation", "classification": "expense"},
            format="json", **_h(token, org["id"]),
        ).json()["data"]
        created = api.post(
            "/api/v1/finance/assets",
            {
                "name": "Press", "cost": "1200", "residual": "0", "life_months": 12,
                "in_service_date": "2026-01-01",
                "cost_account_id": ppe["id"], "accum_account_id": accum["id"],
                "expense_account_id": exp["id"], "credit_account_id": cash["id"],
            },
            format="json", **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="fa-cap"),
        )
        assert created.status_code == 201, created.content
        asset = created.json()["data"]
        assert Decimal(asset["nbv"]) == Decimal("1200.00")
        replay = api.post(
            "/api/v1/finance/assets",
            {
                "name": "Press", "cost": "1200", "residual": "0", "life_months": 12,
                "in_service_date": "2026-01-01",
                "cost_account_id": ppe["id"], "accum_account_id": accum["id"],
                "expense_account_id": exp["id"], "credit_account_id": cash["id"],
            },
            format="json", **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="fa-cap"),
        )
        assert replay.status_code == 201
        assert FixedAsset.objects.filter(organization_id=org["id"]).count() == 1

        dep = api.post(
            "/api/v1/finance/assets/depreciate",
            {"through_date": "2026-02-28", "asset_id": asset["id"]},
            format="json", **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="fa-dep"),
        )
        assert dep.status_code == 200, dep.content
        assert dep.json()["data"]["charged"] == 2
        row = api.get("/api/v1/finance/assets", **_h(token, org["id"])).json()["data"]["items"][0]
        assert Decimal(row["accum"]) == Decimal("200.00")
        assert Decimal(row["nbv"]) == Decimal("1000.00")
        journals = JournalEntry.objects.filter(organization_id=org["id"], source_type="asset").count()
        again = api.post(
            "/api/v1/finance/assets/depreciate",
            {"through_date": "2026-02-28", "asset_id": asset["id"]},
            format="json", **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="fa-dep-2"),
        )
        assert again.json()["data"]["charged"] == 0
        assert JournalEntry.objects.filter(organization_id=org["id"], source_type="asset").count() == journals

        wd = api.post(
            f"/api/v1/finance/assets/{asset['id']}/write-down",
            {"amount": "100", "entry_date": "2026-02-28"},
            format="json", **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="fa-wd"),
        )
        assert wd.status_code == 200, wd.content
        assert Decimal(wd.json()["data"]["nbv"]) == Decimal("900.00")

        # restore NBV to 1000 for the specified dispose fixture: reverse is not needed —
        # use a second asset for dispose SC instead. Write-down already covered.
        other = api.post(
            "/api/v1/finance/assets",
            {
                "name": "Lathe", "cost": "1200", "residual": "0", "life_months": 12,
                "in_service_date": "2026-01-01",
                "cost_account_id": ppe["id"], "accum_account_id": accum["id"],
                "expense_account_id": exp["id"], "credit_account_id": cash["id"],
            },
            format="json", **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="fa-cap-2"),
        ).json()["data"]
        api.post(
            "/api/v1/finance/assets/depreciate",
            {"through_date": "2026-02-28", "asset_id": other["id"]},
            format="json", **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="fa-dep-b"),
        )
        gone = api.post(
            f"/api/v1/finance/assets/{other['id']}/dispose",
            {
                "entry_date": "2026-03-01", "proceeds": "950",
                "proceeds_account_id": cash["id"], "gain_loss_account_id": income["id"],
            },
            format="json", **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="fa-dis"),
        )
        assert gone.status_code == 200, gone.content
        assert gone.json()["data"]["status"] == "disposed"
        loss = JournalLine.objects.filter(account_id=income["id"], debit__gt=0, journal__source_type="asset").first()
        assert Decimal(loss.debit) == Decimal("50.00")
        blocked = api.post(
            f"/api/v1/finance/assets/{other['id']}/dispose",
            {
                "entry_date": "2026-03-01", "proceeds": "950",
                "proceeds_account_id": cash["id"], "gain_loss_account_id": income["id"],
            },
            format="json", **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="fa-dis-2"),
        )
        assert blocked.status_code >= 400

        val = api.get("/api/v1/finance/reports/asset-register", **_h(token, org["id"]))
        assert val.status_code == 200, val.content
        assert Decimal(val.json()["data"]["register_nbv"]) == Decimal(val.json()["data"]["gl_nbv"])
        # press still active after write-down 900; lathe disposed 0
        assert Decimal(val.json()["data"]["register_nbv"]) == Decimal("900.00")
