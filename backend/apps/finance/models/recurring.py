from django.db import models

from apps.authentication.ids import new_uuid


class RecurringSchedule(models.Model):
    class Kind(models.TextChoices):
        INVOICE = "invoice"
        BILL = "bill"
        EXPENSE = "expense"

    class Status(models.TextChoices):
        ACTIVE = "active"
        PAUSED = "paused"

    class Frequency(models.TextChoices):
        MONTHLY = "monthly"
        WEEKLY = "weekly"
        YEARLY = "yearly"

    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    kind = models.CharField(max_length=16, choices=Kind.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    frequency = models.CharField(max_length=16, choices=Frequency.choices, default=Frequency.MONTHLY)
    contact = models.ForeignKey("finance.Contact", on_delete=models.PROTECT)
    currency = models.ForeignKey("finance.Currency", on_delete=models.PROTECT)
    bank_account = models.ForeignKey(
        "finance.Account", null=True, blank=True, on_delete=models.PROTECT
    )
    day_of_month = models.PositiveSmallIntegerField(null=True, blank=True)
    weekday = models.PositiveSmallIntegerField(null=True, blank=True)
    month_of_year = models.PositiveSmallIntegerField(null=True, blank=True)
    start_on = models.DateField()
    next_on = models.DateField()
    end_on = models.DateField(null=True, blank=True)
    fx_rate = models.DecimalField(max_digits=20, decimal_places=8, default=1)
    auto_post = models.BooleanField(default=False)
    lines = models.JSONField(default=list)
    created_by = models.CharField(max_length=36, blank=True, default="")

    class Meta:
        db_table = "finance_recurring_schedule"


class RecurringOccurrence(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    schedule = models.ForeignKey(RecurringSchedule, on_delete=models.CASCADE, related_name="occurrences")
    occurs_on = models.DateField()
    invoice = models.ForeignKey("finance.Invoice", null=True, blank=True, on_delete=models.SET_NULL)
    bill = models.ForeignKey("finance.Bill", null=True, blank=True, on_delete=models.SET_NULL)
    expense = models.ForeignKey("finance.PaidExpense", null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = "finance_recurring_occurrence"
        constraints = [
            models.UniqueConstraint(fields=["schedule", "occurs_on"], name="uniq_finance_recurring_occurrence")
        ]


class ReminderRule(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    document_kind = models.CharField(max_length=16)
    days_before_due = models.IntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "finance_reminder_rule"


class Reminder(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    rule = models.ForeignKey(ReminderRule, on_delete=models.CASCADE, related_name="reminders")
    object_type = models.CharField(max_length=16)
    object_id = models.CharField(max_length=36)
    due_date = models.DateField()
    as_of = models.DateField()
    emailed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "finance_reminder"
        constraints = [
            models.UniqueConstraint(fields=["rule", "object_id", "due_date"], name="uniq_finance_reminder")
        ]
