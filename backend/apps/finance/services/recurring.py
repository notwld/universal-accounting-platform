from calendar import monthrange
from datetime import date, timedelta

from django.db import IntegrityError, transaction

from apps.authentication.exceptions import AuthAPIError
from apps.finance.models import (
    Bill,
    Contact,
    Invoice,
    RecurringOccurrence,
    RecurringSchedule,
)
from apps.finance.services.access import has_finance_permission
from apps.finance.services.context import finance_tx
from apps.finance.services.purchases import post_bill, post_expense, set_bill_lines
from apps.finance.services.sales import post_invoice, set_invoice_lines

KIND_ACTION = {
    RecurringSchedule.Kind.INVOICE: "finance.invoice.create",
    RecurringSchedule.Kind.BILL: "finance.bill.create",
    RecurringSchedule.Kind.EXPENSE: "finance.payment.record",
}


def clamp_day(year: int, month: int, day: int) -> date:
    return date(year, month, min(day, monthrange(year, month)[1]))


def add_month(value: date, day: int) -> date:
    year, month = value.year, value.month + 1
    if month == 13:
        year, month = year + 1, 1
    return clamp_day(year, month, day)


def first_on(start_on: date, *, frequency, day_of_month, weekday, month_of_year) -> date:
    if frequency == RecurringSchedule.Frequency.WEEKLY:
        target = int(weekday)
        cursor = start_on
        while cursor.weekday() != target:
            cursor += timedelta(days=1)
        return cursor
    if frequency == RecurringSchedule.Frequency.YEARLY:
        month = int(month_of_year)
        day = int(day_of_month)
        candidate = clamp_day(start_on.year, month, day)
        if candidate >= start_on:
            return candidate
        return clamp_day(start_on.year + 1, month, day)
    day = int(day_of_month)
    candidate = clamp_day(start_on.year, start_on.month, day)
    if candidate >= start_on:
        return candidate
    return add_month(start_on, day)


def advance(sched: RecurringSchedule, current: date) -> date:
    if sched.frequency == RecurringSchedule.Frequency.WEEKLY:
        return current + timedelta(days=7)
    if sched.frequency == RecurringSchedule.Frequency.YEARLY:
        return clamp_day(current.year + 1, int(sched.month_of_year), int(sched.day_of_month))
    return add_month(current, int(sched.day_of_month))


def create_schedule(*, user_id, org, payload) -> RecurringSchedule:
    kind = payload.get("kind")
    if kind not in KIND_ACTION:
        raise AuthAPIError("validation_error", "kind must be invoice, bill, or expense")
    frequency = payload.get("frequency") or RecurringSchedule.Frequency.MONTHLY
    if frequency not in RecurringSchedule.Frequency.values:
        raise AuthAPIError("validation_error", "frequency must be monthly, weekly, or yearly")
    weekday = payload.get("weekday")
    month_of_year = payload.get("month_of_year")
    day = payload.get("day_of_month")
    if frequency == RecurringSchedule.Frequency.WEEKLY:
        weekday = int(weekday if weekday is not None else 0)
        if weekday < 0 or weekday > 6:
            raise AuthAPIError("validation_error", "weekday must be 0-6")
        day = None
        month_of_year = None
    elif frequency == RecurringSchedule.Frequency.YEARLY:
        month_of_year = int(month_of_year or 0)
        day = int(day or 0)
        if month_of_year < 1 or month_of_year > 12 or day < 1 or day > 31:
            raise AuthAPIError("validation_error", "month_of_year and day_of_month required")
        weekday = None
    else:
        day = int(day or 0)
        if day < 1 or day > 31:
            raise AuthAPIError("validation_error", "day_of_month must be 1-31")
        weekday = None
        month_of_year = None
    start_on = date.fromisoformat(str(payload.get("start_on"))[:10])
    end_on = payload.get("end_on")
    if end_on:
        end_on = date.fromisoformat(str(end_on)[:10])
    if not Contact.objects.filter(id=payload.get("contact_id"), organization=org).exists():
        raise AuthAPIError("cross_organization", "Contact not found")
    lines = payload.get("lines") or []
    if not lines:
        raise AuthAPIError("validation_error", "lines are required")
    if kind == RecurringSchedule.Kind.EXPENSE and not payload.get("bank_account_id"):
        raise AuthAPIError("validation_error", "bank_account_id is required for expenses")
    auto_post = bool(payload.get("auto_post"))
    with finance_tx(user_id=user_id, organization_id=org.id):
        return RecurringSchedule.objects.create(
            organization=org,
            kind=kind,
            frequency=frequency,
            contact_id=payload.get("contact_id"),
            currency_id=payload.get("currency"),
            bank_account_id=payload.get("bank_account_id"),
            day_of_month=day,
            weekday=weekday,
            month_of_year=month_of_year,
            start_on=start_on,
            next_on=first_on(
                start_on, frequency=frequency, day_of_month=day, weekday=weekday, month_of_year=month_of_year
            ),
            end_on=end_on,
            fx_rate=payload.get("fx_rate") or 1,
            auto_post=auto_post,
            lines=lines,
            created_by=user_id,
        )


def set_status(*, user_id, org, schedule_id, status):
    with finance_tx(user_id=user_id, organization_id=org.id):
        sched = RecurringSchedule.objects.select_for_update().filter(id=schedule_id, organization=org).first()
        if not sched:
            raise AuthAPIError("cross_organization", "Schedule not found")
        sched.status = status
        sched.save(update_fields=["status"])
        return sched


def _emit(user_id, org, sched: RecurringSchedule, occurs_on: date):
    if sched.kind == RecurringSchedule.Kind.INVOICE:
        inv = Invoice.objects.create(
            organization=org,
            contact_id=sched.contact_id,
            entry_date=occurs_on,
            due_date=occurs_on,
            currency_id=sched.currency_id,
            fx_rate=sched.fx_rate,
            created_by=user_id,
        )
        set_invoice_lines(inv, sched.lines)
        if sched.auto_post:
            inv = post_invoice(
                user_id=user_id, org=org, invoice=inv,
                idempotency_key=f"recurring:{sched.id}:{occurs_on.isoformat()}",
                skip_approval=True,
            )
        return {"invoice": inv}
    if sched.kind == RecurringSchedule.Kind.BILL:
        bill = Bill.objects.create(
            organization=org,
            contact_id=sched.contact_id,
            entry_date=occurs_on,
            due_date=occurs_on,
            currency_id=sched.currency_id,
            fx_rate=sched.fx_rate,
            created_by=user_id,
        )
        set_bill_lines(bill, sched.lines)
        if sched.auto_post:
            bill = post_bill(
                user_id=user_id, org=org, bill=bill,
                idempotency_key=f"recurring:{sched.id}:{occurs_on.isoformat()}",
                skip_approval=True,
            )
        return {"bill": bill}
    exp = post_expense(
        user_id=user_id,
        org=org,
        contact_id=sched.contact_id,
        bank_account_id=sched.bank_account_id,
        entry_date=occurs_on,
        currency_id=sched.currency_id,
        fx_rate=sched.fx_rate,
        lines=sched.lines,
        idempotency_key=f"recurring:{sched.id}:{occurs_on.isoformat()}",
    )
    return {"expense": exp}


def run_due(*, user_id, org, as_of: date, kinds=None):
    created = []
    with finance_tx(user_id=user_id, organization_id=org.id):
        qs = RecurringSchedule.objects.select_for_update().filter(
            organization=org, status=RecurringSchedule.Status.ACTIVE, next_on__lte=as_of
        )
        if kinds:
            qs = qs.filter(kind__in=list(kinds))
        for sched in qs:
            while sched.next_on <= as_of and (sched.end_on is None or sched.next_on <= sched.end_on):
                occurs_on = sched.next_on
                try:
                    with transaction.atomic():
                        occ = RecurringOccurrence.objects.create(
                            organization=org, schedule=sched, occurs_on=occurs_on
                        )
                except IntegrityError:
                    sched.next_on = advance(sched, occurs_on)
                    continue
                docs = _emit(user_id, org, sched, occurs_on)
                for field, obj in docs.items():
                    setattr(occ, field, obj)
                occ.save()
                created.append(occ)
                sched.next_on = advance(sched, occurs_on)
            sched.save(update_fields=["next_on"])
    return created


def allowed_kinds(user_id, org_id):
    return {kind for kind, action in KIND_ACTION.items() if has_finance_permission(user_id, org_id, action)}
