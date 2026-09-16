from django.conf import settings
from django.utils import timezone

from apps.authentication.crypto import hash_for_audit
from apps.authentication.models import SessionProjection
from apps.authentication.services.security_service import SecurityService


def _browser_family(ua: str) -> str:
    ua_l = (ua or "").lower()
    for name in ("edg", "chrome", "firefox", "safari", "opera"):
        if name in ua_l:
            return "Edge" if name == "edg" else name.capitalize()
    return "unknown"


class SessionService:
    def __init__(self):
        self.security = SecurityService()

    def upsert_projection(self, *, user, clerk_session_id: str | None, device: dict | None, request):
        if not settings.AUTH_SESSION_PROJECTION_ENABLED:
            return None
        if not clerk_session_id:
            return None
        device = device or {}
        ip = request.META.get("REMOTE_ADDR", "")
        ua = request.META.get("HTTP_USER_AGENT", "")
        defaults = {
            "user": user,
            "status": SessionProjection.Status.ACTIVE,
            "device_name": (device.get("name") or "")[:100],
            "device_platform": (device.get("platform") or "")[:40],
            "browser_family": _browser_family(ua)[:50],
            "app_version": (device.get("app_version") or "")[:30],
            "ip_hash": (hash_for_audit(ip) if settings.AUDIT_HASH_IP_ADDRESSES else ip) or "",
            "user_agent_hash": (
                (hash_for_audit(ua) if settings.AUDIT_HASH_USER_AGENTS else (ua[:64] if ua else ""))
                or ""
            ),
            "last_seen_at": timezone.now(),
            "ended_at": None,
        }
        session, created = SessionProjection.objects.update_or_create(
            clerk_session_id=clerk_session_id,
            defaults=defaults,
        )
        if created:
            self.security.record(
                user=user,
                event_type=self.security.EVENT_SESSION_SEEN,
                request=request,
                metadata={"session_id": session.id, "created": True},
                notify_email=True,
            )
        return session

    def list_for_user(self, user, *, current_session_id: str | None = None):
        return (
            SessionProjection.objects.filter(user=user)
            .order_by("-last_seen_at")
        )
