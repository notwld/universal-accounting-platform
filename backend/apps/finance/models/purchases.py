from django.db import models

from apps.authentication.ids import new_uuid


class Bill(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft"
        PENDING = "pending"
        APPROVED = "approved"
        POSTED = "posted"

    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    contact = models.ForeignKey("finance.Contact", on_delete=models.PROTECT)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    number = models.CharField(max_length=32, blank=True, default="")
    entry_date = models.DateField()
    due_date = models.DateField()
    currency = models.ForeignKey("finance.Currency", on_delete=models.PROTECT)
    fx_rate = models.DecimalField(max_digits=20, decimal_places=8, default=1)
    contact_name = models.CharField(max_length=255, blank=True, default="")
    total = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    base_total = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    version = models.PositiveIntegerField(default=1)
    journal = models.ForeignKey("finance.JournalEntry", null=True, blank=True, on_delete=models.PROTECT)
    purchase_order = models.ForeignKey(
        "finance.PurchaseOrder", null=True, blank=True, on_delete=models.SET_NULL
    )
    created_by = models.CharField(max_length=36, blank=True, default="")
    approved_by = models.CharField(max_length=36, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "finance_bill"


class BillLine(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name="lines")
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    item = models.ForeignKey("finance.Item", on_delete=models.PROTECT)
    description = models.CharField(max_length=255, blank=True, default="")
    quantity = models.DecimalField(max_digits=20, decimal_places=8)
    unit_price = models.DecimalField(max_digits=20, decimal_places=8)
    tax_rate_id_snap = models.CharField(max_length=36, blank=True, default="")
    tax_rate_value = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    tax_method = models.CharField(max_length=16, default="exclusive")
    tax_name = models.CharField(max_length=100, blank=True, default="")
    net = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    tax_amount = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    total = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    base_net = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    base_tax = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    base_total = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    expense_account = models.ForeignKey("finance.Account", on_delete=models.PROTECT)

    class Meta:
        db_table = "finance_bill_line"


class VendorCredit(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft"
        POSTED = "posted"

    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    contact = models.ForeignKey("finance.Contact", on_delete=models.PROTECT)
    bill = models.ForeignKey(Bill, null=True, blank=True, on_delete=models.PROTECT)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    number = models.CharField(max_length=32, blank=True, default="")
    entry_date = models.DateField()
    currency = models.ForeignKey("finance.Currency", on_delete=models.PROTECT)
    fx_rate = models.DecimalField(max_digits=20, decimal_places=8, default=1)
    total = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    base_total = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    journal = models.ForeignKey("finance.JournalEntry", null=True, blank=True, on_delete=models.PROTECT)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "finance_vendor_credit"


class VendorCreditLine(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    credit = models.ForeignKey(VendorCredit, on_delete=models.CASCADE, related_name="lines")
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    description = models.CharField(max_length=255, blank=True, default="")
    expense_account = models.ForeignKey("finance.Account", on_delete=models.PROTECT)
    net = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    tax_amount = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    total = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    base_net = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    base_tax = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    base_total = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    tax_payable_account = models.ForeignKey(
        "finance.Account", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )

    class Meta:
        db_table = "finance_vendor_credit_line"


class VendorPayment(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft"
        POSTED = "posted"

    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    contact = models.ForeignKey("finance.Contact", on_delete=models.PROTECT)
    bank_account = models.ForeignKey("finance.Account", on_delete=models.PROTECT)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    entry_date = models.DateField()
    currency = models.ForeignKey("finance.Currency", on_delete=models.PROTECT)
    fx_rate = models.DecimalField(max_digits=20, decimal_places=8, default=1)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    journal = models.ForeignKey("finance.JournalEntry", null=True, blank=True, on_delete=models.PROTECT)

    class Meta:
        db_table = "finance_vendor_payment"


class BillAllocation(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    bill = models.ForeignKey(Bill, on_delete=models.PROTECT, related_name="allocations")
    payment = models.ForeignKey(
        VendorPayment, null=True, blank=True, on_delete=models.PROTECT, related_name="allocations"
    )
    credit = models.ForeignKey(
        VendorCredit, null=True, blank=True, on_delete=models.PROTECT, related_name="allocations"
    )
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    base_amount = models.DecimalField(max_digits=20, decimal_places=8)
    entry_date = models.DateField()

    class Meta:
        db_table = "finance_bill_allocation"


class VendorRefund(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    payment = models.ForeignKey(VendorPayment, null=True, blank=True, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    entry_date = models.DateField()
    bank_account = models.ForeignKey("finance.Account", on_delete=models.PROTECT, related_name="+")
    journal = models.ForeignKey("finance.JournalEntry", on_delete=models.PROTECT)

    class Meta:
        db_table = "finance_vendor_refund"


class PaidExpense(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    contact = models.ForeignKey("finance.Contact", null=True, blank=True, on_delete=models.PROTECT)
    bank_account = models.ForeignKey("finance.Account", on_delete=models.PROTECT)
    number = models.CharField(max_length=32, blank=True, default="")
    entry_date = models.DateField()
    currency = models.ForeignKey("finance.Currency", on_delete=models.PROTECT)
    fx_rate = models.DecimalField(max_digits=20, decimal_places=8, default=1)
    total = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    base_total = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    journal = models.ForeignKey("finance.JournalEntry", on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "finance_paid_expense"


class PaidExpenseLine(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    expense = models.ForeignKey(PaidExpense, on_delete=models.CASCADE, related_name="lines")
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    description = models.CharField(max_length=255, blank=True, default="")
    expense_account = models.ForeignKey("finance.Account", on_delete=models.PROTECT)
    net = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    tax_amount = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    total = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    base_net = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    base_tax = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    base_total = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    tax_payable_account = models.ForeignKey(
        "finance.Account", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )

    class Meta:
        db_table = "finance_paid_expense_line"


class PurchaseOrder(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft"
        CONVERTED = "converted"

    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    contact = models.ForeignKey("finance.Contact", on_delete=models.PROTECT)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    entry_date = models.DateField()
    currency = models.ForeignKey("finance.Currency", on_delete=models.PROTECT)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "finance_purchase_order"


class PurchaseOrderLine(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="lines")
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    item = models.ForeignKey("finance.Item", on_delete=models.PROTECT)
    description = models.CharField(max_length=255, blank=True, default="")
    quantity = models.DecimalField(max_digits=20, decimal_places=8, default=1)
    unit_price = models.DecimalField(max_digits=20, decimal_places=8)
    tax_rate = models.ForeignKey("finance.TaxRate", null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = "finance_purchase_order_line"


class PaymentRun(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft"
        POSTED = "posted"

    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    bank_account = models.ForeignKey("finance.Account", on_delete=models.PROTECT)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    entry_date = models.DateField()
    currency = models.ForeignKey("finance.Currency", on_delete=models.PROTECT)
    number = models.CharField(max_length=32, blank=True, default="")
    idempotency_key = models.CharField(max_length=64)

    class Meta:
        db_table = "finance_payment_run"
        constraints = [
            models.UniqueConstraint(fields=["organization", "idempotency_key"], name="uniq_finance_payment_run_key")
        ]


class PaymentRunLine(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    payment_run = models.ForeignKey(PaymentRun, on_delete=models.CASCADE, related_name="lines")
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    bill = models.ForeignKey(Bill, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    payment = models.ForeignKey(VendorPayment, null=True, blank=True, on_delete=models.PROTECT)

    class Meta:
        db_table = "finance_payment_run_line"
