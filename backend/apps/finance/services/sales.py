from decimal import Decimal

from django.db.models import Sum

from apps.authentication.exceptions import AuthAPIError
from apps.finance.models import (
    Allocation,
    CreditNote,
    CustomerPayment,
    CustomerRefund,
    ExchangeRate,
    FinanceSettings,
    Invoice,
    InvoiceLine,
    Item,
    JournalEntry,
    Quote,
    TaxRate,
)
from apps.finance.services.approvals import invalidate_approval, require_approved_for_post
from apps.finance.services.context import finance_tx
from apps.finance.services.money import quantize_amount
from apps.finance.services.posting import post_generated
from apps.finance.services.sequence import next_document_number
from apps.finance.services.tax import line_tax


def _settings(org) -> FinanceSettings:
    s = FinanceSettings.objects.select_related(
        "base_currency", "ar_account", "advance_account", "fx_gain_account", "fx_loss_account"
    ).filter(organization=org).first()
    if not s:
        raise AuthAPIError("validation_error", "Finance setup is incomplete")
    return s


def resolve_rate(org, currency_id, entry_date, base_id, explicit=None) -> Decimal:
    if currency_id == base_id:
        return Decimal("1")
    if explicit not in (None, ""):
        rate = Decimal(str(explicit))
        if rate != 1:
            return rate
    row = ExchangeRate.objects.filter(organization=org, currency_id=currency_id, as_of=entry_date).first()
    if not row:
        raise AuthAPIError("missing_rate", "Exchange rate is required")
    return row.rate


def to_base(amount, rate, exponent) -> Decimal:
    return quantize_amount(Decimal(str(amount)) * Decimal(str(rate)), exponent)


def outstanding(invoice: Invoice, as_of=None) -> Decimal:
    alloc = Allocation.objects.filter(invoice=invoice)
    if as_of:
        alloc = alloc.filter(entry_date__lte=as_of)
    used = alloc.aggregate(s=Sum("amount"))["s"] or Decimal("0")
    return invoice.total - used


def require_sales_accounts(settings: FinanceSettings):
    if not settings.ar_account_id:
        raise AuthAPIError("validation_error", "AR account is not configured")


def _preview_or_snapshot_invoice(invoice: Invoice, *, persist: bool):
    settings = _settings(invoice.organization)
    exponent = settings.base_currency.exponent
    fx = resolve_rate(
        invoice.organization, invoice.currency_id, invoice.entry_date, settings.base_currency_id, invoice.fx_rate
    )
    gl = []
    total = Decimal("0")
    base_total = Decimal("0")
    if persist:
        invoice.lines.all().delete()
    for raw in invoice._pending_lines:
        item = Item.objects.filter(id=raw["item_id"], organization=invoice.organization).first()
        if not item or item.status != "active":
            raise AuthAPIError("validation_error", "Item is inactive or missing")
        qty = Decimal(str(raw.get("quantity") or 1))
        price = Decimal(str(raw.get("unit_price") if raw.get("unit_price") is not None else item.unit_price))
        ext = qty * price
        tax = None
        tax_id = raw.get("tax_rate_id") or (item.default_tax_id)
        if tax_id:
            tax = TaxRate.objects.filter(id=tax_id, organization=invoice.organization).first()
        method = tax.method if tax else "exclusive"
        rate = tax.rate if tax else Decimal("0")
        net, tax_amt, line_total = line_tax(amount=ext, rate=rate, method=method, exponent=exponent)
        base_net = to_base(net, fx, exponent)
        base_tax = to_base(tax_amt, fx, exponent)
        base_line = to_base(line_total, fx, exponent)
        total += line_total
        base_total += base_line
        if persist:
            InvoiceLine.objects.create(
                invoice=invoice,
                organization=invoice.organization,
                item=item,
                description=raw.get("description") or item.name,
                quantity=qty,
                unit_price=price,
                tax_rate_id_snap=tax.id if tax else "",
                tax_rate_value=rate,
                tax_method=method,
                tax_name=tax.name if tax else "",
                net=net,
                tax_amount=tax_amt,
                total=line_total,
                base_net=base_net,
                base_tax=base_tax,
                base_total=base_line,
                income_account=item.income_account,
            )
        gl.append(("income", item.income_account_id, base_net, raw.get("description") or item.name))
        if tax and base_tax:
            gl.append(("tax", tax.payable_account_id, base_tax, tax.name))
    require_sales_accounts(settings)
    journal_lines = [
        {"account_id": settings.ar_account_id, "debit": str(base_total), "credit": "0", "description": "AR"}
    ]
    for kind, account_id, amt, desc in gl:
        if amt:
            journal_lines.append(
                {"account_id": account_id, "debit": "0", "credit": str(amt), "description": desc}
            )
    if persist:
        invoice.fx_rate = fx
        invoice.total = total
        invoice.base_total = base_total
        invoice.contact_name = invoice.contact.name
        invoice.save()
    return journal_lines, total, base_total


def set_invoice_lines(invoice, lines):
    if invoice.pk:
        invalidate_approval(invoice)
    invoice._pending_lines = lines
    _preview_or_snapshot_invoice(invoice, persist=True)


def invoice_preview(invoice):
    invoice._pending_lines = [
        {
            "item_id": line.item_id,
            "quantity": line.quantity,
            "unit_price": line.unit_price,
            "tax_rate_id": line.tax_rate_id_snap or None,
            "description": line.description,
        }
        for line in invoice.lines.all()
    ]
    gl, _, _ = _preview_or_snapshot_invoice(invoice, persist=False)
    return gl


def post_invoice(*, user_id, org, invoice, idempotency_key, skip_approval=False):
    with finance_tx(user_id=user_id, organization_id=org.id):
        inv = Invoice.objects.select_for_update().filter(id=invoice.id, organization=org).first()
        if not inv or inv.status == Invoice.Status.POSTED:
            if inv and inv.status == Invoice.Status.POSTED:
                return inv
            raise AuthAPIError("cross_organization", "Invoice not found")
        require_approved_for_post(org, inv, skip_approval=skip_approval)
        inv._pending_lines = [
            {
                "item_id": line.item_id,
                "quantity": line.quantity,
                "unit_price": line.unit_price,
                "tax_rate_id": line.tax_rate_id_snap or None,
                "description": line.description,
            }
            for line in inv.lines.all()
        ]
        gl, _, _ = _preview_or_snapshot_invoice(inv, persist=False)
        posted = post_generated(
            user_id=user_id,
            org=org,
            entry_date=inv.entry_date,
            source_type=JournalEntry.Source.INVOICE,
            memo=inv.number or "invoice",
            gl_lines=gl,
            idempotency_key=idempotency_key,
            body={"invoice_id": inv.id},
        )
        inv.status = Invoice.Status.POSTED
        inv.number = next_document_number(org, "invoice", "INV-")
        inv.journal = posted
        Invoice.objects.filter(pk=inv.pk).update(
            status=inv.status, number=inv.number, journal=posted, total=inv.total, base_total=inv.base_total,
            fx_rate=inv.fx_rate, contact_name=inv.contact_name,
        )
        return Invoice.objects.get(pk=inv.pk)


def convert_quote(quote: Quote) -> Invoice:
    if quote.status != Quote.Status.DRAFT:
        raise AuthAPIError("quote_not_convertible", "Quote already converted")
    settings = _settings(quote.organization)
    invoice = Invoice.objects.create(
        organization=quote.organization,
        contact=quote.contact,
        quote=quote,
        entry_date=quote.entry_date,
        due_date=quote.entry_date,
        currency=quote.currency,
        fx_rate=1,
    )
    set_invoice_lines(
        invoice,
        [
            {
                "item_id": line.item_id,
                "quantity": line.quantity,
                "unit_price": line.unit_price,
                "tax_rate_id": line.tax_rate_id,
                "description": line.description,
            }
            for line in quote.lines.all()
        ],
    )
    quote.status = Quote.Status.CONVERTED
    quote.save(update_fields=["status"])
    return invoice


def post_credit(*, user_id, org, credit: CreditNote, idempotency_key):
    settings = _settings(org)
    require_sales_accounts(settings)
    with finance_tx(user_id=user_id, organization_id=org.id):
        cn = CreditNote.objects.select_for_update().get(pk=credit.pk)
        gl = [{"account_id": settings.ar_account_id, "debit": "0", "credit": str(cn.base_total), "description": "AR"}]
        for line in cn.lines.all():
            gl.append({"account_id": line.income_account_id, "debit": str(line.base_net), "credit": "0", "description": line.description})
            if line.base_tax and line.tax_payable_account_id:
                gl.append({"account_id": line.tax_payable_account_id, "debit": str(line.base_tax), "credit": "0", "description": "tax"})
        posted = post_generated(
            user_id=user_id, org=org, entry_date=cn.entry_date, source_type=JournalEntry.Source.CREDIT,
            memo="credit", gl_lines=gl, idempotency_key=idempotency_key, body={"credit_id": cn.id},
        )
        cn.status = CreditNote.Status.POSTED
        cn.number = next_document_number(org, "credit", "CN-")
        cn.journal = posted
        cn.save()
        if cn.invoice_id:
            inv = Invoice.objects.select_for_update().get(pk=cn.invoice_id)
            remain = outstanding(inv)
            apply = min(remain, cn.total)
            if apply < cn.total:
                raise AuthAPIError("over_allocation", "Credit exceeds invoice outstanding")
            Allocation.objects.create(
                organization=org, invoice=inv, credit_note=cn, amount=apply,
                base_amount=cn.base_total, entry_date=cn.entry_date,
            )
        return cn


def post_payment(*, user_id, org, payment: CustomerPayment, allocations: list, idempotency_key):
    settings = _settings(org)
    require_sales_accounts(settings)
    exponent = settings.base_currency.exponent
    if not settings.advance_account_id:
        raise AuthAPIError("validation_error", "Advance account is not configured")
    with finance_tx(user_id=user_id, organization_id=org.id):
        pay = CustomerPayment.objects.select_for_update().get(pk=payment.pk)
        fx = resolve_rate(org, pay.currency_id, pay.entry_date, settings.base_currency_id, pay.fx_rate)
        cash_base = to_base(pay.amount, fx, exponent)
        remaining_pay = pay.amount
        ar_base = Decimal("0")
        created = []
        for alloc in allocations:
            inv = Invoice.objects.select_for_update().filter(
                id=alloc["invoice_id"], organization=org, status=Invoice.Status.POSTED
            ).first()
            if not inv:
                raise AuthAPIError("cross_organization", "Invoice not found")
            amt = Decimal(str(alloc["amount"]))
            if amt <= 0:
                raise AuthAPIError("validation_error", "Allocation must be positive")
            remain = outstanding(inv)
            if amt > remain or amt > remaining_pay:
                raise AuthAPIError("over_allocation", "Allocation exceeds available amount")
            base_amt = to_base(amt, inv.fx_rate, exponent)
            created.append((inv, amt, base_amt))
            remaining_pay -= amt
            ar_base += base_amt
        advance_foreign = remaining_pay
        advance_base = to_base(advance_foreign, fx, exponent)
        gl = [{"account_id": pay.bank_account_id, "debit": str(cash_base), "credit": "0", "description": "bank"}]
        if ar_base:
            gl.append({"account_id": settings.ar_account_id, "debit": "0", "credit": str(ar_base), "description": "AR"})
        if advance_base:
            gl.append({"account_id": settings.advance_account_id, "debit": "0", "credit": str(advance_base), "description": "advance"})
        fx_diff = cash_base - ar_base - advance_base
        if fx_diff != 0:
            gain = settings.fx_gain_account_id
            loss = settings.fx_loss_account_id
            if fx_diff > 0:
                if not gain:
                    raise AuthAPIError("validation_error", "FX gain account is not configured")
                gl.append({"account_id": gain, "debit": "0", "credit": str(fx_diff), "description": "fx"})
            else:
                if not loss:
                    raise AuthAPIError("validation_error", "FX loss account is not configured")
                gl.append({"account_id": loss, "debit": str(-fx_diff), "credit": "0", "description": "fx"})
        posted = post_generated(
            user_id=user_id, org=org, entry_date=pay.entry_date, source_type=JournalEntry.Source.PAYMENT,
            memo="payment", gl_lines=gl, idempotency_key=idempotency_key, body={"payment_id": pay.id, "allocations": allocations},
        )
        pay.status = CustomerPayment.Status.POSTED
        pay.fx_rate = fx
        pay.journal = posted
        pay.save()
        for inv, amt, base_amt in created:
            Allocation.objects.create(
                organization=org, invoice=inv, payment=pay, amount=amt, base_amount=base_amt, entry_date=pay.entry_date
            )
        return pay


def refund_payment(*, user_id, org, payment: CustomerPayment, amount, bank_account_id, entry_date, idempotency_key):
    settings = _settings(org)
    if not settings.advance_account_id:
        raise AuthAPIError("validation_error", "Advance account is not configured")
    amt = Decimal(str(amount))
    allocated = Allocation.objects.filter(payment=payment).aggregate(s=Sum("amount"))["s"] or Decimal("0")
    available = payment.amount - allocated
    refunded = CustomerRefund.objects.filter(payment=payment).aggregate(s=Sum("amount"))["s"] or Decimal("0")
    available -= refunded
    if amt > available:
        raise AuthAPIError("over_allocation", "Refund exceeds remaining advance")
    exponent = settings.base_currency.exponent
    base = to_base(amt, payment.fx_rate, exponent)
    with finance_tx(user_id=user_id, organization_id=org.id):
        posted = post_generated(
            user_id=user_id, org=org, entry_date=entry_date, source_type=JournalEntry.Source.REFUND,
            memo="refund",
            gl_lines=[
                {"account_id": settings.advance_account_id, "debit": str(base), "credit": "0", "description": "advance"},
                {"account_id": bank_account_id, "debit": "0", "credit": str(base), "description": "bank"},
            ],
            idempotency_key=idempotency_key,
            body={"payment_id": payment.id, "amount": str(amt)},
        )
        return CustomerRefund.objects.create(
            organization=org, payment=payment, amount=amt, entry_date=entry_date,
            bank_account_id=bank_account_id, journal=posted,
        )
