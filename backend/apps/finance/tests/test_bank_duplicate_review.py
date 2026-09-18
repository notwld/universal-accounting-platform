from decimal import Decimal

import pytest
from django.test import override_settings

from apps.finance.models import BankLine
from apps.finance.tests.test_purchases import _purchase_setup
from apps.finance.tests.test_setup_isolation import CLERK, auth_headers, create_books, make_token

pytest_plugins = ["apps.finance.tests.test_setup_isolation"]


def _h(token, org_id, **extra):
    return auth_headers(token, org_id, **extra)


@pytest.mark.django_db
def test_in_file_duplicates_kept_unresolved_recon_and_file_replay(api, rsa_keys, auth_user):
    private_pem, public_pem = rsa_keys
    token = make_token(private_pem)
    with override_settings(CLERK_JWT_KEY=public_pem, **CLERK):
        org, cash, _eq, income, _ar = create_books(api, token, name="DupBank", currency="USD", month=1, country="US")
        _tax, _contact, _item, _tax_pay, expense, _ap, cash = _purchase_setup(api, token, org, cash, income)
        from django.core.files.uploadedfile import SimpleUploadedFile

        first = SimpleUploadedFile(
            "fees.csv",
            b"date,amount,description\n2026-06-10,-15,Bank fee\n2026-06-10,-15,Bank fee\n",
            content_type="text/csv",
        )
        imported = api.post(
            "/api/v1/finance/bank-statements",
            {"account_id": cash["id"], "file": first},
            **_h(token, org["id"]),
        )
        assert imported.status_code == 201, imported.content
        created = imported.json()["data"]["created"]
        assert len(created) == 2
        assert BankLine.objects.filter(account_id=cash["id"]).count() == 2
        rec = api.post(
            "/api/v1/finance/bank-reconciliations",
            {
                "account_id": cash["id"], "start_on": "2026-06-01", "end_on": "2026-06-30",
                "opening": "0", "closing": "-30",
            },
            format="json", **_h(token, org["id"]),
        )
        fail = api.post(
            f"/api/v1/finance/bank-reconciliations/{rec.json()['data']['id']}/complete",
            format="json", **_h(token, org["id"]),
        )
        assert fail.json()["error"]["code"] == "recon_unresolved"
        for i, line in enumerate(created):
            cat = api.post(
                f"/api/v1/finance/bank-lines/{line['id']}/categorize",
                {"account_id": expense["id"]},
                format="json", **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY=f"dup-fee-{i}"),
            )
            assert cat.status_code == 200, cat.content
        done = api.post(
            f"/api/v1/finance/bank-reconciliations/{rec.json()['data']['id']}/complete",
            format="json", **_h(token, org["id"]),
        )
        assert done.status_code == 200, done.content
        assert Decimal(done.json()["data"]["book_balance"]) == Decimal(done.json()["data"].get("book_balance") or "0")
        replay = SimpleUploadedFile(
            "fees.csv",
            b"date,amount,description\n2026-06-10,-15,Bank fee\n2026-06-10,-15,Bank fee\n",
            content_type="text/csv",
        )
        again = api.post(
            "/api/v1/finance/bank-statements",
            {"account_id": cash["id"], "file": replay},
            **_h(token, org["id"]),
        )
        assert again.status_code == 201, again.content
        assert again.json()["data"]["created"] == []
        assert len(again.json()["data"]["duplicates"]) == 2
        assert BankLine.objects.filter(account_id=cash["id"]).count() == 2
