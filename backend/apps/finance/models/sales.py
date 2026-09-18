from django.db import models
from django.db.models import Q

from apps.authentication.ids import new_uuid


class Contact(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    name = models.CharField(max_length=255)
    is_customer = models.BooleanField(default=True)
    is_vendor = models.BooleanField(default=False)
    email = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(max_length=16, default="active")
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "finance_contact"


class PaymentTerm(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    name = models.CharField(max_length=100)
    days = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "finance_payment_term"


class TaxRate(models.Model):
    class Method(models.TextChoices):
        EXCLUSIVE = "exclusive"
        INCLUSIVE = "inclusive"

    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    name = models.CharField(max_length=100)
    rate = models.DecimalField(max_digits=10, decimal_places=6)
    method = models.CharField(max_length=16, choices=Method.choices, default=Method.EXCLUSIVE)
    payable_account = models.ForeignKey("finance.Account", on_delete=models.PROTECT)
    valid_from = models.DateField()
    status = models.CharField(max_length=16, default="active")

    class Meta:
        db_table = "finance_tax_rate"


class ExchangeRate(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    currency = models.ForeignKey("finance.Currency", on_delete=models.PROTECT)
    rate = models.DecimalField(max_digits=20, decimal_places=8)
    as_of = models.DateField()

    class Meta:
        db_table = "finance_exchange_rate"
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "currency", "as_of"], name="uniq_finance_fx_rate"
            )
        ]


class Item(models.Model):
    class Kind(models.TextChoices):
        SERVICE = "service"
        GOOD = "good"

    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    sku = models.CharField(max_length=64)
    name = models.CharField(max_length=255)
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.SERVICE)
    unit_price = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    income_account = models.ForeignKey("finance.Account", on_delete=models.PROTECT)
    expense_account = models.ForeignKey(
        "finance.Account", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    default_tax = models.ForeignKey(TaxRate, null=True, blank=True, on_delete=models.SET_NULL)
    tracked = models.BooleanField(default=False)
    status = models.CharField(max_length=16, default="active")
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "finance_item"
        constraints = [models.UniqueConstraint(fields=["organization", "sku"], name="uniq_finance_item_sku")]


class Quote(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft"
        CONVERTED = "converted"

    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    contact = models.ForeignKey(Contact, on_delete=models.PROTECT)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    entry_date = models.DateField()
    currency = models.ForeignKey("finance.Currency", on_delete=models.PROTECT)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "finance_quote"


class QuoteLine(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name="lines")
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    item = models.ForeignKey(Item, on_delete=models.PROTECT)
    description = models.CharField(max_length=255, blank=True, default="")
    quantity = models.DecimalField(max_digits=20, decimal_places=8, default=1)
    unit_price = models.DecimalField(max_digits=20, decimal_places=8)
    tax_rate = models.ForeignKey(TaxRate, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = "finance_quote_line"


class Invoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft"
        PENDING = "pending"
        APPROVED = "approved"
        POSTED = "posted"

    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    contact = models.ForeignKey(Contact, on_delete=models.PROTECT)
    quote = models.ForeignKey(Quote, null=True, blank=True, on_delete=models.SET_NULL)
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
    created_by = models.CharField(max_length=36, blank=True, default="")
    approved_by = models.CharField(max_length=36, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "finance_invoice"


class InvoiceLine(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="lines")
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    item = models.ForeignKey(Item, on_delete=models.PROTECT)
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
    income_account = models.ForeignKey("finance.Account", on_delete=models.PROTECT)

    class Meta:
        db_table = "finance_invoice_line"


class CreditNote(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft"
        POSTED = "posted"

    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    contact = models.ForeignKey(Contact, on_delete=models.PROTECT)
    invoice = models.ForeignKey(Invoice, null=True, blank=True, on_delete=models.PROTECT)
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
        db_table = "finance_credit_note"


class CreditNoteLine(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    credit_note = models.ForeignKey(CreditNote, on_delete=models.CASCADE, related_name="lines")
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    invoice_line = models.ForeignKey(
        InvoiceLine, null=True, blank=True, on_delete=models.PROTECT, related_name="credit_lines"
    )
    item = models.ForeignKey(Item, null=True, blank=True, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    price_only = models.BooleanField(default=False)
    description = models.CharField(max_length=255, blank=True, default="")
    income_account = models.ForeignKey("finance.Account", on_delete=models.PROTECT)
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
        db_table = "finance_credit_note_line"


class CustomerPayment(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft"
        POSTED = "posted"

    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    contact = models.ForeignKey(Contact, on_delete=models.PROTECT)
    bank_account = models.ForeignKey("finance.Account", on_delete=models.PROTECT)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    entry_date = models.DateField()
    currency = models.ForeignKey("finance.Currency", on_delete=models.PROTECT)
    fx_rate = models.DecimalField(max_digits=20, decimal_places=8, default=1)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    journal = models.ForeignKey("finance.JournalEntry", null=True, blank=True, on_delete=models.PROTECT)

    class Meta:
        db_table = "finance_customer_payment"


class Allocation(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="allocations")
    payment = models.ForeignKey(
        CustomerPayment, null=True, blank=True, on_delete=models.PROTECT, related_name="allocations"
    )
    credit_note = models.ForeignKey(
        CreditNote, null=True, blank=True, on_delete=models.PROTECT, related_name="allocations"
    )
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    base_amount = models.DecimalField(max_digits=20, decimal_places=8)
    entry_date = models.DateField()

    class Meta:
        db_table = "finance_allocation"
        constraints = [
            models.UniqueConstraint(
                fields=["payment", "invoice"],
                condition=Q(payment__isnull=False),
                name="uniq_finance_allocation_payment_invoice",
            )
        ]


class CustomerRefund(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    payment = models.ForeignKey(CustomerPayment, null=True, blank=True, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    entry_date = models.DateField()
    bank_account = models.ForeignKey("finance.Account", on_delete=models.PROTECT)
    journal = models.ForeignKey("finance.JournalEntry", on_delete=models.PROTECT)

    class Meta:
        db_table = "finance_customer_refund"
