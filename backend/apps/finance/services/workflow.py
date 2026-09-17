from decimal import Decimal, InvalidOperation

from apps.authentication.exceptions import AuthAPIError
from apps.finance.models import FinanceException, SavedFilter
from apps.finance.services.context import finance_tx

FILTER_FIELDS = {
    "invoice": ("status", "contact_id"),
    "bill": ("status", "contact_id"),
    "bank_line": ("status", "account_id"),
}


def record_exception(*, org, kind, reason, object_type="", object_id=""):
    return FinanceException.objects.create(
        organization=org,
        kind=kind,
        object_type=object_type or "",
        object_id=object_id or "",
        reason=(reason or "")[:500],
    )


def resolve_exception(*, user_id, org, exception_id, reason):
    if not (reason or "").strip():
        raise AuthAPIError("validation_error", "Resolve reason is required")
    with finance_tx(user_id=user_id, organization_id=org.id):
        row = FinanceException.objects.select_for_update().filter(id=exception_id, organization=org).first()
        if not row:
            raise AuthAPIError("cross_organization", "Exception not found")
        row.status = FinanceException.Status.RESOLVED
        row.reason = f"{row.reason}\nresolved: {reason.strip()}".strip()
        row.save(update_fields=["status", "reason"])
        return row


def create_saved_filter(*, user_id, org, payload):
    name = str(payload.get("name") or "").strip()
    resource = str(payload.get("resource") or "").strip()
    if not name or resource not in FILTER_FIELDS:
        raise AuthAPIError("validation_error", "name and resource are required")
    params = payload.get("params") if isinstance(payload.get("params"), dict) else {}
    allowed = FILTER_FIELDS[resource]
    clean = {k: v for k, v in params.items() if k in allowed and v not in (None, "")}
    with finance_tx(user_id=user_id, organization_id=org.id):
        return SavedFilter.objects.create(organization=org, name=name[:100], resource=resource, params=clean)


def apply_saved_filter(qs, *, org, resource, filter_id):
    if not filter_id:
        return qs
    filt = SavedFilter.objects.filter(id=filter_id, organization=org, resource=resource).first()
    if not filt:
        raise AuthAPIError("cross_organization", "Saved filter not found")
    allowed = FILTER_FIELDS[resource]
    kwargs = {k: v for k, v in (filt.params or {}).items() if k in allowed and v not in (None, "")}
    return qs.filter(**kwargs) if kwargs else qs


def parse_optional_decimal(value):
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise AuthAPIError("validation_error", "Invalid amount") from exc
