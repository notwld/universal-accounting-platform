"""Webhook orchestration service (MD §79)."""

from apps.authentication.models import ProviderEvent
from apps.authentication.tasks.webhook_tasks import process_clerk_event


class WebhookService:
    def enqueue(self, provider_event: ProviderEvent):
        process_clerk_event.delay(provider_event.id)
        return provider_event
