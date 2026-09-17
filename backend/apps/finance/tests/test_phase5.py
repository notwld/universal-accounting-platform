import struct
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from apps.authentication.models import AuthUser
from apps.finance.models import BankLine, FinanceException, Invoice
from apps.finance.tests.test_sales import _sales_setup
from apps.finance.tests.test_setup_isolation import CLERK, auth_headers, create_books, make_token

pytest_plugins = ["apps.finance.tests.test_setup_isolation"]


def _h(token, org_id, **extra):
    return auth_headers(token, org_id, **extra)


def _xls(rows):
    def rec(code, data):
        return struct.pack("<HH", code, len(data)) + data

    out = rec(0x0009, struct.pack("<HH", 0x0000, 0x0010))
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                out += rec(0x0003, struct.pack("<HH", r, c) + b"\x00\x00\x00" + struct.pack("<d", float(val)))
            else:
                s = str(val).encode("latin-1", "replace")[:255]
                out += rec(0x0004, struct.pack("<HH", r, c) + b"\x00\x00\x00" + bytes([len(s)]) + s)
    return out + rec(0x000A, b"")


OFX = b"""OFXHEADER:100
DATA:OFXSGML
<OFX>
<BANKMSGSRSV1>
<STMTTRNRS>
<STMTRS>
<BANKTRANLIST>
<STMTTRN>
<TRNTYPE>DEBIT
<DTPOSTED>20260610000000
<TRNAMT>-15.00
<MEMO>Bank fee
</STMTTRN>
</BANKTRANLIST>
</STMTRS>
</STMTTRNRS>
</BANKMSGSRSV1>
</OFX>
"""

QIF = b"!Type:Bank\nD06/10/2026\nT-15.00\nPBank fee\n^\n"


@pytest.mark.django_db
def test_phase5_email_rules_formats_filters_approvals(api, rsa_keys, auth_user, other_user):
    private_pem, public_pem = rsa_keys
    token = make_token(private_pem)
    approver_token = make_token(private_pem, sub="user_clerk_2", sid="sess_2")
    third = AuthUser.objects.create(
        clerk_user_id="user_clerk_3",
        primary_email_hash="ghi",
        primary_email_ciphertext="cara@example.com",
        first_name="Cara",
        last_name="Approver",
        email_verified=True,
    )
    third_token = make_token(private_pem, sub="user_clerk_3", sid="sess_3")
    with override_settings(
        CLERK_JWT_KEY=public_pem,
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        **CLERK,
    ):
        org, cash, equity, income, ar = create_books(api, token, name="Phase5Co", currency="USD", month=1, country="US")
        tax, contact, item, tax_pay, advance, cash = _sales_setup(api, token, org, cash, income, ar)
        api.post(
            "/api/v1/finance/contacts",
            {"name": "Acme Mail", "email": "billing@acme.test"},
            format="json", **_h(token, org["id"]),
        )
        mailed = api.post(
            "/api/v1/finance/contacts",
            {"name": "Mailed Co", "email": "ap@example.test"},
            format="json", **_h(token, org["id"]),
        ).json()["data"]
        inv = api.post(
            "/api/v1/finance/invoices",
            {
                "contact_id": mailed["id"], "entry_date": "2026-06-01", "due_date": "2026-06-10",
                "currency": "USD",
                "lines": [{"item_id": item["id"], "quantity": "1", "unit_price": "100", "tax_rate_id": tax["id"]}],
            },
            format="json", **_h(token, org["id"]),
        )
        assert inv.status_code == 201, inv.content
        small_id = inv.json()["data"]["id"]
        posted = api.post(
            f"/api/v1/finance/invoices/{small_id}/post", format="json",
            **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="p5-small"),
        )
        assert posted.status_code == 200, posted.content
        api.post(
            "/api/v1/finance/reminder-rules",
            {"document_kind": "invoice", "days_before_due": 0},
            format="json", **_h(token, org["id"]),
        )
        mail.outbox.clear()
        first = api.post("/api/v1/finance/reminders/run", {"as_of": "2026-06-10"}, format="json", **_h(token, org["id"]))
        assert first.status_code == 200, first.content
        assert first.json()["data"]["created"][0]["emailed"] is True
        assert len(mail.outbox) == 1
        api.post("/api/v1/finance/reminders/run", {"as_of": "2026-06-10"}, format="json", **_h(token, org["id"]))
        assert len(mail.outbox) == 1

        mute = api.post(
            "/api/v1/finance/contacts", {"name": "No Mail Co"}, format="json", **_h(token, org["id"])
        ).json()["data"]
        mute_inv = api.post(
            "/api/v1/finance/invoices",
            {
                "contact_id": mute["id"], "entry_date": "2026-07-01", "due_date": "2026-07-10",
                "currency": "USD",
                "lines": [{"item_id": item["id"], "quantity": "1", "unit_price": "100", "tax_rate_id": tax["id"]}],
            },
            format="json", **_h(token, org["id"]),
        ).json()["data"]
        api.post(
            f"/api/v1/finance/invoices/{mute_inv['id']}/post", format="json",
            **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="p5-mute"),
        )
        mail.outbox.clear()
        mute_run = api.post("/api/v1/finance/reminders/run", {"as_of": "2026-07-10"}, format="json", **_h(token, org["id"]))
        assert mute_run.json()["data"]["created"][0]["emailed"] is False
        assert mail.outbox == []
        open_ex = api.get("/api/v1/finance/exceptions?status=open", **_h(token, org["id"]))
        assert open_ex.status_code == 200, open_ex.content
        assert any(e["kind"] == "reminder_no_email" for e in open_ex.json()["data"]["items"])
        ex_id = next(e["id"] for e in open_ex.json()["data"]["items"] if e["kind"] == "reminder_no_email")
        resolved = api.post(
            f"/api/v1/finance/exceptions/{ex_id}/resolve",
            {"reason": "added email"},
            format="json", **_h(token, org["id"]),
        )
        assert resolved.json()["data"]["status"] == "resolved"

        expense = api.post(
            "/api/v1/finance/accounts",
            {"code": "5000", "name": "Purchases", "classification": "expense"},
            format="json", **_h(token, org["id"]),
        ).json()["data"]
        rule = api.post(
            "/api/v1/finance/bank-rules",
            {
                "pattern": "fee$", "match_kind": "regex", "account_id": expense["id"],
                "direction": "outflow", "amount_min": "-20", "amount_max": "-10", "priority": 1,
            },
            format="json", **_h(token, org["id"]),
        )
        assert rule.status_code == 201, rule.content
        imported = api.post(
            "/api/v1/finance/bank-statements",
            {
                "account_id": cash["id"],
                "file": SimpleUploadedFile(
                    "stmt.csv",
                    b"date,amount,description\n2026-06-10,-60,Vendor pay\n2026-06-10,-15,Bank fee\n",
                    content_type="text/csv",
                ),
            },
            **_h(token, org["id"]),
        )
        assert imported.status_code == 201, imported.content
        assert len(imported.json()["data"]["categorized"]) == 1
        assert BankLine.objects.get(description="Bank fee").status == BankLine.Status.CATEGORIZED
        assert BankLine.objects.get(description="Vendor pay").status == BankLine.Status.IMPORTED

        ofx = api.post(
            "/api/v1/finance/bank-statements",
            {"account_id": cash["id"], "file": SimpleUploadedFile("stmt.ofx", OFX)},
            **_h(token, org["id"]),
        )
        assert ofx.status_code == 201, ofx.content
        assert ofx.json()["data"]["duplicates"]

        qif = api.post(
            "/api/v1/finance/bank-statements",
            {"account_id": cash["id"], "file": SimpleUploadedFile("stmt.qif", QIF)},
            **_h(token, org["id"]),
        )
        assert qif.status_code == 201, qif.content
        assert qif.json()["data"]["duplicates"]

        xls = api.post(
            "/api/v1/finance/bank-statements",
            {
                "account_id": cash["id"],
                "file": SimpleUploadedFile(
                    "stmt.xls",
                    _xls([["date", "amount", "description"], ["2026-06-10", -15, "Bank fee"]]),
                ),
            },
            **_h(token, org["id"]),
        )
        assert xls.status_code == 201, xls.content
        assert xls.json()["data"]["duplicates"]

        denied = api.post(
            "/api/v1/finance/bank-feeds",
            {"account_id": cash["id"], "url": "https://127.0.0.1/stmt.ofx"},
            format="json", **_h(token, org["id"]),
        )
        assert denied.json()["error"]["code"] == "validation_error"
        feed = api.post(
            "/api/v1/finance/bank-feeds",
            {"account_id": cash["id"], "url": "https://example.com/stmt.ofx"},
            format="json", **_h(token, org["id"]),
        )
        assert feed.status_code == 201, feed.content
        with patch("apps.finance.services.banking._http_get_safe", return_value=OFX):
            fetched = api.post(
                f"/api/v1/finance/bank-feeds/{feed.json()['data']['id']}/fetch",
                format="json", **_h(token, org["id"]),
            )
        assert fetched.status_code == 200, fetched.content
        assert fetched.json()["data"]["duplicates"]

        saved = api.post(
            "/api/v1/finance/saved-filters",
            {"name": "posted", "resource": "invoice", "params": {"status": "posted"}},
            format="json", **_h(token, org["id"]),
        )
        assert saved.status_code == 201, saved.content
        listed = api.get(
            f"/api/v1/finance/invoices?saved_filter_id={saved.json()['data']['id']}",
            **_h(token, org["id"]),
        )
        assert listed.status_code == 200, listed.content
        assert listed.json()["data"]["items"]
        assert all(i["status"] == "posted" for i in listed.json()["data"]["items"])

        settings = api.put(
            "/api/v1/finance/settings",
            {
                "country_code": "US", "base_currency": "USD", "fiscal_year_start_month": 1,
                "timezone": "UTC", "locale": "en", "tax_registration_applies": False,
                "require_document_approval": True, "approval_threshold": "200", "approval_levels": 2,
            },
            format="json", **_h(token, org["id"]),
        )
        assert settings.status_code == 200, settings.content
        api.put(f"/api/v1/finance/grants/{other_user.id}", {"role_slug": "approver"}, format="json", **_h(token, org["id"]))
        api.put(f"/api/v1/finance/grants/{third.id}", {"role_slug": "approver"}, format="json", **_h(token, org["id"]))
        under = api.post(
            "/api/v1/finance/invoices",
            {
                "contact_id": mailed["id"], "entry_date": "2026-08-01", "due_date": "2026-08-10",
                "currency": "USD",
                "lines": [{"item_id": item["id"], "quantity": "1", "unit_price": "100", "tax_rate_id": tax["id"]}],
            },
            format="json", **_h(token, org["id"]),
        ).json()["data"]
        under_post = api.post(
            f"/api/v1/finance/invoices/{under['id']}/post", format="json",
            **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="p5-under"),
        )
        assert under_post.status_code == 200, under_post.content
        over = api.post(
            "/api/v1/finance/invoices",
            {
                "contact_id": mailed["id"], "entry_date": "2026-08-02", "due_date": "2026-08-12",
                "currency": "USD",
                "lines": [{"item_id": item["id"], "quantity": "20", "unit_price": "100", "tax_rate_id": tax["id"]}],
            },
            format="json", **_h(token, org["id"]),
        ).json()["data"]
        blocked = api.post(
            f"/api/v1/finance/invoices/{over['id']}/post", format="json",
            **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="p5-over"),
        )
        assert blocked.json()["error"]["code"] == "approval_required"
        api.post(f"/api/v1/finance/invoices/{over['id']}/submit", format="json", **_h(token, org["id"]))
        first_ap = api.post(
            f"/api/v1/finance/invoices/{over['id']}/approve", format="json", **_h(approver_token, org["id"])
        )
        assert first_ap.json()["data"]["status"] == "pending"
        twice = api.post(
            f"/api/v1/finance/invoices/{over['id']}/approve", format="json", **_h(approver_token, org["id"])
        )
        assert twice.json()["data"]["status"] == "pending"
        second_ap = api.post(
            f"/api/v1/finance/invoices/{over['id']}/approve", format="json", **_h(third_token, org["id"])
        )
        assert second_ap.json()["data"]["status"] == "approved"
        done = api.post(
            f"/api/v1/finance/invoices/{over['id']}/post", format="json",
            **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="p5-over-ok"),
        )
        assert done.status_code == 200, done.content
        assert Invoice.objects.get(id=over["id"]).status == Invoice.Status.POSTED
        assert FinanceException.objects.filter(kind="reminder_no_email", status="resolved").exists()
