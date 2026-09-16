from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from apps.authentication.crypto import decrypt_field
from apps.authentication.models import AuthUser, SecurityEvent


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_security_email(self, user_id: str, event_type: str, event_id: str):
    """Transactional SMTP for security notifications only (not Clerk OTP/verification)."""
    user = AuthUser.objects.filter(id=user_id).first()
    if not user:
        return
    to_email = decrypt_field(user.primary_email_ciphertext)
    if not to_email:
        return
    event = SecurityEvent.objects.filter(id=event_id).first()
    subject = f"[Security] {event_type}"
    body = (
        f"A security event was recorded on your Universal Accounting account.\n\n"
        f"Type: {event_type}\n"
        f"Event ID: {event_id}\n"
        f"Time: {event.created_at.isoformat() if event else 'n/a'}\n\n"
        f"If this wasn't you, review your sessions at {settings.FRONTEND_URL}/account/sessions\n"
    )
    send_mail(
        subject=subject,
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[to_email],
        fail_silently=False,
    )
