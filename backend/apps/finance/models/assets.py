from django.db import models

from apps.authentication.ids import new_uuid


class FixedAsset(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active"
        DISPOSED = "disposed"

    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    number = models.CharField(max_length=32)
    name = models.CharField(max_length=255)
    cost = models.DecimalField(max_digits=20, decimal_places=8)
    residual = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    life_months = models.PositiveIntegerField()
    in_service_date = models.DateField()
    accum = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    cost_account = models.ForeignKey("finance.Account", on_delete=models.PROTECT, related_name="+")
    accum_account = models.ForeignKey("finance.Account", on_delete=models.PROTECT, related_name="+")
    expense_account = models.ForeignKey("finance.Account", on_delete=models.PROTECT, related_name="+")
    journal = models.ForeignKey("finance.JournalEntry", null=True, blank=True, on_delete=models.PROTECT)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    disposed_on = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "finance_fixed_asset"
        constraints = [
            models.UniqueConstraint(fields=["organization", "number"], name="uniq_finance_fixed_asset_number")
        ]


class AssetCharge(models.Model):
    class Kind(models.TextChoices):
        DEPRECIATE = "depreciate"
        WRITE_DOWN = "write_down"

    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    asset = models.ForeignKey(FixedAsset, on_delete=models.PROTECT, related_name="charges")
    kind = models.CharField(max_length=16, choices=Kind.choices)
    period = models.DateField()
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    journal = models.ForeignKey("finance.JournalEntry", on_delete=models.PROTECT)

    class Meta:
        db_table = "finance_asset_charge"
        constraints = [
            models.UniqueConstraint(fields=["asset", "kind", "period"], name="uniq_finance_asset_charge")
        ]
