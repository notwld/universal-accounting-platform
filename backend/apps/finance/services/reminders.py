from datetime import date, timedelta

from django.db import IntegrityError, transaction

from apps.authentication.exceptions import AuthAPIError
from apps.finance.models import Bill, Invoice, Reminder, ReminderRule
from apps.finance.services.context import finance_tx
from apps.finance.services.purchases import outstanding as bill_outstanding
from apps.finance.services.sales import outstanding as invoice_outstanding


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
    return created
