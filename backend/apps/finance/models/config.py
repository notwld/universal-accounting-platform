from django.db import models

from apps.authentication.ids import new_uuid


ISO_CURRENCIES = (
    ("USD", 2, "US Dollar"),
    ("EUR", 2, "Euro"),
    ("GBP", 2, "Pound Sterling"),
    ("JPY", 0, "Yen"),
    ("KWD", 3, "Kuwaiti Dinar"),
    ("BHD", 3, "Bahraini Dinar"),
    ("CLP", 0, "Chilean Peso"),
    ("AUD", 2, "Australian Dollar"),
    ("CAD", 2, "Canadian Dollar"),
    ("CHF", 2, "Swiss Franc"),
    ("INR", 2, "Indian Rupee"),
    ("SGD", 2, "Singapore Dollar"),
    ("ZAR", 2, "Rand"),
    ("SEK", 2, "Swedish Krona"),
    ("NOK", 2, "Norwegian Krone"),
    ("DKK", 2, "Danish Krone"),
    ("CNY", 2, "Yuan Renminbi"),
    ("HKD", 2, "Hong Kong Dollar"),
    ("NZD", 2, "New Zealand Dollar"),
    ("MXN", 2, "Mexican Peso"),
)


class Currency(models.Model):
    code = models.CharField(max_length=3, primary_key=True)
    exponent = models.PositiveSmallIntegerField()
    name = models.CharField(max_length=64)

    class Meta:
        db_table = "finance_currency"


class FinanceSettings(models.Model):
    organization = models.OneToOneField(
        "tenancy.Organization",
        on_delete=models.PROTECT,
        primary_key=True,
        related_name="finance_settings",
    )
    country_code = models.CharField(max_length=2)
    base_currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    fiscal_year_start_month = models.PositiveSmallIntegerField()
    timezone = models.CharField(max_length=64)
    locale = models.CharField(max_length=32, default="en")
    tax_registration_applies = models.BooleanField(default=False)
    setup_completed_at = models.DateTimeField()
    ar_account = models.ForeignKey(
        "finance.Account", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    advance_account = models.ForeignKey(
        "finance.Account", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    fx_gain_account = models.ForeignKey(
        "finance.Account", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    fx_loss_account = models.ForeignKey(
        "finance.Account", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    ap_account = models.ForeignKey(
        "finance.Account", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    vendor_advance_account = models.ForeignKey(
        "finance.Account", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    inventory_account = models.ForeignKey(
        "finance.Account", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    cogs_account = models.ForeignKey(
        "finance.Account", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    require_document_approval = models.BooleanField(default=False)
    allow_self_approve = models.BooleanField(default=False)
    approval_threshold = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    approval_levels = models.PositiveSmallIntegerField(default=1)

    class Meta:
        db_table = "finance_settings"


class FinanceRole(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE, related_name="finance_roles"
    )
    slug = models.CharField(max_length=64)
    name = models.CharField(max_length=100)
    permissions = models.JSONField(default=list)
    is_preset = models.BooleanField(default=False)

    class Meta:
        db_table = "finance_role"
        constraints = [
            models.UniqueConstraint(fields=["organization", "slug"], name="uniq_finance_role_org_slug")
        ]


class FinanceGrant(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE, related_name="finance_grants"
    )
    user_id = models.CharField(max_length=36, db_index=True)
    role = models.ForeignKey(FinanceRole, on_delete=models.PROTECT, related_name="grants")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "finance_grant"
        constraints = [
            models.UniqueConstraint(fields=["organization", "user_id"], name="uniq_finance_grant_org_user")
        ]


class Account(models.Model):
    class Classification(models.TextChoices):
        ASSET = "asset"
        LIABILITY = "liability"
        EQUITY = "equity"
        INCOME = "income"
        EXPENSE = "expense"

    class Status(models.TextChoices):
        ACTIVE = "active"
        INACTIVE = "inactive"

    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.PROTECT, related_name="accounts"
    )
    code = models.CharField(max_length=32)
    name = models.CharField(max_length=255)
    classification = models.CharField(max_length=16, choices=Classification.choices)
    is_control = models.BooleanField(default=False)
    control_kind = models.CharField(max_length=8, blank=True, default="")
    cashflow_kind = models.CharField(max_length=16, blank=True, default="")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "finance_account"
        constraints = [
            models.UniqueConstraint(fields=["organization", "code"], name="uniq_finance_account_org_code")
        ]


class DocumentSequence(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.PROTECT, related_name="document_sequences"
    )
    document_type = models.CharField(max_length=32)
    series = models.CharField(max_length=32, default="default")
    prefix = models.CharField(max_length=16, blank=True, default="JE-")
    next_number = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "finance_document_sequence"
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "document_type", "series"],
                name="uniq_finance_sequence",
            )
        ]


class FiscalPeriodLock(models.Model):
    class Status(models.TextChoices):
        OPEN = "open"
        LOCKED = "locked"

    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.PROTECT, related_name="period_locks"
    )
    start_on = models.DateField()
    end_on = models.DateField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    locked_by = models.CharField(max_length=36, blank=True, default="")
    locked_at = models.DateTimeField(null=True, blank=True)
    reopen_reason = models.TextField(blank=True, default="")
    reopened_by = models.CharField(max_length=36, blank=True, default="")
    reopened_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "finance_period_lock"


class ReportingTag(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    name = models.CharField(max_length=100)

    class Meta:
        db_table = "finance_reporting_tag"
        constraints = [
            models.UniqueConstraint(fields=["organization", "name"], name="uniq_finance_reporting_tag")
        ]


class SavedFilter(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    name = models.CharField(max_length=100)
    resource = models.CharField(max_length=32)
    params = models.JSONField(default=dict)

    class Meta:
        db_table = "finance_saved_filter"
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "resource", "name"], name="uniq_finance_saved_filter"
            )
        ]


class FinanceException(models.Model):
    class Status(models.TextChoices):
        OPEN = "open"
        RESOLVED = "resolved"

    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    kind = models.CharField(max_length=64)
    object_type = models.CharField(max_length=32, blank=True, default="")
    object_id = models.CharField(max_length=36, blank=True, default="")
    reason = models.TextField(blank=True, default="")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "finance_exception"


class ApprovalAction(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    object_type = models.CharField(max_length=16)
    object_id = models.CharField(max_length=36)
    actor_user_id = models.CharField(max_length=36)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "finance_approval_action"
        constraints = [
            models.UniqueConstraint(
                fields=["object_type", "object_id", "actor_user_id"],
                name="uniq_finance_approval_action",
            )
        ]
