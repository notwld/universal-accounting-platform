from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from apps.finance.models import Bill, JournalLine
from apps.finance.tests.test_setup_isolation import CLERK, auth_headers, create_books, make_token
from apps.finance.tests.test_purchases import _purchase_setup

pytest_plugins = ["apps.finance.tests.test_setup_isolation"]


def _h(token, org_id, **extra):
    return auth_headers(token, org_id, **extra)


def _pdf():
    return SimpleUploadedFile("receipt.pdf", b"%PDF-1.4 test", content_type="application/pdf")


@pytest.mark.django_db
def test_po_payment_run_attachment_statement(api, rsa_keys, auth_user):
    private_pem, public_pem = rsa_keys
    token = make_token(private_pem)
    with override_settings(CLERK_JWT_KEY=public_pem, **CLERK):
        org, cash, equity, income, ar = create_books(api, token, name="POCo", currency="USD", month=1, country="US")
        tax, contact, item, tax_pay, expense, ap, cash = _purchase_setup(api, token, org, cash, income)
        po = api.post(
            "/api/v1/finance/purchase-orders",
            {
                "contact_id": contact["id"], "entry_date": "2026-06-01", "currency": "USD",
                "lines": [{"item_id": item["id"], "quantity": "1", "unit_price": "100", "tax_rate_id": tax["id"]}],
            },
            format="json", **_h(token, org["id"]),
        )
        assert po.status_code == 201, po.content
        tb = api.get(
            "/api/v1/finance/reports/trial-balance?from=2026-01-01&to=2026-12-31", **_h(token, org["id"])
        ).json()["data"]["items"]
        assert tb == []
        converted = api.post(
            f"/api/v1/finance/purchase-orders/{po.json()['data']['id']}/convert",
            format="json", **_h(token, org["id"]),
        )
        assert converted.status_code == 201, converted.content
        assert JournalLine.objects.count() == 0
        again = api.post(
            f"/api/v1/finance/purchase-orders/{po.json()['data']['id']}/convert",
            format="json", **_h(token, org["id"]),
        )
        assert again.json()["error"]["code"] == "po_not_convertible"
        bill_id = converted.json()["data"]["id"]
        posted = api.post(
            f"/api/v1/finance/bills/{bill_id}/post", format="json",
            **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="po-bill"),
        )
        assert posted.status_code == 200, posted.content

        bill_b = api.post(
            "/api/v1/finance/bills",
            {
                "contact_id": contact["id"], "entry_date": "2026-06-02", "currency": "USD",
                "lines": [{"item_id": item["id"], "quantity": "1", "unit_price": "100", "tax_rate_id": tax["id"]}],
            },
            format="json", **_h(token, org["id"]),
        )
        api.post(
            f"/api/v1/finance/bills/{bill_b.json()['data']['id']}/post", format="json",
            **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="po-bill-2"),
        )
        run = api.post(
            "/api/v1/finance/payment-runs",
            {
                "bank_account_id": cash["id"], "entry_date": "2026-06-10", "currency": "USD",
                "items": [
                    {"bill_id": bill_id, "amount": "110"},
                    {"bill_id": bill_b.json()["data"]["id"], "amount": "110"},
                ],
            },
            format="json", **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="run1"),
        )
        assert run.status_code == 201, run.content
        replay = api.post(
            "/api/v1/finance/payment-runs",
            {
                "bank_account_id": cash["id"], "entry_date": "2026-06-10", "currency": "USD",
                "items": [
                    {"bill_id": bill_id, "amount": "110"},
                    {"bill_id": bill_b.json()["data"]["id"], "amount": "110"},
                ],
            },
            format="json", **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="run1"),
        )
        assert replay.json()["data"]["id"] == run.json()["data"]["id"]
        aging = api.get(
            "/api/v1/finance/reports/ap-aging?as_of=2026-06-30", **_h(token, org["id"])
        ).json()["data"]["items"]
        assert aging == []

        stmt = api.get(
            f"/api/v1/finance/contacts/{contact['id']}/vendor-statement?from=2026-06-01&to=2026-06-30",
            **_h(token, org["id"]),
        )
        assert stmt.status_code == 200, stmt.content
        types = {row["type"] for row in stmt.json()["data"]["items"]}
        assert "bill" in types and "payment" in types

        att = api.post(
            "/api/v1/finance/attachments",
            {"object_type": "bill", "object_id": bill_id, "file": _pdf()},
            format="multipart", **_h(token, org["id"]),
        )
        assert att.status_code == 201, att.content
        dl = api.get(
            f"/api/v1/finance/attachments/{att.json()['data']['id']}/download",
            **_h(token, org["id"]),
        )
        assert dl.status_code == 200
        assert b"".join(dl.streaming_content).startswith(b"%PDF")
        bad = api.post(
            "/api/v1/finance/attachments",
            {"object_type": "bill", "object_id": bill_id, "file": SimpleUploadedFile("x.exe", b"MZ", content_type="application/x-msdownload")},
            format="multipart", **_h(token, org["id"]),
        )
        assert bad.status_code == 422
        spoof = api.post(
            "/api/v1/finance/attachments",
            {
                "object_type": "bill",
                "object_id": bill_id,
                "file": SimpleUploadedFile("x.pdf", b"MZ", content_type="application/pdf"),
            },
            format="multipart", **_h(token, org["id"]),
        )
        assert spoof.status_code == 422

        other, *_ = create_books(api, token, name="OtherCo", currency="USD", month=1, country="US")
        blocked = api.get(
            f"/api/v1/finance/attachments/{att.json()['data']['id']}/download",
            **_h(token, other["id"]),
        )
        assert blocked.status_code in (403, 404)
