import hashlib
import hmac
import json
from datetime import timedelta

from django.utils import timezone

from apps.authentication.exceptions import AuthAPIError
from apps.authentication.ids import new_uuid
from apps.finance.models import FinanceWebhookDelivery, FinanceWebhookEndpoint

MAX_ATTEMPTS = 3


def sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def create_endpoint(*, org, url, events, secret=""):
    url = (url or "").strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        raise AuthAPIError("validation_error", "Webhook URL must be http(s)")
    import secrets

    secret = secret or secrets.token_hex(16)
    return FinanceWebhookEndpoint.objects.create(
        organization=org, url=url, secret=secret, events=list(events or []), enabled=True
    )


def enqueue_journal(*, org, journal):
    endpoints = FinanceWebhookEndpoint.objects.filter(organization=org, enabled=True)
    if not endpoints:
        return
    event_type = f"{journal.source_type}.posted"
    payload = {"event": event_type, "journal_id": journal.id, "source_type": journal.source_type, "number": journal.number}
    now = timezone.now()
    for ep in endpoints:
        wanted = ep.events or []
        if wanted and event_type not in wanted and "journal.posted" not in wanted:
            continue
        FinanceWebhookDelivery.objects.create(
            organization=org,
            endpoint=ep,
            event_id=new_uuid(),
            event_type=event_type,
            payload=payload,
            next_attempt=now,
        )


def deliver_due(*, org, now=None):
    now = now or timezone.now()
    import httpx

    sent = []
    qs = FinanceWebhookDelivery.objects.select_related("endpoint").filter(
        organization=org, status=FinanceWebhookDelivery.Status.PENDING, next_attempt__lte=now
    )
    for row in qs:
        body = json.dumps(row.payload, sort_keys=True).encode()
        headers = {
            "Content-Type": "application/json",
            "X-Finance-Signature": sign(row.endpoint.secret, body),
            "X-Finance-Event-Id": row.event_id,
            "X-Finance-Event": row.event_type,
        }
        try:
            resp = httpx.post(row.endpoint.url, content=body, headers=headers, timeout=10)
            ok = 200 <= resp.status_code < 300
            err = "" if ok else f"http {resp.status_code}"
        except Exception as exc:
            ok, err = False, str(exc)[:255]
        row.attempts += 1
        if ok:
            row.status = FinanceWebhookDelivery.Status.DELIVERED
            row.last_error = ""
        elif row.attempts >= MAX_ATTEMPTS:
            row.status = FinanceWebhookDelivery.Status.DEAD
            row.last_error = err
        else:
            row.next_attempt = now + timedelta(minutes=2**row.attempts)
            row.last_error = err
        row.save(update_fields=["attempts", "status", "next_attempt", "last_error"])
        sent.append({"id": row.id, "status": row.status})
    return sent
