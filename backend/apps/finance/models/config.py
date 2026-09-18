from django.db import models

from apps.authentication.ids import new_uuid


# ISO 4217 current codes. Exponent overrides: 0 minor units, 3, 4; default 2.
_ISO_ZERO = "BIF CLP DJF GNF ISK JPY KMF KRW PYG RWF UGX VND VUV XAF XAG XAU XBA XBB XBC XBD XDR XOF XPD XPF XPT XSU XTS XUA XXX".split()
_ISO_THREE = "BHD IQD JOD KWD LYD OMR TND".split()
_ISO_FOUR = "CLF UYW".split()
_ISO_NAMES = {
    "AED": "UAE Dirham", "AFN": "Afghani", "ALL": "Lek", "AMD": "Armenian Dram", "ANG": "Netherlands Antillean Guilder",
    "AOA": "Kwanza", "ARS": "Argentine Peso", "AUD": "Australian Dollar", "AWG": "Aruban Florin", "AZN": "Azerbaijan Manat",
    "BAM": "Convertible Mark", "BBD": "Barbados Dollar", "BDT": "Taka", "BGN": "Bulgarian Lev", "BHD": "Bahraini Dinar",
    "BIF": "Burundi Franc", "BMD": "Bermudian Dollar", "BND": "Brunei Dollar", "BOB": "Boliviano", "BOV": "Mvdol",
    "BRL": "Brazilian Real", "BSD": "Bahamian Dollar", "BTN": "Ngultrum", "BWP": "Pula", "BYN": "Belarusian Ruble",
    "BZD": "Belize Dollar", "CAD": "Canadian Dollar", "CDF": "Congolese Franc", "CHE": "WIR Euro", "CHF": "Swiss Franc",
    "CHW": "WIR Franc", "CLF": "Unidad de Fomento", "CLP": "Chilean Peso", "CNY": "Yuan Renminbi", "COP": "Colombian Peso",
    "COU": "Unidad de Valor Real", "CRC": "Costa Rican Colon", "CUC": "Peso Convertible", "CUP": "Cuban Peso",
    "CVE": "Cabo Verde Escudo", "CZK": "Czech Koruna", "DJF": "Djibouti Franc", "DKK": "Danish Krone", "DOP": "Dominican Peso",
    "DZD": "Algerian Dinar", "EGP": "Egyptian Pound", "ERN": "Nakfa", "ETB": "Ethiopian Birr", "EUR": "Euro",
    "FJD": "Fiji Dollar", "FKP": "Falkland Islands Pound", "GBP": "Pound Sterling", "GEL": "Lari", "GHS": "Ghana Cedi",
    "GIP": "Gibraltar Pound", "GMD": "Dalasi", "GNF": "Guinean Franc", "GTQ": "Quetzal", "GYD": "Guyana Dollar",
    "HKD": "Hong Kong Dollar", "HNL": "Lempira", "HTG": "Gourde", "HUF": "Forint", "IDR": "Rupiah", "ILS": "New Israeli Sheqel",
    "INR": "Indian Rupee", "IQD": "Iraqi Dinar", "IRR": "Iranian Rial", "ISK": "Iceland Krona", "JMD": "Jamaican Dollar",
    "JOD": "Jordanian Dinar", "JPY": "Yen", "KES": "Kenyan Shilling", "KGS": "Som", "KHR": "Riel", "KMF": "Comorian Franc",
    "KPW": "North Korean Won", "KRW": "Won", "KWD": "Kuwaiti Dinar", "KYD": "Cayman Islands Dollar", "KZT": "Tenge",
    "LAK": "Lao Kip", "LBP": "Lebanese Pound", "LKR": "Sri Lanka Rupee", "LRD": "Liberian Dollar", "LSL": "Loti",
    "LYD": "Libyan Dinar", "MAD": "Moroccan Dirham", "MDL": "Moldovan Leu", "MGA": "Malagasy Ariary", "MKD": "Denar",
    "MMK": "Kyat", "MNT": "Tugrik", "MOP": "Pataca", "MRU": "Ouguiya", "MUR": "Mauritius Rupee", "MVR": "Rufiyaa",
    "MWK": "Malawi Kwacha", "MXN": "Mexican Peso", "MXV": "Mexican Unidad de Inversion", "MYR": "Malaysian Ringgit",
    "MZN": "Mozambique Metical", "NAD": "Namibia Dollar", "NGN": "Naira", "NIO": "Cordoba Oro", "NOK": "Norwegian Krone",
    "NPR": "Nepalese Rupee", "NZD": "New Zealand Dollar", "OMR": "Rial Omani", "PAB": "Balboa", "PEN": "Sol",
    "PGK": "Kina", "PHP": "Philippine Peso", "PKR": "Pakistan Rupee", "PLN": "Zloty", "PYG": "Guarani", "QAR": "Qatari Rial",
    "RON": "Romanian Leu", "RSD": "Serbian Dinar", "RUB": "Russian Ruble", "RWF": "Rwanda Franc", "SAR": "Saudi Riyal",
    "SBD": "Solomon Islands Dollar", "SCR": "Seychelles Rupee", "SDG": "Sudanese Pound", "SEK": "Swedish Krona",
    "SGD": "Singapore Dollar", "SHP": "Saint Helena Pound", "SLE": "Leone", "SOS": "Somali Shilling", "SRD": "Surinam Dollar",
    "SSP": "South Sudanese Pound", "STN": "Dobra", "SVC": "El Salvador Colon", "SYP": "Syrian Pound", "SZL": "Lilangeni",
    "THB": "Baht", "TJS": "Somoni", "TMT": "Turkmenistan New Manat", "TND": "Tunisian Dinar", "TOP": "Pa’anga",
    "TRY": "Turkish Lira", "TTD": "Trinidad and Tobago Dollar", "TWD": "New Taiwan Dollar", "TZS": "Tanzanian Shilling",
    "UAH": "Hryvnia", "UGX": "Uganda Shilling", "USD": "US Dollar", "USN": "US Dollar (Next day)", "UYI": "Uruguay Peso en Unidades Indexadas",
    "UYU": "Peso Uruguayo", "UYW": "Unidad Previsional", "UZS": "Uzbekistan Sum", "VED": "Bolivar Soberano",
    "VES": "Bolivar Soberano", "VND": "Dong", "VUV": "Vatu", "WST": "Tala", "XAF": "CFA Franc BEAC", "XAG": "Silver",
    "XAU": "Gold", "XBA": "Bond Markets Unit European Composite", "XBB": "Bond Markets Unit European Monetary",
    "XBC": "Bond Markets Unit European Unit of Account 9", "XBD": "Bond Markets Unit European Unit of Account 17",
    "XCD": "East Caribbean Dollar", "XDR": "SDR", "XOF": "CFA Franc BCEAO", "XPD": "Palladium", "XPF": "CFP Franc",
    "XPT": "Platinum", "XSU": "Sucre", "XTS": "Codes specifically reserved for testing", "XUA": "ADB Unit of Account",
    "XXX": "No currency", "YER": "Yemeni Rial", "ZAR": "Rand", "ZMW": "Zambian Kwacha", "ZWG": "Zimbabwe Gold",
}


def _iso_exponent(code: str) -> int:
    if code in _ISO_ZERO:
        return 0
    if code in _ISO_THREE:
        return 3
    if code in _ISO_FOUR:
        return 4
    return 2


ISO_CURRENCIES = tuple((code, _iso_exponent(code), name) for code, name in sorted(_ISO_NAMES.items()))


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
    retained_earnings_account = models.ForeignKey(
        "finance.Account", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    cutover_mode = models.CharField(max_length=16, blank=True, default="")
    cutover_stage = models.CharField(max_length=32, blank=True, default="")
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


class FinanceCountryPack(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.CASCADE)
    country_code = models.CharField(max_length=16)
    enabled = models.BooleanField(default=False)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.CharField(max_length=36, blank=True, default="")
    capabilities = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "finance_country_pack"
        constraints = [
            models.UniqueConstraint(fields=["organization", "country_code"], name="uniq_finance_country_pack")
        ]


class FinanceAdjustment(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.CASCADE)
    kind = models.CharField(max_length=16)
    debit_account = models.ForeignKey("finance.Account", on_delete=models.PROTECT, related_name="+")
    credit_account = models.ForeignKey("finance.Account", on_delete=models.PROTECT, related_name="+")
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    entry_date = models.DateField()
    reverse_on = models.DateField()
    memo = models.CharField(max_length=255, blank=True, default="")
    journal = models.ForeignKey("finance.JournalEntry", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    reverse_journal = models.ForeignKey(
        "finance.JournalEntry", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        db_table = "finance_adjustment"


class FinanceFxReval(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.CASCADE)
    as_of = models.DateField()
    amount = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    journal = models.ForeignKey("finance.JournalEntry", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    reverse_journal = models.ForeignKey(
        "finance.JournalEntry", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        db_table = "finance_fx_reval"
        constraints = [models.UniqueConstraint(fields=["organization", "as_of"], name="uniq_finance_fx_reval")]


class FinanceWebhookEndpoint(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.CASCADE)
    url = models.CharField(max_length=500)
    secret = models.CharField(max_length=64)
    events = models.JSONField(default=list, blank=True)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "finance_webhook_endpoint"


class FinanceWebhookDelivery(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending"
        DELIVERED = "delivered"
        DEAD = "dead"

    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.CASCADE)
    endpoint = models.ForeignKey(FinanceWebhookEndpoint, on_delete=models.CASCADE)
    event_id = models.CharField(max_length=36)
    event_type = models.CharField(max_length=64)
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    attempts = models.PositiveSmallIntegerField(default=0)
    next_attempt = models.DateTimeField()
    last_error = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "finance_webhook_delivery"
        constraints = [models.UniqueConstraint(fields=["organization", "event_id"], name="uniq_finance_webhook_event")]
