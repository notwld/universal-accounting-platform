from decimal import Decimal

from django.utils import timezone

from apps.authentication.exceptions import AuthAPIError
from apps.finance.models import (
    BankLine,
    Bill,
    FinanceException,
    FinanceSettings,
    FiscalPeriodLock,
    Invoice,
    JournalEntry,
)
from apps.finance.selectors.reports import profit_loss
from apps.finance.services.context import finance_tx
from apps.finance.services.posting import post_generated


def _settings(org) -> FinanceSettings:
    s = FinanceSettings.objects.select_related("base_currency", "retained_earnings_account").filter(
        organization=org
    ).first()
    if not s:
        raise AuthAPIError("validation_error", "Finance setup is incomplete")
    return s


def require_close_ready(org, period: FiscalPeriodLock):
    start, end = period.start_on, period.end_on
    if Invoice.objects.filter(organization=org, status=Invoice.Status.DRAFT, entry_date__gte=start, entry_date__lte=end).exists():
        raise AuthAPIError("close_blocked", "Draft invoices remain in the period")
    if Bill.objects.filter(organization=org, status=Bill.Status.DRAFT, entry_date__gte=start, entry_date__lte=end).exists():
        raise AuthAPIError("close_blocked", "Draft bills remain in the period")
    if JournalEntry.objects.filter(
        organization=org, status=JournalEntry.Status.DRAFT, entry_date__gte=start, entry_date__lte=end
    ).exists():
        raise AuthAPIError("close_blocked", "Draft journals remain in the period")
    if BankLine.objects.filter(
        organization=org,
        entry_date__gte=start,
        entry_date__lte=end,
        status__in=[BankLine.Status.IMPORTED, BankLine.Status.REVIEW],
    ).exists():
        raise AuthAPIError("close_blocked", "Unresolved bank lines remain in the period")
    if FinanceException.objects.filter(organization=org, status=FinanceException.Status.OPEN).exists():
        raise AuthAPIError("close_blocked", "Unresolved exceptions remain")
    from decimal import Decimal as D

    from apps.finance.models import ExchangeRate, RecurringSchedule
    from apps.finance.services.assets import register
    from apps.finance.services.stock import valuation

    val = valuation(org=org)
    if D(val["stock_total"]) != D(val["gl_inventory"]):
        raise AuthAPIError("close_blocked", "Inventory valuation does not match GL")
    reg = register(org=org)
    if D(reg["register_nbv"]) != D(reg["gl_nbv"]):
        raise AuthAPIError("close_blocked", "Asset register does not match GL")
    if RecurringSchedule.objects.filter(
        organization=org, status=RecurringSchedule.Status.ACTIVE, next_on__gte=start, next_on__lte=end
    ).exists():
        raise AuthAPIError("close_blocked", "Unposted recurring schedules remain")
    base = _settings(org).base_currency_id
    fx_invoices = Invoice.objects.filter(
        organization=org, status=Invoice.Status.POSTED, entry_date__gte=start, entry_date__lte=end
    ).exclude(currency_id=base)
    for inv in fx_invoices:
        if not ExchangeRate.objects.filter(organization=org, currency_id=inv.currency_id, as_of__lte=end).exists():
            raise AuthAPIError("close_blocked", "Missing FX rates for the period")


def _post_year_end(*, user_id, org, period: FiscalPeriodLock, idempotency_key):
    settings = _settings(org)
    if not settings.retained_earnings_account_id:
        raise AuthAPIError("validation_error", "Retained earnings account is not configured")
    exponent = settings.base_currency.exponent
    pnl = profit_loss(org=org, start=period.start_on, end=period.end_on, exponent=exponent)
    gl = []
    for row in pnl["income"]:
        amt = Decimal(row["amount"])
        if amt:
            gl.append({"account_id": row["account_id"], "debit": str(amt), "credit": "0", "description": "year close"})
    for row in pnl["expense"]:
        amt = Decimal(row["amount"])
        if amt:
            gl.append({"account_id": row["account_id"], "debit": "0", "credit": str(amt), "description": "year close"})
    net = Decimal(pnl["net_income"])
    if net > 0:
        gl.append(
            {
                "account_id": settings.retained_earnings_account_id,
                "debit": "0",
                "credit": str(net),
                "description": "retained earnings",
            }
        )
    elif net < 0:
        gl.append(
            {
                "account_id": settings.retained_earnings_account_id,
                "debit": str(-net),
                "credit": "0",
                "description": "retained earnings",
            }
        )
    if len(gl) < 2:
        return None
    return post_generated(
        user_id=user_id,
        org=org,
        entry_date=period.end_on,
        source_type=JournalEntry.Source.CLOSE,
        memo="year close",
        gl_lines=gl,
        idempotency_key=idempotency_key or f"year-close:{period.id}",
        body={"period_id": period.id, "year_end": True},
    )


def lock_period(*, user_id, org, period_id, year_end=False, idempotency_key=""):
    with finance_tx(user_id=user_id, organization_id=org.id):
        period = FiscalPeriodLock.objects.select_for_update().filter(id=period_id, organization=org).first()
        if not period:
            raise AuthAPIError("cross_organization", "Period not found")
        if period.status == FiscalPeriodLock.Status.LOCKED:
            return period
        require_close_ready(org, period)
        if year_end:
            _post_year_end(user_id=user_id, org=org, period=period, idempotency_key=idempotency_key)
        period.status = FiscalPeriodLock.Status.LOCKED
        period.locked_by = user_id
        period.locked_at = timezone.now()
        period.save(update_fields=["status", "locked_by", "locked_at"])
        return period
