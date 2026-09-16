"""Thin selectors layer (MD §79)."""

from apps.authentication.models import AuthUser, SecurityEvent, SessionProjection


def get_user_by_clerk_id(clerk_user_id: str) -> AuthUser | None:
    return AuthUser.objects.filter(clerk_user_id=clerk_user_id, deleted_at__isnull=True).first()


def active_sessions_for_user(user_id: str):
    return SessionProjection.objects.filter(
        user_id=user_id, status=SessionProjection.Status.ACTIVE
    ).order_by("-last_seen_at")


def security_events_for_user(user_id: str):
    return SecurityEvent.objects.filter(user_id=user_id).order_by("-occurred_at")
