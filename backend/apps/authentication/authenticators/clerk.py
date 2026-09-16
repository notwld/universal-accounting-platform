import logging
from typing import Any

import httpx
import jwt
from django.conf import settings
from django.core.cache import cache
from django.db import OperationalError
from rest_framework import authentication, exceptions

from apps.authentication.models import AuthUser
from apps.authentication.services.cache_service import AuthCacheService

logger = logging.getLogger(__name__)


def _fail(code: str, message: str, *, status=401):
    if status == 403:
        raise exceptions.PermissionDenied({"code": code, "message": message})
    raise exceptions.AuthenticationFailed({"code": code, "message": message})


class ClerkJWTAuthentication(authentication.BaseAuthentication):
    """Verify Clerk session JWT locally. Never call Clerk Backend API per request."""

    keyword = "Bearer"

    def authenticate(self, request):
        header = authentication.get_authorization_header(request).decode("utf-8")
        if not header:
            return None
        parts = header.split()
        if len(parts) != 2 or parts[0] != self.keyword:
            return None
        token = parts[1]
        claims = self._verify(token)
        clerk_user_id = claims.get("sub")
        if not clerk_user_id:
            _fail("invalid_token", "Token missing subject")
        sid = claims.get("sid") or claims.get("session_id")
        if not sid:
            _fail("invalid_session", "Token missing session id")
        request.clerk_claims = claims
        request.clerk_session_id = sid

        user = self._resolve_user(clerk_user_id)
        if user and user.status == AuthUser.Status.SUSPENDED:
            _fail("account_suspended", "Application account suspended", status=403)
        if user and user.status == AuthUser.Status.DELETED:
            _fail("invalid_session", "Account no longer available")
        return (user, claims) if user else (ClerkPrincipal(clerk_user_id, claims), claims)

    def _resolve_user(self, clerk_user_id: str) -> AuthUser | None:
        cache_svc = AuthCacheService()
        cached = cache_svc.get_user(clerk_user_id)
        try:
            if cached and cached.get("id"):
                user = AuthUser.objects.filter(id=cached["id"], deleted_at__isnull=True).first()
            else:
                user = AuthUser.objects.filter(
                    clerk_user_id=clerk_user_id, deleted_at__isnull=True
                ).first()
        except OperationalError as exc:
            logger.error("auth_db_unavailable", extra={"error": str(exc)})
            _fail("identity_dependency_unavailable", "Database unavailable", status=503)
            raise
        if user:
            cache_svc.set_user(
                clerk_user_id,
                {
                    "id": user.id,
                    "authorization_version": user.authorization_version,
                    "status": user.status,
                },
            )
        return user

    def _verify(self, token: str) -> dict[str, Any]:
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as exc:
            _fail("invalid_token", "Malformed token")
            raise exc  # pragma: no cover

        key = self._resolve_key(header.get("kid"))
        options = {"require": ["exp", "iat", "nbf", "sub"]}
        leeway = settings.CLERK_CLOCK_SKEW_MS / 1000.0
        try:
            claims = jwt.decode(
                token,
                key=key,
                algorithms=["RS256", "ES256"],
                issuer=settings.CLERK_ISSUER or None,
                leeway=leeway,
                options={**options, "verify_iss": bool(settings.CLERK_ISSUER)},
            )
        except jwt.ExpiredSignatureError as exc:
            _fail("expired_token", "Session token expired")
            raise exc  # pragma: no cover
        except jwt.InvalidIssuerError as exc:
            _fail("invalid_token_issuer", "Token issuer is not trusted")
            raise exc  # pragma: no cover
        except jwt.MissingRequiredClaimError as exc:
            claim = getattr(exc, "claim", "claim")
            if claim == "nbf":
                _fail("invalid_token", "Token not yet valid (nbf)")
            _fail("invalid_token", f"Missing required claim: {claim}")
            raise exc  # pragma: no cover
        except jwt.PyJWTError as exc:
            _fail("invalid_token", "Invalid session token")
            raise exc  # pragma: no cover

        if settings.CLERK_VERIFY_AUTHORIZED_PARTY and settings.CLERK_AUTHORIZED_PARTIES:
            azp = claims.get("azp") or claims.get("aud")
            allowed = set(settings.CLERK_AUTHORIZED_PARTIES)
            ok = (
                bool(allowed.intersection(azp))
                if isinstance(azp, list)
                else azp in allowed
            )
            if not ok:
                _fail("invalid_authorized_party", "Unauthorized party")
        return claims

    def _resolve_key(self, kid: str | None):
        if settings.CLERK_JWT_KEY:
            return settings.CLERK_JWT_KEY
        jwks = self._jwks()
        for jwk in jwks.get("keys", []):
            if kid is None or jwk.get("kid") == kid:
                return jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
        _fail("invalid_token", "Signing key not found")

    def _jwks(self) -> dict:
        cache_key = "clerk:jwks"
        cached = cache.get(cache_key)
        if cached:
            return cached
        url = settings.CLERK_JWKS_URL
        if not url and settings.CLERK_ISSUER:
            url = settings.CLERK_ISSUER.rstrip("/") + "/.well-known/jwks.json"
        if not url:
            _fail("misconfigured", "Clerk JWKS not configured")
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(url)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:  # noqa: BLE001
            logger.warning("jwks_fetch_failed", extra={"error": type(exc).__name__})
            _fail("identity_dependency_unavailable", "Unable to verify token")
            raise
        cache.set(cache_key, data, timeout=3600)
        return data


class ClerkPrincipal:
    """Unauthenticated-to-app principal used during JIT bootstrap."""

    is_authenticated = True
    is_anonymous = False

    def __init__(self, clerk_user_id: str, claims: dict):
        self.clerk_user_id = clerk_user_id
        self.claims = claims
        self.id = None
        self.pk = None
