from datetime import date, timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.authentication.exceptions import AuthAPIError
from apps.finance.models import Bill, Invoice, Reminder, ReminderRule
from apps.finance.services.context import finance_tx
from apps.finance.services.purchases import outstanding as bill_outstanding
from apps.finance.services.sales import outstanding as invoice_outstanding
from apps.finance.services.workflow import record_exception


def create_rule(*, user_id, org, payload) -> ReminderRule:
    kind = payload.get("document_kind")
    if kind not in ("invoice", "bill"):
        raise AuthAPIError("validation_error", "document_kind must be invoice or bill")
    with finance_tx(user_id=user_id, organization_id=org.id):
        return ReminderRule.objects.create(
            organization=org,
            document_kind=kind,
            days_before_due=int(payload.get("days_before_due") or 0),
        )


def _deliver(user_id, reminder: Reminder):
    with finance_tx(user_id=user_id, organization_id=reminder.organization_id):
        rem = Reminder.objects.select_for_update().select_related().filter(pk=reminder.pk).first()
        if not rem or rem.emailed_at:
            return rem
        if rem.object_type == "invoice":
            doc = Invoice.objects.select_related("contact").filter(pk=rem.object_id).first()
        else:
            doc = Bill.objects.select_related("contact").filter(pk=rem.object_id).first()
        email = ((doc.contact.email if doc else "") or "").strip()
        if not email:
            record_exception(
                org=rem.organization,
                kind="reminder_no_email",
                reason="Contact has no email",
                object_type=rem.object_type,
                object_id=rem.object_id,
            )
            return rem
        try:
            send_mail(
                subject=f"Payment reminder: {doc.number or rem.object_id}",
                message=f"A {rem.object_type} is due {rem.due_date.isoformat()}.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
        except Exception as exc:
            record_exception(
                org=rem.organization,
                kind="reminder_send_failed",
                reason=str(exc)[:500],
                object_type=rem.object_type,
                object_id=rem.object_id,
            )
            return rem
        rem.emailed_at = timezone.now()
        rem.save(update_fields=["emailed_at"])
        return rem


def run_reminders(*, user_id, org, as_of: date):
    created = []
    with finance_tx(user_id=user_id, organization_id=org.id):
        for rule in ReminderRule.objects.filter(organization=org, active=True):
            if rule.document_kind == "invoice":
                docs = Invoice.objects.filter(organization=org, status=Invoice.Status.POSTED)
                amount = invoice_outstanding
                object_type = "invoice"
            else:
                docs = Bill.objects.filter(organization=org, status=Bill.Status.POSTED)
                amount = bill_outstanding
                object_type = "bill"
            for doc in docs:
                if amount(doc, as_of=as_of) <= 0:
                    continue
                if doc.due_date - timedelta(days=rule.days_before_due) != as_of:
                    continue
                try:
                    with transaction.atomic():
                        created.append(
                            Reminder.objects.create(
                                organization=org,
                                rule=rule,
                                object_type=object_type,
                                object_id=doc.id,
                                due_date=doc.due_date,
                                as_of=as_of,
                            )
                        )
                except IntegrityError:
                    continue
    return [_deliver(user_id, rem) or rem for rem in created]
