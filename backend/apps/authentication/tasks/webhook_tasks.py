from celery import shared_task
from django.utils import timezone

from apps.authentication.crypto import encrypt_field, hmac_email
from apps.authentication.models import AuthUser, ProviderEvent, SessionProjection
from apps.authentication.services.cache_service import AuthCacheService
from apps.authentication.services.rls import celery_rls_context
from apps.authentication.services.security_service import IdentityService, SecurityService


@shared_task(bind=True, max_retries=5, default_retry_delay=30)
def process_clerk_event(self, provider_event_id: str):
    event = ProviderEvent.objects.filter(id=provider_event_id).first()
    if not event or event.processed_at:
        return
    event.status = ProviderEvent.Status.PROCESSING
    event.processing_started_at = timezone.now()
    event.attempts += 1
    event.save(update_fields=["status", "processing_started_at", "attempts"])

    payload = event.payload or {}
    etype = event.event_type or payload.get("type", "")
    data = payload.get("data") or {}
    cache = AuthCacheService()
    security = SecurityService()
    identity = IdentityService()

    try:
        if etype in ("user.created", "user.updated"):
            clerk_user_id = data.get("id")
            if clerk_user_id:
                emails = data.get("email_addresses") or []
                primary = ""
                verified = False
                for e in emails:
                    if e.get("id") == data.get("primary_email_address_id") or not primary:
                        primary = e.get("email_address", "")
                        verified = (e.get("verification") or {}).get("status") == "verified"
                user, _ = AuthUser.objects.update_or_create(
                    clerk_user_id=clerk_user_id,
                    defaults={
                        "primary_email_hash": hmac_email(primary)
                        if primary
                        else hmac_email(clerk_user_id),
                        "primary_email_ciphertext": encrypt_field(primary) or "",
                        "first_name": data.get("first_name") or "",
                        "last_name": data.get("last_name") or "",
                        "email_verified": verified,
                        "avatar_url": data.get("image_url") or "",
                    },
                )
                celery_rls_context(user_id=user.id)
                cache.invalidate_user(clerk_user_id)
                security.record(
                    user=user,
                    event_type=security.EVENT_WEBHOOK_PROCESSED,
                    metadata={"event_type": etype},
                )
        elif etype == "user.deleted":
            clerk_user_id = data.get("id")
            if clerk_user_id:
                user = AuthUser.objects.filter(clerk_user_id=clerk_user_id).first()
                if user:
                    identity.anonymize(user)
                    cache.invalidate_user(clerk_user_id)
        elif etype in ("session.revoked", "session.ended"):
            sid = data.get("id")
            if sid:
                SessionProjection.objects.filter(clerk_session_id=sid).update(
                    status=SessionProjection.Status.ENDED,
                    ended_at=timezone.now(),
                )
        event.status = ProviderEvent.Status.PROCESSED
        event.processed_at = timezone.now()
        event.save(update_fields=["status", "processed_at"])
    except Exception as exc:  # noqa: BLE001
        event.status = ProviderEvent.Status.FAILED
        event.error_code = type(exc).__name__
        event.error_summary = str(exc)[:500]
        event.save(update_fields=["status", "error_code", "error_summary"])
        security.record(
            user=None,
            event_type=security.EVENT_WEBHOOK_FAILED,
            metadata={"event_id": event.id, "error": event.error_code},
            severity="error",
        )
        raise
