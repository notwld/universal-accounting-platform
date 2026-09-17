from decimal import Decimal

import pytest
from django.test import override_settings

from apps.finance.models import Invoice, JournalLine, Reminder
from apps.finance.tests.test_sales import _sales_setup
from apps.finance.tests.test_setup_isolation import CLERK, auth_headers, create_books, make_token

pytest_plugins = ["apps.finance.tests.test_setup_isolation"]


def _h(token, org_id, **extra):
    return auth_headers(token, org_id, **extra)


@pytest.mark.django_db
def test_weekly_yearly_autopost(api, rsa_keys, auth_user):
    private_pem, public_pem = rsa_keys
    token = make_token(private_pem)
    with override_settings(CLERK_JWT_KEY=public_pem, **CLERK):
        org, cash, equity, income, ar = create_books(api, token, name="CadenceCo", currency="USD", month=1, country="US")
        tax, contact, item, tax_pay, advance, cash = _sales_setup(api, token, org, cash, income, ar)
        weekly = api.post(
            "/api/v1/finance/recurring",
            {
                "kind": "invoice", "frequency": "weekly", "weekday": 0,
                "contact_id": contact["id"], "currency": "USD", "start_on": "2026-06-01",
                "lines": [{"item_id": item["id"], "quantity": "1", "unit_price": "100", "tax_rate_id": tax["id"]}],
            },
            format="json", **_h(token, org["id"]),
        )
        assert weekly.status_code == 201, weekly.content
        run = api.post("/api/v1/finance/recurring/run", {"as_of": "2026-06-09"}, format="json", **_h(token, org["id"]))
        assert run.status_code == 200, run.content
        dates = sorted(Invoice.objects.filter(organization_id=org["id"]).values_list("entry_date", flat=True))
        assert [d.isoformat() for d in dates] == ["2026-06-01", "2026-06-08"]
        assert all(i.status == Invoice.Status.DRAFT for i in Invoice.objects.all())

        yearly = api.post(
            "/api/v1/finance/recurring",
            {
                "kind": "invoice", "frequency": "yearly", "month_of_year": 2, "day_of_month": 29,
                "contact_id": contact["id"], "currency": "USD", "start_on": "2024-02-29",
                "lines": [{"item_id": item["id"], "quantity": "1", "unit_price": "100", "tax_rate_id": tax["id"]}],
            },
            format="json", **_h(token, org["id"]),
        )
        assert yearly.status_code == 201, yearly.content
        yrun = api.post("/api/v1/finance/recurring/run", {"as_of": "2025-03-01"}, format="json", **_h(token, org["id"]))
        assert yrun.status_code == 200, yrun.content
        ydates = sorted(
            Invoice.objects.filter(organization_id=org["id"]).exclude(entry_date__year=2026).values_list("entry_date", flat=True)
        )
        assert [d.isoformat() for d in ydates] == ["2024-02-29", "2025-02-28"]

        auto = api.post(
            "/api/v1/finance/recurring",
            {
                "kind": "invoice", "frequency": "monthly", "day_of_month": 15, "auto_post": True,
                "contact_id": contact["id"], "currency": "USD", "start_on": "2026-07-15",
                "lines": [{"item_id": item["id"], "quantity": "1", "unit_price": "100", "tax_rate_id": tax["id"]}],
            },
            format="json", **_h(token, org["id"]),
        )
        assert auto.status_code == 201, auto.content
        posted_run = api.post("/api/v1/finance/recurring/run", {"as_of": "2026-07-15"}, format="json", **_h(token, org["id"]))
        assert posted_run.status_code == 200, posted_run.content
        posted = Invoice.objects.get(entry_date="2026-07-15")
        assert posted.status == Invoice.Status.POSTED
        before = JournalLine.objects.count()
        replay = api.post("/api/v1/finance/recurring/run", {"as_of": "2026-07-15"}, format="json", **_h(token, org["id"]))
        assert replay.json()["data"]["created"] == []
        assert JournalLine.objects.count() == before


@pytest.mark.django_db
def test_approval_and_reminders(api, rsa_keys, auth_user, other_user):
    private_pem, public_pem = rsa_keys
    token = make_token(private_pem)
    approver_token = make_token(private_pem, sub="user_clerk_2", sid="sess_2")
    with override_settings(CLERK_JWT_KEY=public_pem, **CLERK):
        org, cash, equity, income, ar = create_books(api, token, name="ApproveCo", currency="USD", month=1, country="US")
        tax, contact, item, tax_pay, advance, cash = _sales_setup(api, token, org, cash, income, ar)
        settings = api.put(
            "/api/v1/finance/settings",
            {
                "country_code": "US", "base_currency": "USD", "fiscal_year_start_month": 1,
                "timezone": "UTC", "locale": "en", "tax_registration_applies": False,
                "require_document_approval": True,
            },
            format="json", **_h(token, org["id"]),
        )
        assert settings.status_code == 200, settings.content
        grant = api.put(
            f"/api/v1/finance/grants/{other_user.id}",
            {"role_slug": "approver"},
            format="json", **_h(token, org["id"]),
        )
        assert grant.status_code == 200, grant.content
        inv = api.post(
            "/api/v1/finance/invoices",
            {
                "contact_id": contact["id"], "entry_date": "2026-06-01", "due_date": "2026-06-10",
                "currency": "USD",
                "lines": [{"item_id": item["id"], "quantity": "1", "unit_price": "100", "tax_rate_id": tax["id"]}],
            },
            format="json", **_h(token, org["id"]),
        )
        assert inv.status_code == 201, inv.content
        inv_id = inv.json()["data"]["id"]
        blocked = api.post(
            f"/api/v1/finance/invoices/{inv_id}/post", format="json",
            **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="need-appr"),
        )
        assert blocked.json()["error"]["code"] == "approval_required"
        submitted = api.post(f"/api/v1/finance/invoices/{inv_id}/submit", format="json", **_h(token, org["id"]))
        assert submitted.json()["data"]["status"] == "pending"
        self_appr = api.post(f"/api/v1/finance/invoices/{inv_id}/approve", format="json", **_h(token, org["id"]))
        assert self_appr.json()["error"]["code"] == "self_approve_forbidden"
        rejected = api.post(
            f"/api/v1/finance/invoices/{inv_id}/reject", {"reason": "fix tax"},
            format="json", **_h(approver_token, org["id"]),
        )
        assert rejected.json()["data"]["status"] == "draft"
        api.post(f"/api/v1/finance/invoices/{inv_id}/submit", format="json", **_h(token, org["id"]))
        approved = api.post(f"/api/v1/finance/invoices/{inv_id}/approve", format="json", **_h(approver_token, org["id"]))
        assert approved.json()["data"]["status"] == "approved"
        posted = api.post(
            f"/api/v1/finance/invoices/{inv_id}/post", format="json",
            **_h(token, org["id"], HTTP_IDEMPOTENCY_KEY="after-appr"),
        )
        assert posted.status_code == 200, posted.content
        assert posted.json()["data"]["status"] == "posted"

        rule = api.post(
            "/api/v1/finance/reminder-rules",
            {"document_kind": "invoice", "days_before_due": 0},
            format="json", **_h(token, org["id"]),
        )
        assert rule.status_code == 201, rule.content
        first = api.post("/api/v1/finance/reminders/run", {"as_of": "2026-06-10"}, format="json", **_h(token, org["id"]))
        assert first.status_code == 200, first.content
        assert len(first.json()["data"]["created"]) == 1
        second = api.post("/api/v1/finance/reminders/run", {"as_of": "2026-06-10"}, format="json", **_h(token, org["id"]))
        assert second.json()["data"]["created"] == []
        assert Reminder.objects.count() == 1
        assert Decimal(Invoice.objects.get(id=inv_id).total) == Decimal("110.00")
