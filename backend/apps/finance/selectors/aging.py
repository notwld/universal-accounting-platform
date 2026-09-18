from decimal import Decimal

from django.db.models import Sum

from apps.finance.models import Bill, FinanceSettings, Invoice, JournalEntry, JournalLine
from apps.finance.services.money import quantize_amount
from apps.finance.services.purchases import outstanding as bill_outstanding
from apps.finance.services.sales import outstanding


def _control_balance(*, org, account_id, as_of, exponent):
    if not account_id:
        return Decimal("0")
    agg = JournalLine.objects.filter(
        organization=org,
        account_id=account_id,
        journal__status=JournalEntry.Status.POSTED,
        journal__entry_date__lte=as_of,
    ).aggregate(d=Sum("debit"), c=Sum("credit"))
    return quantize_amount((agg["d"] or 0) - (agg["c"] or 0), exponent)


def ar_aging(*, org, as_of):
    settings = FinanceSettings.objects.select_related("base_currency").filter(organization=org).first()
    exponent = settings.base_currency.exponent if settings else 2
    rows = []
    total = Decimal("0")
    invoices = Invoice.objects.filter(organization=org, status=Invoice.Status.POSTED, entry_date__lte=as_of)
    for inv in invoices:
        due = outstanding(inv, as_of=as_of)
        if due <= 0:
            continue
        total += due
        rows.append(
            {
                "invoice_id": inv.id,
                "number": inv.number,
                "contact_name": inv.contact_name,
                "entry_date": inv.entry_date.isoformat(),
                "due_date": inv.due_date.isoformat(),
                "outstanding": str(due),
            }
        )
    control = _control_balance(
        org=org, account_id=settings.ar_account_id if settings else None, as_of=as_of, exponent=exponent
    )
    return {
        "items": rows,
        "outstanding_total": str(quantize_amount(total, exponent)),
        "control_balance": str(control),
    }


def ap_aging(*, org, as_of):
    settings = FinanceSettings.objects.select_related("base_currency").filter(organization=org).first()
    exponent = settings.base_currency.exponent if settings else 2
    rows = []
    total = Decimal("0")
    bills = Bill.objects.filter(organization=org, status=Bill.Status.POSTED, entry_date__lte=as_of)
    for bill in bills:
        due = bill_outstanding(bill, as_of=as_of)
        if due <= 0:
            continue
        total += due
        rows.append(
            {
                "bill_id": bill.id,
                "number": bill.number,
                "contact_name": bill.contact_name,
                "entry_date": bill.entry_date.isoformat(),
                "due_date": bill.due_date.isoformat(),
                "outstanding": str(due),
            }
        )
    control = _control_balance(
        org=org, account_id=settings.ap_account_id if settings else None, as_of=as_of, exponent=exponent
    )
    return {
        "items": rows,
        "outstanding_total": str(quantize_amount(total, exponent)),
        "control_balance": str(-control if control < 0 else control),
    }
