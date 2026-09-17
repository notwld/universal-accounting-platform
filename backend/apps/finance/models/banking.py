from django.db import models
from django.db.models import Q

from apps.authentication.ids import new_uuid


class BankStatement(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    account = models.ForeignKey("finance.Account", on_delete=models.PROTECT)
    original_name = models.CharField(max_length=255, blank=True, default="")
    imported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "finance_bank_statement"


class BankLine(models.Model):
    class Status(models.TextChoices):
        IMPORTED = "imported"
        MATCHED = "matched"
        CATEGORIZED = "categorized"

    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    statement = models.ForeignKey(BankStatement, on_delete=models.CASCADE, related_name="lines")
    account = models.ForeignKey("finance.Account", on_delete=models.PROTECT)
    entry_date = models.DateField()
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    description = models.CharField(max_length=255, blank=True, default="")
    fingerprint = models.CharField(max_length=64)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.IMPORTED)
    customer_payment = models.ForeignKey(
        "finance.CustomerPayment", null=True, blank=True, on_delete=models.PROTECT
    )
    vendor_payment = models.ForeignKey(
        "finance.VendorPayment", null=True, blank=True, on_delete=models.PROTECT
    )
    journal = models.ForeignKey("finance.JournalEntry", null=True, blank=True, on_delete=models.PROTECT)

    class Meta:
        db_table = "finance_bank_line"
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "account", "fingerprint"],
                name="uniq_finance_bank_line_fingerprint",
            ),
            models.UniqueConstraint(
                fields=["customer_payment"],
                condition=Q(customer_payment__isnull=False),
                name="uniq_finance_bank_line_customer_payment",
            ),
            models.UniqueConstraint(
                fields=["vendor_payment"],
                condition=Q(vendor_payment__isnull=False),
                name="uniq_finance_bank_line_vendor_payment",
            ),
        ]


class BankReconciliation(models.Model):
    class Status(models.TextChoices):
        OPEN = "open"
        COMPLETE = "complete"

    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    account = models.ForeignKey("finance.Account", on_delete=models.PROTECT)
    start_on = models.DateField()
    end_on = models.DateField()
    opening = models.DecimalField(max_digits=20, decimal_places=8)
    closing = models.DecimalField(max_digits=20, decimal_places=8)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    reopen_reason = models.TextField(blank=True, default="")

    class Meta:
        db_table = "finance_bank_reconciliation"


class BankRule(models.Model):
    class Direction(models.TextChoices):
        ANY = "any"
        INFLOW = "inflow"
        OUTFLOW = "outflow"

    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    class MatchKind(models.TextChoices):
        CONTAINS = "contains"
        REGEX = "regex"

    pattern = models.CharField(max_length=255)
    match_kind = models.CharField(max_length=16, choices=MatchKind.choices, default=MatchKind.CONTAINS)
    amount_min = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    amount_max = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    account = models.ForeignKey("finance.Account", on_delete=models.PROTECT)
    direction = models.CharField(max_length=16, choices=Direction.choices, default=Direction.ANY)
    priority = models.IntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "finance_bank_rule"


class BankFeed(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    account = models.ForeignKey("finance.Account", on_delete=models.PROTECT)
    url = models.CharField(max_length=500)
    active = models.BooleanField(default=True)
    last_fetched_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True, default="")

    class Meta:
        db_table = "finance_bank_feed"
