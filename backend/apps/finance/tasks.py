from celery import shared_task
from django.utils import timezone

from apps.finance.models import RecurringSchedule, ReminderRule
from apps.finance.services.recurring import run_due
from apps.finance.services.reminders import run_reminders
from apps.tenancy.models import Organization


@shared_task
def run_due_recurring():
    today = timezone.now().date()
    org_ids = (
        RecurringSchedule.objects.filter(status=RecurringSchedule.Status.ACTIVE, next_on__lte=today)
        .values_list("organization_id", "created_by")
        .distinct()
    )
    for org_id, user_id in org_ids:
        if not user_id:
            continue
        org = Organization.objects.filter(pk=org_id).first()
        if org:
            run_due(user_id=user_id, org=org, as_of=today)


@shared_task
def run_due_reminders():
    today = timezone.now().date()
    for org_id in ReminderRule.objects.filter(active=True).values_list("organization_id", flat=True).distinct():
        org = Organization.objects.filter(pk=org_id).first()
        if not org:
            continue
        sched = RecurringSchedule.objects.filter(organization_id=org_id).first()
        user_id = sched.created_by if sched else org.id
        run_reminders(user_id=user_id, org=org, as_of=today)
