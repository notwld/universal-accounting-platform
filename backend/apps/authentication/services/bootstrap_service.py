import hashlib
import json
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, OperationalError, transaction
from django.utils import timezone

from apps.authentication.exceptions import AuthAPIError
from apps.authentication.models import AuthUser, IdempotencyRecord
from apps.authentication.services.cache_service import AuthCacheService
from apps.authentication.services.context_service import ContextService
from apps.authentication.services.security_service import IdentityService, SecurityService
from apps.authentication.services.session_service import SessionService


class BootstrapService:
    def __init__(self):
        self.identity = IdentityService()
        self.sessions = SessionService()
        self.context = ContextService()
        self.security = SecurityService()
        self.cache = AuthCacheService()

    def run(self, *, request, claims: dict, payload: dict) -> dict:
        if claims.get("sub") is None:
            raise AuthAPIError("invalid_token", "Missing subject")

        lock_key = f"bootstrap:{claims['sub']}"
        self.cache.acquire_lock(lock_key, ttl=30)
        try:
            try:
                user = self.identity.upsert_from_claims(claims, payload.get("preferences"))
            except OperationalError as exc:
                raise AuthAPIError(
                    "identity_dependency_unavailable",
                    "Database unavailable",
                ) from exc
            if user.status == AuthUser.Status.SUSPENDED:
                raise AuthAPIError("account_suspended", "Application account suspended")
            session_id = getattr(request, "clerk_session_id", None) or claims.get("sid")
            self.sessions.upsert_projection(
                user=user,
                clerk_session_id=session_id,
                device=payload.get("device"),
                request=request,
            )
            org, loc, roles = self.context.resolve_defaults(user)
            self.cache.set_user(
                user.clerk_user_id,
                {
                    "id": user.id,
                    "authorization_version": user.authorization_version,
                    "status": user.status,
                },
            )
            self.security.record(
                user=user,
                event_type=self.security.EVENT_BOOTSTRAP,
                request=request,
                organization_id=org.id if org else "",
                location_id=loc.id if loc else "",
                metadata={"roles": roles},
            )
            email = self.identity.email_plaintext(user)
            return {
                "user": {
                    "id": user.id,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": email,
                    "email_verified": user.email_verified,
                    "status": user.status,
                },
                "context": {
                    "organization_id": org.id if org else None,
                    "location_id": loc.id if loc else None,
                },
                "authorization": {
                    "version": user.authorization_version,
                    "roles": roles,
                },
                "onboarding": {
                    "required": org is None,
                    "next_step": "create_organization" if org is None else None,
                },
            }
        finally:
            self.cache.release_lock(lock_key)


class IdempotencyService:
    def begin(self, *, key: str | None, user_id: str, body: dict, method="", path="", organization_id=""):
        if not settings.IDEMPOTENCY_ENABLED or not key:
            return None
        request_hash = hashlib.sha256(
            json.dumps(body, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        key_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()
        existing = IdempotencyRecord.objects.filter(key=key, user_id=user_id).first()
        if existing:
            if existing.expires_at < timezone.now():
                existing.delete()
            elif existing.request_hash != request_hash:
                raise AuthAPIError(
                    "idempotency_conflict",
                    "Idempotency key reused with different payload",
                )
            elif existing.response_body is not None:
                return existing
        expires = timezone.now() + timedelta(seconds=settings.IDEMPOTENCY_RECORD_TTL_SECONDS)
        try:
            with transaction.atomic():
                return IdempotencyRecord.objects.create(
                    key=key,
                    key_hash=key_hash,
                    user_id=user_id,
                    method=method,
                    path=path,
                    organization_id=organization_id or "",
                    request_hash=request_hash,
                    expires_at=expires,
                )
        except IntegrityError:
            existing = IdempotencyRecord.objects.filter(key=key, user_id=user_id).first()
            if existing and existing.response_body is not None:
                return existing
            raise AuthAPIError("idempotency_conflict", "Idempotency key in progress")

    def complete(self, record: IdempotencyRecord | None, status_code: int, body: dict):
        if record is None:
            return
        record.response_status = status_code
        record.response_body = body
        record.save(update_fields=["response_status", "response_body"])
