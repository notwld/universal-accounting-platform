from apps.finance.models import Bill, Invoice
from apps.finance.services.purchases import outstanding as bill_outstanding
from apps.finance.services.sales import outstanding


def ar_aging(*, org, as_of):
    rows = []
    invoices = Invoice.objects.filter(organization=org, status=Invoice.Status.POSTED, entry_date__lte=as_of)
    for inv in invoices:
        due = outstanding(inv, as_of=as_of)
        if due <= 0:
            continue
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
    return rows


def ap_aging(*, org, as_of):
    rows = []
    bills = Bill.objects.filter(organization=org, status=Bill.Status.POSTED, entry_date__lte=as_of)
    for bill in bills:
        due = bill_outstanding(bill, as_of=as_of)
        if due <= 0:
            continue
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
    return rows
