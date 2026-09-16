import hashlib
import json
import logging

from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.authentication.exceptions import AuthAPIError, envelope_success
from apps.authentication.models import ProviderEvent
from apps.authentication.services.security_service import SecurityService
from apps.authentication.tasks.webhook_tasks import process_clerk_event

logger = logging.getLogger(__name__)


class ClerkWebhookAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    @extend_schema(
        tags=["Webhooks"],
        summary="Clerk webhook receiver",
        request=None,
        responses={200: OpenApiResponse(description="Accepted")},
        auth=[],
    )
    def post(self, request):
        secret = settings.CLERK_WEBHOOK_SIGNING_SECRET
        if not secret:
            raise AuthAPIError("misconfigured", "Webhook signing secret not configured")
        payload = request.body
        headers = {
            "svix-id": request.headers.get("svix-id", ""),
            "svix-timestamp": request.headers.get("svix-timestamp", ""),
            "svix-signature": request.headers.get("svix-signature", ""),
        }
        try:
            from svix.webhooks import Webhook

            wh = Webhook(secret)
            data = wh.verify(payload, headers)
        except Exception as exc:  # noqa: BLE001
            logger.warning("webhook_verify_failed", extra={"error": type(exc).__name__})
            raise AuthAPIError("webhook_invalid", "Invalid webhook signature") from exc

        event_id = headers["svix-id"] or data.get("id") or ""
        event_type = data.get("type", "")
        payload_hash = hashlib.sha256(
            json.dumps(data, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        obj, created = ProviderEvent.objects.get_or_create(
            provider="clerk",
            external_event_id=event_id,
            defaults={
                "event_type": event_type,
                "payload": data,
                "payload_hash": payload_hash,
                "status": ProviderEvent.Status.RECEIVED,
            },
        )
        security = SecurityService()
        if not created:
            security.record(
                user=None,
                event_type=security.EVENT_WEBHOOK_DUPLICATE,
                request=request,
                metadata={"external_event_id": event_id},
            )
            obj.status = ProviderEvent.Status.DUPLICATE
            obj.save(update_fields=["status"])
            return envelope_success(request, {"accepted": True, "duplicate": True})

        security.record(
            user=None,
            event_type=security.EVENT_WEBHOOK_RECEIVED,
            request=request,
            metadata={"external_event_id": event_id, "event_type": event_type},
        )
        if obj.processed_at is None:
            process_clerk_event.delay(obj.id)
        return envelope_success(request, {"accepted": True, "duplicate": False})
