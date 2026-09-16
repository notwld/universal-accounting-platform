import hashlib
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.test import override_settings
from rest_framework.test import APIClient

from apps.authentication.models import AuthUser, IdempotencyRecord, ProviderEvent
from apps.tenancy.models import Location, Membership, Organization


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


def make_token(private_pem, *, claims_extra=None, exp_delta=3600, issuer="https://example.clerk.accounts.dev"):
    now = datetime.now(timezone.utc)
    claims = {
        "sub": "user_clerk_1",
        "sid": "sess_1",
        "email": "ada@example.com",
        "email_verified": True,
        "first_name": "Ada",
        "last_name": "Lovelace",
        "azp": "http://localhost:5173",
        "iss": issuer,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()) - 1,
        "exp": int((now + timedelta(seconds=exp_delta)).timestamp()),
    }
    if claims_extra:
        claims.update(claims_extra)
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
def membership(auth_user):
    org = Organization.objects.create(name="ABC Trading")
    loc = Location.objects.create(organization=org, name="Lahore")
    Membership.objects.create(
        user_id=auth_user.id,
        organization=org,
        location=loc,
        roles=["owner"],
        status=Membership.Status.ACTIVE,
    )
    return org, loc


@pytest.mark.django_db
@override_settings(
    CLERK_JWT_KEY=None,
    CLERK_ISSUER="https://example.clerk.accounts.dev",
    CLERK_AUTHORIZED_PARTIES=["http://localhost:5173"],
    CLERK_VERIFY_AUTHORIZED_PARTY=True,
)
def test_valid_clerk_token_accepted(api, rsa_keys, auth_user):
    private_pem, public_pem = rsa_keys
    with override_settings(CLERK_JWT_KEY=public_pem):
        token = make_token(private_pem)
        resp = api.get("/api/v1/auth/me", HTTP_AUTHORIZATION=f"Bearer {token}")
    assert resp.status_code == 200
    assert resp.data["data"]["identity"]["clerk_user_id"] == "user_clerk_1"
    assert resp["Cache-Control"] == "no-store"


@pytest.mark.django_db
def test_webhook_duplicate_ignored(api, settings):
    settings.CLERK_WEBHOOK_SIGNING_SECRET = "whsec_test"
    ProviderEvent.objects.create(
        provider="clerk",
        external_event_id="evt_1",
        event_type="user.updated",
        payload_hash="x",
        status=ProviderEvent.Status.PROCESSED,
        processed_at=datetime.now(timezone.utc),
    )
    with patch("svix.webhooks.Webhook") as Wh:
        inst = Wh.return_value
        inst.verify.return_value = {"type": "user.updated", "data": {"id": "user_x"}}
        resp = api.post(
            "/api/v1/webhooks/clerk",
            data=b"{}",
            content_type="application/json",
            HTTP_SVIX_ID="evt_1",
            HTTP_SVIX_TIMESTAMP="1",
            HTTP_SVIX_SIGNATURE="v1,x",
        )
    assert resp.status_code == 200
    assert resp.data["data"]["duplicate"] is True


@pytest.mark.django_db
@override_settings(CLERK_ISSUER="https://example.clerk.accounts.dev", CLERK_VERIFY_AUTHORIZED_PARTY=False)
def test_expired_token_rejected(api, rsa_keys, auth_user):
    private_pem, public_pem = rsa_keys
    with override_settings(CLERK_JWT_KEY=public_pem):
        token = make_token(private_pem, exp_delta=-60)
        resp = api.get("/api/v1/auth/me", HTTP_AUTHORIZATION=f"Bearer {token}")
    assert resp.status_code == 401
    assert resp.data["error"]["code"] == "expired_token"
    assert resp["WWW-Authenticate"] == "Bearer"


@pytest.mark.django_db
@override_settings(CLERK_ISSUER="https://example.clerk.accounts.dev", CLERK_VERIFY_AUTHORIZED_PARTY=False)
def test_wrong_issuer_rejected(api, rsa_keys, auth_user):
    private_pem, public_pem = rsa_keys
    with override_settings(CLERK_JWT_KEY=public_pem):
        token = make_token(private_pem, issuer="https://evil.example")
        resp = api.get("/api/v1/auth/me", HTTP_AUTHORIZATION=f"Bearer {token}")
    assert resp.status_code == 401
    assert resp.data["error"]["code"] == "invalid_token_issuer"


@pytest.mark.django_db
@override_settings(
    CLERK_ISSUER="https://example.clerk.accounts.dev",
    CLERK_AUTHORIZED_PARTIES=["http://localhost:5173"],
    CLERK_VERIFY_AUTHORIZED_PARTY=True,
)
def test_wrong_azp_rejected(api, rsa_keys, auth_user):
    private_pem, public_pem = rsa_keys
    with override_settings(CLERK_JWT_KEY=public_pem):
        token = make_token(private_pem, claims_extra={"azp": "https://evil.example"})
        resp = api.get("/api/v1/auth/me", HTTP_AUTHORIZATION=f"Bearer {token}")
    assert resp.status_code == 401
    assert resp.data["error"]["code"] == "invalid_authorized_party"


@pytest.mark.django_db
def test_missing_token_rejected(api):
    resp = api.get("/api/v1/auth/me")
    assert resp.status_code in (401, 403)


@pytest.mark.django_db
@override_settings(CLERK_ISSUER="https://example.clerk.accounts.dev", CLERK_VERIFY_AUTHORIZED_PARTY=False)
def test_suspended_user_rejected(api, rsa_keys, auth_user):
    from django.core.cache import cache

    auth_user.status = AuthUser.Status.SUSPENDED
    auth_user.save()
    cache.clear()
    private_pem, public_pem = rsa_keys
    with override_settings(CLERK_JWT_KEY=public_pem):
        token = make_token(private_pem)
        resp = api.get("/api/v1/auth/me", HTTP_AUTHORIZATION=f"Bearer {token}")
    assert resp.status_code == 403, resp.data
    assert resp.data["error"]["code"] == "account_suspended"


@pytest.mark.django_db
def test_cross_org_denied(api, auth_user, membership):
    other = Organization.objects.create(name="Other Co")

    class FakeAuth:
        def authenticate(self, request):
            request.clerk_claims = {"sub": auth_user.clerk_user_id, "sid": "sess_1"}
            request.clerk_session_id = "sess_1"
            return (auth_user, request.clerk_claims)

    from apps.authentication.api.v1.views import SwitchContextAPIView

    SwitchContextAPIView.authentication_classes = [FakeAuth]
    resp = api.post(
        "/api/v1/auth/context/switch",
        {"organization_id": other.id},
        format="json",
        HTTP_AUTHORIZATION="Bearer x",
    )
    assert resp.status_code == 403
    assert resp.data["error"]["code"] == "organization_access_denied"


@pytest.mark.django_db
def test_cross_location_denied(api, auth_user, membership):
    org, loc = membership
    other_loc = Location.objects.create(organization=org, name="Karachi")
    Membership.objects.filter(user_id=auth_user.id).update(location=loc)

    class FakeAuth:
        def authenticate(self, request):
            request.clerk_claims = {"sub": auth_user.clerk_user_id, "sid": "sess_1"}
            request.clerk_session_id = "sess_1"
            return (auth_user, request.clerk_claims)

    from apps.authentication.api.v1.views import SwitchContextAPIView

    SwitchContextAPIView.authentication_classes = [FakeAuth]
    resp = api.post(
        "/api/v1/auth/context/switch",
        {"organization_id": org.id, "location_id": other_loc.id},
        format="json",
        HTTP_AUTHORIZATION="Bearer x",
    )
    assert resp.status_code == 403
    assert resp.data["error"]["code"] == "location_access_denied"


@pytest.mark.django_db
def test_idempotency_replay_and_conflict(api, auth_user):
    class FakeAuth:
        def authenticate(self, request):
            request.clerk_claims = {
                "sub": auth_user.clerk_user_id,
                "sid": "sess_1",
                "email": "ada@example.com",
            }
            request.clerk_session_id = "sess_1"
            return (auth_user, request.clerk_claims)

    from apps.authentication.api.v1.views import BootstrapAPIView

    BootstrapAPIView.authentication_classes = [FakeAuth]
    headers = {"HTTP_AUTHORIZATION": "Bearer x", "HTTP_IDEMPOTENCY_KEY": "idem-1"}
    r1 = api.post("/api/v1/auth/bootstrap", {"device": {"name": "A"}}, format="json", **headers)
    r2 = api.post("/api/v1/auth/bootstrap", {"device": {"name": "A"}}, format="json", **headers)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.data["data"]["user"]["id"] == r2.data["data"]["user"]["id"]
    r3 = api.post("/api/v1/auth/bootstrap", {"device": {"name": "B"}}, format="json", **headers)
    assert r3.status_code == 409
    assert r3.data["error"]["code"] == "idempotency_conflict"


@pytest.mark.django_db
def test_webhook_bad_signature(api, settings):
    settings.CLERK_WEBHOOK_SIGNING_SECRET = "whsec_test"
    with patch("svix.webhooks.Webhook") as Wh:
        Wh.return_value.verify.side_effect = Exception("bad sig")
        resp = api.post(
            "/api/v1/webhooks/clerk",
            data=b"{}",
            content_type="application/json",
            HTTP_SVIX_ID="evt_2",
            HTTP_SVIX_TIMESTAMP="1",
            HTTP_SVIX_SIGNATURE="v1,x",
        )
    assert resp.status_code == 401
    assert resp.data["error"]["code"] == "webhook_invalid"


@pytest.mark.django_db
def test_bootstrap_jit(api):
    from apps.authentication.authenticators.clerk import ClerkPrincipal

    claims = {
        "sub": "user_new",
        "sid": "sess_new",
        "email": "new@example.com",
        "email_verified": True,
        "first_name": "New",
    }
    principal = ClerkPrincipal(claims["sub"], claims)

    class FakeAuth:
        def authenticate(self, request):
            request.clerk_claims = claims
            request.clerk_session_id = claims["sid"]
            return (principal, claims)

    from apps.authentication.api.v1 import views as v

    v.BootstrapAPIView.authentication_classes = [FakeAuth]
    resp = api.post(
        "/api/v1/auth/bootstrap",
        {"device": {"name": "Test", "platform": "web"}, "preferences": {"timezone": "UTC"}},
        format="json",
        HTTP_AUTHORIZATION="Bearer x",
    )
    assert resp.status_code == 200
    assert AuthUser.objects.filter(clerk_user_id="user_new").exists()


@pytest.mark.django_db
def test_health_ready(api):
    assert api.get("/health/").status_code == 200
    assert api.get("/ready/").status_code == 200
