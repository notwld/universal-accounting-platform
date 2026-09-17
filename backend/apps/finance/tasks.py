from celery import shared_task
from django.utils import timezone

from apps.finance.models import BankFeed, RecurringSchedule, ReminderRule
from apps.finance.services.banking import fetch_bank_feed
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


@shared_task
def run_due_feeds():
    for feed in BankFeed.objects.filter(active=True).select_related("organization"):
        user_id = (
            RecurringSchedule.objects.filter(organization_id=feed.organization_id)
            .values_list("created_by", flat=True)
            .first()
            or feed.organization_id
        )
        try:
            fetch_bank_feed(user_id=user_id, org=feed.organization, feed_id=feed.id)
        except Exception:
            continue
