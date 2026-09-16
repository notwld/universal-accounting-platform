from celery import shared_task
from django.utils import timezone
from datetime import timedelta

from apps.authentication.models import IdempotencyRecord, ProviderEvent, SessionProjection


@shared_task
def cleanup_expired_idempotency():
    IdempotencyRecord.objects.filter(expires_at__lt=timezone.now()).delete()


@shared_task
def cleanup_provider_events():
    from django.conf import settings

    days = getattr(settings, "PROVIDER_EVENT_RETENTION_DAYS", 30) or 30
    cutoff = timezone.now() - timedelta(days=days)
    ProviderEvent.objects.filter(processed_at__lt=cutoff).delete()


@shared_task
def expire_local_session_projection():
    """Mark stale active projections expired (Clerk remains authority)."""
    cutoff = timezone.now() - timedelta(days=30)
    SessionProjection.objects.filter(
        status=SessionProjection.Status.ACTIVE, last_seen_at__lt=cutoff
    ).update(status=SessionProjection.Status.EXPIRED, ended_at=timezone.now())


@shared_task
def reconcile_unprocessed_webhooks():
    from apps.authentication.tasks.webhook_tasks import process_clerk_event

    cutoff = timezone.now() - timedelta(minutes=2)
    qs = ProviderEvent.objects.filter(
        processed_at__isnull=True,
        status__in=[ProviderEvent.Status.RECEIVED, ProviderEvent.Status.FAILED],
        received_at__lte=cutoff,
    )[:100]
    for event in qs:
        process_clerk_event.delay(event.id)
