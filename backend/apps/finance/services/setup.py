from zoneinfo import ZoneInfo

from django.utils import timezone

from apps.authentication.exceptions import AuthAPIError
from apps.finance.models import (
    Account,
    Currency,
    DocumentSequence,
    FinanceGrant,
    FinanceRole,
    FinanceSettings,
    JournalEntry,
)
from apps.finance.permissions import PRESETS
from apps.tenancy.models import Membership, Organization


def create_organization(*, user_id: str, name: str) -> Organization:
    name = (name or "").strip()
    if not name:
        raise AuthAPIError("validation_error", "Name is required")
    org = Organization.objects.create(name=name)
    Membership.objects.create(
        user_id=user_id,
        organization=org,
        roles=["owner"],
        status=Membership.Status.ACTIVE,
    )
    seed_preset_roles(org)
    owner_role = FinanceRole.objects.get(organization=org, slug="owner")
    FinanceGrant.objects.create(organization=org, user_id=user_id, role=owner_role)
    return org


def seed_preset_roles(org: Organization):
    names = {
        "owner": "Owner",
        "finance_admin": "Finance Admin",
        "accountant": "Accountant",
        "sales_clerk": "Sales Clerk",
        "purchasing_clerk": "Purchasing Clerk",
        "approver": "Approver",
        "viewer": "Viewer",
    }
    for slug, perms in PRESETS.items():
        role, _ = FinanceRole.objects.get_or_create(
            organization=org,
            slug=slug,
            defaults={"name": names[slug], "permissions": list(perms), "is_preset": True},
        )
        if role.is_preset:
            role.permissions = list(perms)
            role.name = names[slug]
            role.save(update_fields=["permissions", "name"])


def upsert_settings(*, org: Organization, payload: dict) -> FinanceSettings:
    country = (payload.get("country_code") or "").upper()
    if len(country) != 2 or not country.isalpha():
        raise AuthAPIError("validation_error", "country_code must be ISO 3166-1 alpha-2")
    code = (payload.get("base_currency") or "").upper()
    currency = Currency.objects.filter(pk=code).first()
    if not currency:
        raise AuthAPIError("validation_error", "Unknown currency")
    month = int(payload.get("fiscal_year_start_month") or 0)
    if month < 1 or month > 12:
        raise AuthAPIError("validation_error", "fiscal_year_start_month must be 1-12")
    tz = payload.get("timezone") or ""
    try:
        ZoneInfo(tz)
    except Exception as exc:
        raise AuthAPIError("validation_error", "Invalid timezone") from exc
    existing = FinanceSettings.objects.filter(organization=org).first()
    if existing and existing.base_currency_id != currency.code:
        if JournalEntry.objects.filter(organization=org, status=JournalEntry.Status.POSTED).exists():
            raise AuthAPIError("base_currency_locked", "Base currency cannot change after posting")
    defaults = {
        "country_code": country,
        "base_currency": currency,
        "fiscal_year_start_month": month,
        "timezone": tz,
        "locale": payload.get("locale") or "en",
        "tax_registration_applies": bool(payload.get("tax_registration_applies")),
        "setup_completed_at": timezone.now(),
    }
    for key, field in (
        ("ar_account_id", "ar_account_id"),
        ("advance_account_id", "advance_account_id"),
        ("fx_gain_account_id", "fx_gain_account_id"),
        ("fx_loss_account_id", "fx_loss_account_id"),
        ("ap_account_id", "ap_account_id"),
        ("vendor_advance_account_id", "vendor_advance_account_id"),
        ("inventory_account_id", "inventory_account_id"),
        ("cogs_account_id", "cogs_account_id"),
        ("retained_earnings_account_id", "retained_earnings_account_id"),
    ):
        if payload.get(key):
            acc = Account.objects.filter(id=payload[key], organization=org).first()
            if not acc:
                raise AuthAPIError("cross_organization", "Account does not belong to organization")
            defaults[field] = acc.id
    if "require_document_approval" in payload:
        defaults["require_document_approval"] = bool(payload.get("require_document_approval"))
    if "allow_self_approve" in payload:
        defaults["allow_self_approve"] = bool(payload.get("allow_self_approve"))
    if "approval_threshold" in payload:
        try:
            from decimal import Decimal

            defaults["approval_threshold"] = Decimal(str(payload.get("approval_threshold") or 0))
        except Exception as exc:
            raise AuthAPIError("validation_error", "Invalid approval_threshold") from exc
    if "approval_levels" in payload:
        try:
            levels = int(payload.get("approval_levels") or 1)
        except (TypeError, ValueError) as exc:
            raise AuthAPIError("validation_error", "Invalid approval_levels") from exc
        if levels < 1:
            raise AuthAPIError("validation_error", "approval_levels must be at least 1")
        defaults["approval_levels"] = levels
    settings, _ = FinanceSettings.objects.update_or_create(organization=org, defaults=defaults)
    DocumentSequence.objects.get_or_create(
        organization=org,
        document_type="journal",
        series="default",
        defaults={"prefix": "JE-", "next_number": 1},
    )
    seed_preset_roles(org)
    return settings
