from django.conf import settings
from django.utils import timezone

from apps.authentication.crypto import encrypt_field, hash_for_audit, hmac_email
from apps.authentication.models import AuthUser, SecurityEvent
from apps.authentication.tasks.security_tasks import send_security_email


class SecurityService:
    EVENT_BOOTSTRAP = "auth.application_bootstrap"
    EVENT_CONTEXT_SWITCH = "auth.context_switched"
    EVENT_SESSION_SEEN = "auth.session_seen"
    EVENT_ACCOUNT_SUSPENDED = "auth.account_suspended"
    EVENT_WEBHOOK_PROCESSED = "auth.webhook_processed"
    EVENT_WEBHOOK_RECEIVED = "auth.webhook_received"
    EVENT_WEBHOOK_FAILED = "auth.webhook_failed"
    EVENT_WEBHOOK_DUPLICATE = "auth.webhook_duplicate"

    def record(
        self,
        *,
        user: AuthUser | None,
        event_type: str,
        request=None,
        organization_id: str = "",
        location_id: str = "",
        metadata: dict | None = None,
        notify_email: bool = False,
        severity: str = "info",
    ) -> SecurityEvent:
        ip_hash = ""
        ua_hash = ""
        request_id = ""
        clerk_session_id = ""
        if request is not None:
            request_id = getattr(request, "request_id", "") or ""
            clerk_session_id = getattr(request, "clerk_session_id", "") or ""
            ip = request.META.get("REMOTE_ADDR", "")
            ua = request.META.get("HTTP_USER_AGENT", "")
            if settings.AUDIT_HASH_IP_ADDRESSES:
                ip_hash = hash_for_audit(ip) or ""
            else:
                ip_hash = ip
            if settings.AUDIT_HASH_USER_AGENTS:
                ua_hash = hash_for_audit(ua) or ""
            else:
                ua_hash = ua[:64]
        event = SecurityEvent.objects.create(
            user=user,
            event_type=event_type,
            organization_id=organization_id or "",
            location_id=location_id or "",
            request_id=request_id,
            clerk_session_id=clerk_session_id or "",
            severity=severity,
            ip_hash=ip_hash,
            user_agent_hash=ua_hash,
            metadata=metadata or {},
        )
        if notify_email and user and settings.SECURITY_NOTIFY_EMAIL_ENABLED:
            try:
                send_security_email.delay(user.id, event_type, event.id)
            except Exception:  # noqa: BLE001
                pass
        return event


class IdentityService:
    def upsert_from_claims(self, claims: dict, preferences: dict | None = None) -> AuthUser:
        clerk_user_id = claims["sub"]
        email = claims.get("email") or ""
        if isinstance(email, dict):
            email = email.get("email_address", "")
        first = claims.get("first_name") or claims.get("given_name") or ""
        last = claims.get("last_name") or claims.get("family_name") or ""
        verified = bool(claims.get("email_verified", False))
        prefs = preferences or {}

        user, created = AuthUser.objects.get_or_create(
            clerk_user_id=clerk_user_id,
            defaults={
                "primary_email_hash": hmac_email(email) if email else hmac_email(clerk_user_id),
                "primary_email_ciphertext": encrypt_field(email) or "",
                "first_name": first or "",
                "last_name": last or "",
                "email_verified": verified,
                "timezone": prefs.get("timezone", ""),
                "locale": prefs.get("locale", ""),
                "last_authenticated_at": timezone.now(),
                "last_seen_at": timezone.now(),
            },
        )
        if not created:
            if email:
                user.primary_email_hash = hmac_email(email)
                user.primary_email_ciphertext = encrypt_field(email) or ""
            if first:
                user.first_name = first
            if last:
                user.last_name = last
            user.email_verified = verified
            if prefs.get("timezone"):
                user.timezone = prefs["timezone"]
            if prefs.get("locale"):
                user.locale = prefs["locale"]
            user.last_authenticated_at = timezone.now()
            user.last_seen_at = timezone.now()
            user.save()
        return user

    def anonymize(self, user: AuthUser) -> AuthUser:
        """Privacy: strip PII on deletion (MD §74–75)."""
        user.first_name = ""
        user.last_name = ""
        user.avatar_url = ""
        user.primary_email_ciphertext = ""
        user.primary_email_hash = hmac_email(f"deleted:{user.id}")
        user.email_verified = False
        user.status = AuthUser.Status.DELETED
        user.deleted_at = timezone.now()
        user.authorization_version += 1
        user.save()
        return user

    def email_plaintext(self, user: AuthUser) -> str:
        from apps.authentication.crypto import decrypt_field

        return decrypt_field(user.primary_email_ciphertext) or ""
