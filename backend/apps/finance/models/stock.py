from django.db import models

from apps.authentication.ids import new_uuid


class Warehouse(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    name = models.CharField(max_length=100)

    class Meta:
        db_table = "finance_warehouse"
        constraints = [
            models.UniqueConstraint(fields=["organization", "name"], name="uniq_finance_warehouse_name")
        ]


class StockBalance(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    item = models.ForeignKey("finance.Item", on_delete=models.PROTECT)
    qty = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    value = models.DecimalField(max_digits=20, decimal_places=8, default=0)

    class Meta:
        db_table = "finance_stock_balance"
        constraints = [
            models.UniqueConstraint(fields=["warehouse", "item"], name="uniq_finance_stock_balance")
        ]


class StockMove(models.Model):
    class Kind(models.TextChoices):
        RECEIVE = "receive"
        ISSUE = "issue"
        ADJUST = "adjust"
        TRANSFER = "transfer"

    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    item = models.ForeignKey("finance.Item", on_delete=models.PROTECT)
    kind = models.CharField(max_length=16, choices=Kind.choices)
    qty = models.DecimalField(max_digits=20, decimal_places=8)
    unit_cost = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    value = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    source_type = models.CharField(max_length=16, blank=True, default="")
    source_id = models.CharField(max_length=36, blank=True, default="")
    entry_date = models.DateField()

    class Meta:
        db_table = "finance_stock_move"
