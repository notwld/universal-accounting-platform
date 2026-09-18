from django.db import models
from django.db.models import Q

from apps.authentication.ids import new_uuid


class JournalEntry(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft"
        POSTED = "posted"

    class Source(models.TextChoices):
        MANUAL = "manual"
        OPENING = "opening"
        INVOICE = "invoice"
        PAYMENT = "payment"
        CREDIT = "credit"
        REFUND = "refund"
        BILL = "bill"
        EXPENSE = "expense"
        VENDOR_PAYMENT = "vendor_payment"
        VENDOR_CREDIT = "vendor_credit"
        VENDOR_REFUND = "vendor_refund"
        BANK = "bank"
        STOCK = "stock"
        ASSET = "asset"
        CLOSE = "close"
        FX_REVAL = "fx_reval"
        ADJUST = "adjust"

    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.PROTECT, related_name="journals"
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    entry_date = models.DateField()
    number = models.CharField(max_length=32, blank=True, default="")
    memo = models.TextField(blank=True, default="")
    source_type = models.CharField(max_length=16, choices=Source.choices, default=Source.MANUAL)
    version = models.PositiveIntegerField(default=1)
    posted_at = models.DateTimeField(null=True, blank=True)
    posted_by = models.CharField(max_length=36, blank=True, default="")
    reverses = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="reversal_of"
    )
    reversed_by = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="reversal_source"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "finance_journal"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            prev = JournalEntry.objects.filter(pk=self.pk).values("status").first()
            if prev and prev["status"] == self.Status.POSTED:
                update_fields = set(kwargs.get("update_fields") or [])
                if update_fields and update_fields <= {"reversed_by", "updated_at"}:
                    super().save(*args, **kwargs)
                    return
                raise PermissionError("posted journal is immutable")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.status == self.Status.POSTED:
            raise PermissionError("posted journal is immutable")
        super().delete(*args, **kwargs)


class JournalLine(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    journal = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name="lines")
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    account = models.ForeignKey("finance.Account", on_delete=models.PROTECT)
    description = models.CharField(max_length=255, blank=True, default="")
    tag = models.ForeignKey("finance.ReportingTag", null=True, blank=True, on_delete=models.SET_NULL)
    debit = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    credit = models.DecimalField(max_digits=20, decimal_places=8, default=0)

    class Meta:
        db_table = "finance_journal_line"
        constraints = [
            models.CheckConstraint(
                condition=(Q(debit__gt=0, credit=0) | Q(credit__gt=0, debit=0)),
                name="journal_line_debit_xor_credit",
            )
        ]

    def save(self, *args, **kwargs):
        if self.journal_id and JournalEntry.objects.filter(
            pk=self.journal_id, status=JournalEntry.Status.POSTED
        ).exists():
            raise PermissionError("posted journal is immutable")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.journal.status == JournalEntry.Status.POSTED:
            raise PermissionError("posted journal is immutable")
        super().delete(*args, **kwargs)


class FinanceIdempotency(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.CASCADE)
    operation = models.CharField(max_length=64)
    key = models.CharField(max_length=128)
    request_hash = models.CharField(max_length=64)
    journal = models.ForeignKey(JournalEntry, null=True, blank=True, on_delete=models.SET_NULL)
    resource_type = models.CharField(max_length=32, blank=True, default="")
    resource_id = models.CharField(max_length=36, blank=True, default="")
    status = models.CharField(max_length=24, default="in_progress")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "finance_idempotency"
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "operation", "key"],
                name="uniq_finance_idempotency",
            )
        ]


class FinanceAuditEvent(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.CASCADE)
    actor_user_id = models.CharField(max_length=36)
    action = models.CharField(max_length=64)
    object_type = models.CharField(max_length=32)
    object_id = models.CharField(max_length=36, blank=True, default="")
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "finance_audit_event"
