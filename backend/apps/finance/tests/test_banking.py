from datetime import date
from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape
import zipfile

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from apps.finance.models import JournalLine
from apps.finance.tests.test_setup_isolation import CLERK, auth_headers, create_books, make_token
from apps.finance.tests.test_purchases import _purchase_setup

pytest_plugins = ["apps.finance.tests.test_setup_isolation"]


def _h(token, org_id, **extra):
    return auth_headers(token, org_id, **extra)


def _xlsx(rows):
    shared = []

    def sid(value):
        text = str(value)
        if text not in shared:
            shared.append(text)
        return shared.index(text)

    body = []
    for r, row in enumerate(rows, 1):
        cells = []
        for c, val in enumerate(row):
            ref = f"{chr(65 + c)}{r}"
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                cells.append(f'<c r="{ref}"><v>{val}</v></c>')
            else:
                cells.append(f'<c r="{ref}" t="s"><v>{sid(val)}</v></c>')
        body.append(f'<row r="{r}">{"".join(cells)}</row>')
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    sst = f'<sst xmlns="{ns}">' + "".join(f"<si><t>{escape(s)}</t></si>" for s in shared) + "</sst>"
    sheet = f'<worksheet xmlns="{ns}"><sheetData>{"".join(body)}</sheetData></worksheet>'
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("xl/sharedStrings.xml", sst)
        zf.writestr("xl/worksheets/sheet1.xml", sheet)
    return buf.getvalue()


def _tb(api, token, org_id):
    return api.get(
        "/api/v1/finance/reports/trial-balance?from=2026-01-01&to=2026-12-31", **_h(token, org_id)
    ).json()["data"]["items"]


@pytest.mark.django_db
def test_xlsx_import_match_categorize_reports(api, rsa_keys, auth_user):
    private_pem, public_pem = rsa_keys
    token = make_token(private_pem)
    with override_settings(CLERK_JWT_KEY=public_pem, **CLERK):
        org, cash, equity, income, ar = create_books(api, token, name="BankCo", currency="USD", month=1, country="US")
        tax, contact, item, tax_pay, expense, ap, cash = _purchase_setup(api, token, org, cash, income)
        bill = api.post(
            "/api/v1/finance/bills",
            {
                "contact_id": contact["id"], "entry_date": "2026-06-01", "currency": "USD",
                "lines": [{"item_id": item["id"], "quantity": "1", "unit_price": "100", "tax_rate_id": tax["id"]}],
            },
            format="json", **_h(token, org["id"]),
        )
        assert bill.status_code == 201, bill.content
        api.post(
            f"/api/v1/finance/bills/{bill.json()['data']['id']}/post", format="json",
            **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="bank-bill"),
        )
        pay = api.post(
            "/api/v1/finance/vendor-payments",
            {
                "contact_id": contact["id"], "bank_account_id": cash["id"], "entry_date": "2026-06-10",
                "currency": "USD", "amount": "60",
                "allocations": [{"bill_id": bill.json()["data"]["id"], "amount": "60"}],
            },
            format="json", **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="bank-pay"),
        )
        assert pay.status_code == 201, pay.content
        before = _tb(api, token, org["id"])
        xlsx = SimpleUploadedFile(
            "stmt.xlsx",
            _xlsx([
                ["date", "amount", "description"],
                ["2026-06-10", -60, "Vendor pay"],
                [(date(2026, 6, 10) - date(1899, 12, 30)).days, -15, "Bank fee"],
                ["2026-06-12", -20, "Wire"],
            ]),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        imported = api.post(
            "/api/v1/finance/bank-statements",
            {"account_id": cash["id"], "file": xlsx},
            **_h(token, org["id"]),
        )
        assert imported.status_code == 201, imported.content
        created = imported.json()["data"]["created"]
        assert len(created) == 3
        assert imported.json()["data"]["duplicates"] == []
        csv_file = SimpleUploadedFile(
            "stmt.csv",
            b"date,amount,description\n2026-06-10,-60,Vendor pay\n2026-06-10,-15,Bank fee\n2026-06-12,-20,Wire\n",
            content_type="text/csv",
        )
        again = api.post(
            "/api/v1/finance/bank-statements",
            {"account_id": cash["id"], "file": csv_file},
            **_h(token, org["id"]),
        )
        assert again.status_code == 201, again.content
        assert again.json()["data"]["created"] == []
        assert len(again.json()["data"]["duplicates"]) == 3

        pay_line = next(x for x in created if Decimal(x["amount"]) == Decimal("-60"))
        fee_line = next(x for x in created if Decimal(x["amount"]) == Decimal("-15"))
        wire_line = next(x for x in created if Decimal(x["amount"]) == Decimal("-20"))
        matched = api.post(
            f"/api/v1/finance/bank-lines/{pay_line['id']}/match",
            {"vendor_payment_id": pay.json()["data"]["id"]},
            format="json", **_h(token, org["id"]),
        )
        assert matched.status_code == 200, matched.content
        assert _tb(api, token, org["id"]) == before
        twice = api.post(
            f"/api/v1/finance/bank-lines/{pay_line['id']}/match",
            {"vendor_payment_id": pay.json()["data"]["id"]},
            format="json", **_h(token, org["id"]),
        )
        assert twice.json()["error"]["code"] == "already_matched"
        cat = api.post(
            f"/api/v1/finance/bank-lines/{fee_line['id']}/categorize",
            {"account_id": expense["id"]},
            format="json", **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="bank-fee"),
        )
        assert cat.status_code == 200, cat.content
        api.post(
            f"/api/v1/finance/bank-lines/{wire_line['id']}/categorize",
            {"account_id": expense["id"]},
            format="json", **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="bank-wire"),
        )
        assert JournalLine.objects.filter(journal__source_type="bank").count() == 4
        bad = api.post(
            "/api/v1/finance/bank-reconciliations",
            {
                "account_id": cash["id"], "start_on": "2026-06-01", "end_on": "2026-06-30",
                "opening": "0", "closing": "0",
            },
            format="json", **_h(token, org["id"]),
        )
        assert bad.status_code == 201
        fail = api.post(
            f"/api/v1/finance/bank-reconciliations/{bad.json()['data']['id']}/complete",
            format="json", **_h(token, org["id"]),
        )
        assert fail.json()["error"]["code"] == "recon_imbalanced"
        rec = api.post(
            "/api/v1/finance/bank-reconciliations",
            {
                "account_id": cash["id"], "start_on": "2026-06-01", "end_on": "2026-06-30",
                "opening": "0", "closing": "-95",
            },
            format="json", **_h(token, org["id"]),
        )
        done = api.post(
            f"/api/v1/finance/bank-reconciliations/{rec.json()['data']['id']}/complete",
            format="json", **_h(token, org["id"]),
        )
        assert done.status_code == 200, done.content
        assert done.json()["data"]["status"] == "complete"
        pnl = api.get(
            "/api/v1/finance/reports/profit-loss?from=2026-01-01&to=2026-12-31", **_h(token, org["id"])
        ).json()["data"]
        assert Decimal(pnl["expense_total"]) == Decimal("135.00")
        bs = api.get(
            "/api/v1/finance/reports/balance-sheet?as_of=2026-12-31", **_h(token, org["id"])
        ).json()["data"]
        cash_row = next(x for x in bs["assets"] if x["code"] == "1000")
        assert Decimal(cash_row["amount"]) == Decimal("-95.00")
        assert bs["asset_total"] == bs["liability_and_equity_total"]
        reopen = api.post(
            f"/api/v1/finance/bank-reconciliations/{rec.json()['data']['id']}/reopen",
            {"reason": "check fee"},
            format="json", **_h(token, org["id"]),
        )
        assert reopen.json()["data"]["status"] == "open"
