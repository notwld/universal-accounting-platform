from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from apps.finance.models import BankLine, JournalLine
from apps.finance.tests.test_purchases import _purchase_setup
from apps.finance.tests.test_setup_isolation import CLERK, auth_headers, create_books, make_token

pytest_plugins = ["apps.finance.tests.test_setup_isolation"]


def _h(token, org_id, **extra):
    return auth_headers(token, org_id, **extra)


@pytest.mark.django_db
def test_bank_rules_apply_priority_and_replay(api, rsa_keys, auth_user):
    private_pem, public_pem = rsa_keys
    token = make_token(private_pem)
    with override_settings(CLERK_JWT_KEY=public_pem, **CLERK):
        org, cash, equity, income, ar = create_books(api, token, name="RuleCo", currency="USD", month=1, country="US")
        tax, contact, item, tax_pay, expense, ap, cash = _purchase_setup(api, token, org, cash, income)
        other = api.post(
            "/api/v1/finance/accounts",
            {"code": "5100", "name": "Bank fees alt", "classification": "expense"},
            format="json", **_h(token, org["id"]),
        ).json()["data"]
        bill = api.post(
            "/api/v1/finance/bills",
            {
                "contact_id": contact["id"], "entry_date": "2026-06-01", "currency": "USD",
                "lines": [{"item_id": item["id"], "quantity": "1", "unit_price": "60", "tax_rate_id": tax["id"]}],
            },
            format="json", **_h(token, org["id"]),
        )
        api.post(
            f"/api/v1/finance/bills/{bill.json()['data']['id']}/post", format="json",
            **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="rule-bill"),
        )
        pay = api.post(
            "/api/v1/finance/vendor-payments",
            {
                "contact_id": contact["id"], "bank_account_id": cash["id"], "entry_date": "2026-06-10",
                "currency": "USD", "amount": "60",
                "allocations": [{"bill_id": bill.json()["data"]["id"], "amount": "60"}],
            },
            format="json", **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="rule-pay"),
        )
        assert pay.status_code == 201, pay.content
        imported = api.post(
            "/api/v1/finance/bank-statements",
            {
                "account_id": cash["id"],
                "file": SimpleUploadedFile(
                    "stmt.csv",
                    b"date,amount,description\n2026-06-10,-60,Vendor pay\n2026-06-10,-15,Bank fee\n2026-06-11,15,FEE REFUND\n",
                    content_type="text/csv",
                ),
            },
            **_h(token, org["id"]),
        )
        assert imported.status_code == 201, imported.content
        created = imported.json()["data"]["created"]
        pay_line = next(x for x in created if Decimal(x["amount"]) == Decimal("-60"))
        matched = api.post(
            f"/api/v1/finance/bank-lines/{pay_line['id']}/match",
            {"vendor_payment_id": pay.json()["data"]["id"]},
            format="json", **_h(token, org["id"]),
        )
        assert matched.status_code == 200, matched.content
        denied = api.post(
            "/api/v1/finance/bank-rules",
            {"pattern": "fee", "account_id": ap["id"]},
            format="json", **_h(token, org["id"]),
        )
        assert denied.json()["error"]["code"] == "control_account_restricted"
        first = api.post(
            "/api/v1/finance/bank-rules",
            {"pattern": "fee", "account_id": expense["id"], "direction": "outflow", "priority": 1},
            format="json", **_h(token, org["id"]),
        )
        assert first.status_code == 201, first.content
        second = api.post(
            "/api/v1/finance/bank-rules",
            {"pattern": "fee", "account_id": other["id"], "direction": "outflow", "priority": 2},
            format="json", **_h(token, org["id"]),
        )
        assert second.status_code == 201, second.content
        listed = api.get("/api/v1/finance/bank-rules", **_h(token, org["id"]))
        assert len(listed.json()["data"]["items"]) == 2
        applied = api.post("/api/v1/finance/bank-rules/apply", {}, format="json", **_h(token, org["id"]))
        assert applied.status_code == 200, applied.content
        assert len(applied.json()["data"]["categorized"]) == 1
        fee = BankLine.objects.get(description="Bank fee")
        assert fee.status == BankLine.Status.CATEGORIZED
        assert JournalLine.objects.filter(journal=fee.journal, account_id=expense["id"], debit__gt=0).exists()
        assert not JournalLine.objects.filter(journal=fee.journal, account_id=other["id"]).exists()
        refund = BankLine.objects.get(description="FEE REFUND")
        assert refund.status == BankLine.Status.IMPORTED
        assert BankLine.objects.get(id=pay_line["id"]).status == BankLine.Status.MATCHED
        before = JournalLine.objects.filter(journal__source_type="bank").count()
        replay = api.post("/api/v1/finance/bank-rules/apply", {}, format="json", **_h(token, org["id"]))
        assert replay.json()["data"]["categorized"] == []
        assert JournalLine.objects.filter(journal__source_type="bank").count() == before
        paused = api.patch(
            f"/api/v1/finance/bank-rules/{first.json()['data']['id']}",
            {"active": False},
            format="json", **_h(token, org["id"]),
        )
        assert paused.json()["data"]["active"] is False
