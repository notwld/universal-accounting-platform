from datetime import datetime, timedelta, timezone

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.test import override_settings
from rest_framework.test import APIClient

from apps.authentication.models import AuthUser
from apps.finance.models import FinanceAuditEvent, FinanceGrant, JournalEntry
from apps.tenancy.models import Location, Membership

CLERK = dict(
    CLERK_ISSUER="https://example.clerk.accounts.dev",
    CLERK_AUTHORIZED_PARTIES=["http://localhost:5173"],
    CLERK_VERIFY_AUTHORIZED_PARTY=True,
)


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def rsa_keys():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return private_pem, public_pem


def make_token(private_pem, *, sub="user_clerk_1", sid="sess_1"):
    now = datetime.now(timezone.utc)
    claims = {
        "sub": sub,
        "sid": sid,
        "email": "ada@example.com",
        "email_verified": True,
        "first_name": "Ada",
        "last_name": "Lovelace",
        "azp": "http://localhost:5173",
        "iss": "https://example.clerk.accounts.dev",
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()) - 1,
        "exp": int((now + timedelta(seconds=3600)).timestamp()),
    }
    return jwt.encode(claims, private_pem, algorithm="RS256")


@pytest.fixture
def auth_user(db):
    return AuthUser.objects.create(
        clerk_user_id="user_clerk_1",
        primary_email_hash="abc",
        primary_email_ciphertext="ada@example.com",
        first_name="Ada",
        last_name="Lovelace",
        email_verified=True,
    )


@pytest.fixture
def other_user(db):
    return AuthUser.objects.create(
        clerk_user_id="user_clerk_2",
        primary_email_hash="def",
        primary_email_ciphertext="bob@example.com",
        first_name="Bob",
        last_name="Viewer",
        email_verified=True,
    )


def auth_headers(token, org_id=None, **extra):
    headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"}
    if org_id:
        headers["HTTP_X_ORGANIZATION_ID"] = org_id
    headers.update(extra)
    return headers


def create_books(api, token, *, name, currency, month, country):
    org_resp = api.post("/api/v1/organizations", {"name": name}, format="json", **auth_headers(token))
    assert org_resp.status_code == 201, org_resp.content
    org = org_resp.json()["data"]
    resp = api.put(
        "/api/v1/finance/settings",
        {
            "country_code": country,
            "base_currency": currency,
            "fiscal_year_start_month": month,
            "timezone": "UTC",
            "locale": "en",
            "tax_registration_applies": False,
        },
        format="json",
        **auth_headers(token, org["id"]),
    )
    assert resp.status_code == 200, resp.content
    cash = api.post(
        "/api/v1/finance/accounts",
        {"code": "1000", "name": "Cash", "classification": "asset"},
        format="json",
        **auth_headers(token, org["id"]),
    ).json()["data"]
    equity = api.post(
        "/api/v1/finance/accounts",
        {"code": "3000", "name": "Opening equity", "classification": "equity"},
        format="json",
        **auth_headers(token, org["id"]),
    ).json()["data"]
    income = api.post(
        "/api/v1/finance/accounts",
        {"code": "4000", "name": "Revenue", "classification": "income"},
        format="json",
        **auth_headers(token, org["id"]),
    ).json()["data"]
    ar = api.post(
        "/api/v1/finance/accounts",
        {"code": "1100", "name": "AR", "classification": "asset", "is_control": True, "control_kind": "ar"},
        format="json",
        **auth_headers(token, org["id"]),
    ).json()["data"]
    return org, cash, equity, income, ar


@pytest.mark.django_db
def test_two_organizations_isolated(api, rsa_keys, auth_user):
    private_pem, public_pem = rsa_keys
    token = make_token(private_pem)
    with override_settings(CLERK_JWT_KEY=public_pem, **CLERK):
        a, *_rest = create_books(api, token, name="A Co", currency="USD", month=1, country="US")
        b, cash_b, *_ = create_books(api, token, name="B Co", currency="EUR", month=7, country="DE")
        listed = api.get("/api/v1/organizations", **auth_headers(token)).json()["data"]["items"]
        assert {row["id"] for row in listed} >= {a["id"], b["id"]}
        settings_b = api.get("/api/v1/finance/settings", **auth_headers(token, b["id"])).json()["data"]
        assert settings_b["base_currency"] == "EUR"
        assert settings_b["fiscal_year_start_month"] == 7
        settings_a = api.get("/api/v1/finance/settings", **auth_headers(token, a["id"])).json()["data"]
        assert settings_a["base_currency"] == "USD"
        accounts_a = api.get("/api/v1/finance/accounts", **auth_headers(token, a["id"])).json()["data"]["items"]
        cash_id = next(x["id"] for x in accounts_a if x["code"] == "1000")
        eq_id = next(x["id"] for x in accounts_a if x["code"] == "3000")
        assert cash_b["id"] not in {x["id"] for x in accounts_a}
        draft = api.post(
            "/api/v1/finance/journals",
            {
                "entry_date": "2026-01-01",
                "source_type": "opening",
                "lines": [
                    {"account_id": cash_id, "debit": "100.00", "credit": "0"},
                    {"account_id": eq_id, "debit": "0", "credit": "100.00"},
                ],
            },
            format="json",
            **auth_headers(token, a["id"]),
        )
        assert draft.status_code == 201, draft.content
        posted = api.post(
            f"/api/v1/finance/journals/{draft.json()['data']['id']}/post",
            {"version": 1},
            format="json",
            **auth_headers(token, a["id"], HTTP_IDEMPOTENCY_KEY="k-open-a"),
        )
        assert posted.status_code == 200, posted.content
        blocked = api.put(
            "/api/v1/finance/settings",
            {
                "country_code": "US",
                "base_currency": "EUR",
                "fiscal_year_start_month": 1,
                "timezone": "UTC",
                "locale": "en",
                "tax_registration_applies": False,
            },
            format="json",
            **auth_headers(token, a["id"]),
        )
        assert blocked.status_code == 409
        assert blocked.json()["error"]["code"] == "base_currency_locked"


@pytest.mark.django_db
def test_access_and_posting(api, rsa_keys, auth_user, other_user):
    private_pem, public_pem = rsa_keys
    token = make_token(private_pem)
    viewer_token = make_token(private_pem, sub="user_clerk_2", sid="sess_2")
    with override_settings(CLERK_JWT_KEY=public_pem, **CLERK):
        org, cash, equity, income, ar = create_books(
            api, token, name="Books", currency="USD", month=1, country="US"
        )
        grant = api.put(
            f"/api/v1/finance/grants/{other_user.id}",
            {"role_slug": "viewer"},
            format="json",
            **auth_headers(token, org["id"]),
        )
        assert grant.status_code == 200, grant.content
        assert FinanceAuditEvent.objects.filter(action="access.grant").exists()

        denied = api.post(
            "/api/v1/finance/journals",
            {"entry_date": "2026-01-02", "lines": []},
            format="json",
            **auth_headers(viewer_token, org["id"]),
        )
        assert denied.status_code == 403

        unbalanced = api.post(
            "/api/v1/finance/journals",
            {
                "entry_date": "2026-01-02",
                "lines": [
                    {"account_id": cash["id"], "debit": "10", "credit": "0"},
                    {"account_id": income["id"], "debit": "0", "credit": "5"},
                ],
            },
            format="json",
            **auth_headers(token, org["id"]),
        )
        assert unbalanced.status_code == 201
        fail = api.post(
            f"/api/v1/finance/journals/{unbalanced.json()['data']['id']}/post",
            {"version": 1},
            format="json",
            **auth_headers(token, org["id"], HTTP_IDEMPOTENCY_KEY="k-imbalance"),
        )
        assert fail.status_code == 422
        assert fail.json()["error"]["code"] == "journal_imbalanced"
        assert JournalEntry.objects.filter(status=JournalEntry.Status.POSTED).count() == 0
        JournalEntry.objects.filter(id=unbalanced.json()["data"]["id"]).delete()

        control = api.post(
            "/api/v1/finance/journals",
            {
                "entry_date": "2026-01-02",
                "source_type": "manual",
                "lines": [
                    {"account_id": ar["id"], "debit": "10", "credit": "0"},
                    {"account_id": income["id"], "debit": "0", "credit": "10"},
                ],
            },
            format="json",
            **auth_headers(token, org["id"]),
        )
        assert control.status_code == 422
        assert control.json()["error"]["code"] == "control_account_restricted"

        draft = api.post(
            "/api/v1/finance/journals",
            {
                "entry_date": "2026-01-02",
                "lines": [
                    {"account_id": cash["id"], "debit": "60.00", "credit": "0"},
                    {"account_id": income["id"], "debit": "0", "credit": "60.00"},
                ],
            },
            format="json",
            **auth_headers(token, org["id"]),
        ).json()["data"]
        posted = api.post(
            f"/api/v1/finance/journals/{draft['id']}/post",
            {"version": draft["version"]},
            format="json",
            **auth_headers(token, org["id"], HTTP_IDEMPOTENCY_KEY="k1"),
        )
        assert posted.status_code == 200, posted.content
        jid = posted.json()["data"]["id"]
        replay = api.post(
            f"/api/v1/finance/journals/{jid}/post",
            {"version": draft["version"]},
            format="json",
            **auth_headers(token, org["id"], HTTP_IDEMPOTENCY_KEY="k1"),
        )
        assert replay.json()["data"]["id"] == jid
        conflict = api.post(
            f"/api/v1/finance/journals/{jid}/post",
            {"version": 99},
            format="json",
            **auth_headers(token, org["id"], HTTP_IDEMPOTENCY_KEY="k1"),
        )
        assert conflict.status_code == 409

        mutate = api.patch(
            f"/api/v1/finance/journals/{jid}",
            {"memo": "nope", "version": posted.json()["data"]["version"]},
            format="json",
            **auth_headers(token, org["id"]),
        )
        assert mutate.json()["error"]["code"] == "validation_error"

        reversal = api.post(
            f"/api/v1/finance/journals/{jid}/reverse",
            {"reason": "correction"},
            format="json",
            **auth_headers(token, org["id"], HTTP_IDEMPOTENCY_KEY="rev1"),
        )
        assert reversal.status_code == 201, reversal.content
        original = JournalEntry.objects.get(id=jid)
        assert original.status == JournalEntry.Status.POSTED
        assert original.reversed_by_id == reversal.json()["data"]["id"]
        again = api.post(
            f"/api/v1/finance/journals/{jid}/reverse",
            {"reason": "correction again"},
            format="json",
            **auth_headers(token, org["id"], HTTP_IDEMPOTENCY_KEY="rev2"),
        )
        assert again.status_code == 409

        tb = api.get(
            "/api/v1/finance/reports/trial-balance?from=2026-01-01&to=2026-12-31",
            **auth_headers(token, org["id"]),
        ).json()["data"]["items"]
        gl = api.get(
            "/api/v1/finance/reports/general-ledger?from=2026-01-01&to=2026-12-31",
            **auth_headers(token, org["id"]),
        ).json()["data"]["items"]
        assert gl and all("journal_id" in row for row in gl)
        assert sum(float(r["debit"]) for r in tb) == sum(float(r["credit"]) for r in tb)

        period = api.post(
            "/api/v1/finance/periods",
            {"start_on": "2026-01-01", "end_on": "2026-01-31"},
            format="json",
            **auth_headers(token, org["id"]),
        ).json()["data"]
        JournalEntry.objects.filter(organization_id=org["id"], status=JournalEntry.Status.DRAFT).delete()
        lock_resp = api.post(
            f"/api/v1/finance/periods/{period['id']}/lock",
            {},
            format="json",
            **auth_headers(token, org["id"]),
        )
        assert lock_resp.status_code == 200, lock_resp.content
        draft2 = api.post(
            "/api/v1/finance/journals",
            {
                "entry_date": "2026-01-15",
                "lines": [
                    {"account_id": cash["id"], "debit": "1", "credit": "0"},
                    {"account_id": income["id"], "debit": "0", "credit": "1"},
                ],
            },
            format="json",
            **auth_headers(token, org["id"]),
        ).json()["data"]
        fail_close = api.post(
            f"/api/v1/finance/journals/{draft2['id']}/post",
            {"version": 1},
            format="json",
            **auth_headers(token, org["id"], HTTP_IDEMPOTENCY_KEY="closed"),
        )
        assert fail_close.json()["error"]["code"] == "period_closed"
        assert api.post(
            f"/api/v1/finance/periods/{period['id']}/reopen",
            {"reason": "fix"},
            format="json",
            **auth_headers(token, org["id"]),
        ).status_code == 200
        stale = api.patch(
            f"/api/v1/finance/journals/{draft2['id']}",
            {"memo": "x", "version": 0},
            format="json",
            **auth_headers(token, org["id"]),
        )
        assert stale.json()["error"]["code"] == "stale_version"
        assert api.put(
            f"/api/v1/finance/grants/{other_user.id}",
            {"role_slug": "sales_clerk"},
            format="json",
            **auth_headers(token, org["id"]),
        ).status_code == 200
        post_denied = api.post(
            f"/api/v1/finance/journals/{draft2['id']}/post",
            {"version": 1},
            format="json",
            **auth_headers(viewer_token, org["id"], HTTP_IDEMPOTENCY_KEY="sales-post"),
        )
        assert post_denied.status_code == 403


@pytest.mark.django_db
def test_member_without_grant_denied(api, rsa_keys, auth_user, other_user):
    private_pem, public_pem = rsa_keys
    token = make_token(private_pem)
    with override_settings(CLERK_JWT_KEY=public_pem, **CLERK):
        org, *_ = create_books(api, token, name="Solo", currency="JPY", month=4, country="JP")
        Membership.objects.create(
            user_id=other_user.id,
            organization_id=org["id"],
            status=Membership.Status.ACTIVE,
            roles=["member"],
        )
        viewer_token = make_token(private_pem, sub="user_clerk_2", sid="sess_2")
        resp = api.get("/api/v1/finance/journals", **auth_headers(viewer_token, org["id"]))
        assert resp.status_code == 403
        assert not FinanceGrant.objects.filter(user_id=other_user.id).exists()


@pytest.mark.django_db
def test_location_membership_without_grant(api, rsa_keys, auth_user, other_user):
    private_pem, public_pem = rsa_keys
    token = make_token(private_pem)
    with override_settings(CLERK_JWT_KEY=public_pem, **CLERK):
        org, *_ = create_books(api, token, name="LocCo", currency="KWD", month=1, country="KW")
        loc = Location.objects.create(organization_id=org["id"], name="Warehouse")
        Membership.objects.create(
            user_id=other_user.id,
            organization_id=org["id"],
            location=loc,
            status=Membership.Status.ACTIVE,
            roles=["member"],
        )
        viewer_token = make_token(private_pem, sub="user_clerk_2", sid="sess_2")
        resp = api.get(
            "/api/v1/finance/reports/trial-balance?from=2026-01-01&to=2026-12-31",
            **auth_headers(viewer_token, org["id"]),
            HTTP_X_LOCATION_ID=loc.id,
        )
        assert resp.status_code == 403
