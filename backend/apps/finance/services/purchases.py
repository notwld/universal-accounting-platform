from decimal import Decimal

from django.db.models import Sum

from apps.authentication.exceptions import AuthAPIError
from apps.finance.models import (
    Account,
    Bill,
    BillAllocation,
    BillLine,
    FinanceSettings,
    Item,
    JournalEntry,
    PaidExpense,
    PaidExpenseLine,
    PaymentRun,
    PaymentRunLine,
    PurchaseOrder,
    TaxRate,
    VendorCredit,
    VendorCreditLine,
    VendorPayment,
    VendorRefund,
)
from apps.finance.services.approvals import invalidate_approval, require_approved_for_post
from apps.finance.services.context import finance_tx
from apps.finance.services.money import quantize_quantity
from apps.finance.services.posting import begin_command, finish_command, post_generated, replay_resource
from apps.finance.services.resolve import currency_get, org_get, org_get_optional
from apps.finance.services.sales import resolve_rate, to_base
from apps.finance.services.sequence import next_document_number
from apps.finance.services.stock import receive_line, return_qty
from apps.finance.services.tax import line_tax


def _settings(org) -> FinanceSettings:
    s = FinanceSettings.objects.select_related(
        "base_currency", "ap_account", "vendor_advance_account", "fx_gain_account", "fx_loss_account"
    ).filter(organization=org).first()
    if not s:
        raise AuthAPIError("validation_error", "Finance setup is incomplete")
    return s


def require_ap(settings: FinanceSettings):
    if not settings.ap_account_id:
        raise AuthAPIError("validation_error", "AP account is not configured")


def outstanding(bill: Bill, as_of=None) -> Decimal:
    alloc = BillAllocation.objects.filter(bill=bill)
    if as_of:
        alloc = alloc.filter(entry_date__lte=as_of)
    used = alloc.aggregate(s=Sum("amount"))["s"] or Decimal("0")
    return bill.total - used


def _snapshot_bill(bill: Bill, lines):
    settings = _settings(bill.organization)
    exponent = settings.base_currency.exponent
    fx = resolve_rate(
        bill.organization, bill.currency_id, bill.entry_date, settings.base_currency_id, bill.fx_rate
    )
    gl = []
    total = Decimal("0")
    base_total = Decimal("0")
    bill.lines.all().delete()
    for raw in lines:
        item = Item.objects.filter(id=raw["item_id"], organization=bill.organization).first()
        if not item or item.status != "active":
            raise AuthAPIError("validation_error", "Item is inactive or missing")
        expense_id = raw.get("expense_account_id") or item.expense_account_id
        if item.tracked:
            if item.kind != Item.Kind.GOOD:
                raise AuthAPIError("validation_error", "Tracked items must be goods")
            if not settings.inventory_account_id:
                raise AuthAPIError("validation_error", "Inventory and COGS accounts are required")
            expense_id = settings.inventory_account_id
        if not expense_id:
            raise AuthAPIError("validation_error", "Expense account is required")
        qty = Decimal(str(raw.get("quantity") or 1))
        price = Decimal(str(raw.get("unit_price") if raw.get("unit_price") is not None else item.unit_price))
        ext = qty * price
        tax = None
        tax_id = raw.get("tax_rate_id") or item.default_tax_id
        if tax_id:
            tax = TaxRate.objects.filter(id=tax_id, organization=bill.organization).first()
        method = tax.method if tax else "exclusive"
        rate = tax.rate if tax else Decimal("0")
        net, tax_amt, line_total = line_tax(amount=ext, rate=rate, method=method, exponent=exponent)
        base_net = to_base(net, fx, exponent)
        base_tax = to_base(tax_amt, fx, exponent)
        base_line = to_base(line_total, fx, exponent)
        total += line_total
        base_total += base_line
        BillLine.objects.create(
            bill=bill,
            organization=bill.organization,
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
            expense_account_id=expense_id,
        )
        gl.append(("expense", expense_id, base_net, raw.get("description") or item.name))
        if tax and base_tax:
            gl.append(("tax", tax.payable_account_id, base_tax, tax.name))
    require_ap(settings)
    journal_lines = []
    for _kind, account_id, amt, desc in gl:
        if amt:
            journal_lines.append(
                {"account_id": account_id, "debit": str(amt), "credit": "0", "description": desc}
            )
    journal_lines.append(
        {"account_id": settings.ap_account_id, "debit": "0", "credit": str(base_total), "description": "AP"}
    )
    bill.fx_rate = fx
    bill.total = total
    bill.base_total = base_total
    bill.contact_name = bill.contact.name
    bill.save()
    return journal_lines


def bill_preview(bill: Bill):
    settings = _settings(bill.organization)
    require_ap(settings)
    gl = []
    for line in bill.lines.all():
        if line.base_net:
            gl.append({"account_id": line.expense_account_id, "debit": str(line.base_net), "credit": "0", "description": line.description})
        if line.base_tax:
            tax = TaxRate.objects.filter(id=line.tax_rate_id_snap, organization=bill.organization).first()
            if tax:
                gl.append({"account_id": tax.payable_account_id, "debit": str(line.base_tax), "credit": "0", "description": line.tax_name})
    gl.append({"account_id": settings.ap_account_id, "debit": "0", "credit": str(bill.base_total), "description": "AP"})
    return gl


def set_bill_lines(bill, lines):
    if bill.pk:
        invalidate_approval(bill)
    return _snapshot_bill(bill, lines)


def post_bill(*, user_id, org, bill, idempotency_key, skip_approval=False):
    with finance_tx(user_id=user_id, organization_id=org.id):
        inv = Bill.objects.select_for_update().filter(id=bill.id, organization=org).first()
        if not inv:
            raise AuthAPIError("cross_organization", "Bill not found")
        if inv.status == Bill.Status.POSTED:
            return inv
        require_approved_for_post(org, inv, skip_approval=skip_approval)
        gl = bill_preview(inv)
        posted = post_generated(
            user_id=user_id,
            org=org,
            entry_date=inv.entry_date,
            source_type=JournalEntry.Source.BILL,
            memo=inv.number or "bill",
            gl_lines=gl,
            idempotency_key=idempotency_key,
            body={"bill_id": inv.id},
        )
        for line in inv.lines.select_related("item"):
            receive_line(
                org=org,
                item=line.item,
                qty=line.quantity,
                cost=line.base_net,
                source_type="bill",
                source_id=inv.id,
                entry_date=inv.entry_date,
            )
        inv.status = Bill.Status.POSTED
        inv.number = next_document_number(org, "bill", "BILL-")
        inv.journal = posted
        Bill.objects.filter(pk=inv.pk).update(
            status=inv.status, number=inv.number, journal=posted
        )
        return Bill.objects.get(pk=inv.pk)


def _vendor_credit_stock(*, org, credit: VendorCredit):
    from apps.finance.models import StockMove

    removed = Decimal("0")
    for line in credit.lines.select_related("item", "bill_line", "bill_line__item"):
        if line.price_only:
            continue
        qty = quantize_quantity(line.quantity or 0)
        if qty <= 0:
            continue
        item = line.item
        if line.bill_line_id:
            src = BillLine.objects.select_for_update().filter(pk=line.bill_line_id, organization=org).first()
            if not src:
                raise AuthAPIError("cross_organization", "Bill line not found")
            used = (
                VendorCreditLine.objects.filter(
                    bill_line=src, credit__status=VendorCredit.Status.POSTED, organization=org
                )
                .exclude(pk=line.pk)
                .aggregate(s=Sum("quantity"))["s"]
                or Decimal("0")
            )
            if used + qty > src.quantity:
                raise AuthAPIError("over_allocation", "Credit quantity exceeds source line")
            item = src.item
        if not item or not item.tracked:
            continue
        move = StockMove.objects.filter(
            organization=org,
            source_type="bill",
            source_id=credit.bill_id or "",
            item=item,
            kind=StockMove.Kind.RECEIVE,
        ).first()
        removed += return_qty(
            org=org,
            item=item,
            qty=qty,
            unit_cost=move.unit_cost if move else 0,
            source_type="vendor_credit",
            source_id=credit.id,
            entry_date=credit.entry_date,
            inbound=False,
        )
    return removed


def post_vendor_credit(*, user_id, org, credit: VendorCredit, idempotency_key):
    settings = _settings(org)
    require_ap(settings)
    with finance_tx(user_id=user_id, organization_id=org.id):
        cn = VendorCredit.objects.select_for_update().filter(pk=credit.pk, organization=org).first()
        if not cn:
            raise AuthAPIError("cross_organization", "Vendor credit not found")
        if cn.status == VendorCredit.Status.POSTED:
            return cn
        gl = [{"account_id": settings.ap_account_id, "debit": str(cn.base_total), "credit": "0", "description": "AP"}]
        for line in cn.lines.all():
            gl.append({"account_id": line.expense_account_id, "debit": "0", "credit": str(line.base_net), "description": line.description})
            if line.base_tax and line.tax_payable_account_id:
                gl.append({"account_id": line.tax_payable_account_id, "debit": "0", "credit": str(line.base_tax), "description": "tax"})
        removed = _vendor_credit_stock(org=org, credit=cn)
        if removed:
            if not settings.inventory_account_id or not settings.cogs_account_id:
                raise AuthAPIError("validation_error", "Inventory and COGS accounts are required")
            gl.append({"account_id": settings.cogs_account_id, "debit": str(removed), "credit": "0", "description": "COGS"})
            gl.append({"account_id": settings.inventory_account_id, "debit": "0", "credit": str(removed), "description": "inventory"})
        posted = post_generated(
            user_id=user_id, org=org, entry_date=cn.entry_date, source_type=JournalEntry.Source.VENDOR_CREDIT,
            memo="vendor credit", gl_lines=gl, idempotency_key=idempotency_key,             body={"vendor_credit_id": cn.id},
        )
        cn.status = VendorCredit.Status.POSTED
        cn.number = next_document_number(org, "vendor_credit", "VC-")
        cn.journal = posted
        cn.save()
        if cn.bill_id:
            bill = Bill.objects.select_for_update().filter(pk=cn.bill_id, organization=org).first()
            if not bill:
                raise AuthAPIError("cross_organization", "Bill not found")
            remain = outstanding(bill)
            apply = min(remain, cn.total)
            if apply < cn.total:
                raise AuthAPIError("over_allocation", "Credit exceeds bill outstanding")
            BillAllocation.objects.create(
                organization=org, bill=bill, credit=cn, amount=apply,
                base_amount=cn.base_total, entry_date=cn.entry_date,
            )
        return cn


def create_and_post_vendor_credit(*, user_id, org, payload, idempotency_key):
    from apps.finance.models import Contact

    body = {
        "contact_id": payload.get("contact_id"),
        "bill_id": payload.get("bill_id"),
        "entry_date": payload.get("entry_date"),
        "currency": payload.get("currency"),
        "total": str(payload.get("total") or 0),
        "lines": payload.get("lines") or [],
    }
    with finance_tx(user_id=user_id, organization_id=org.id):
        rec, replay = begin_command(org, "vendor_credit.command", idempotency_key, body)
        if replay:
            return replay_resource(rec, VendorCredit)
        contact = org_get(Contact, org, payload.get("contact_id"))
        bill = org_get_optional(Bill, org, payload.get("bill_id"))
        cn = VendorCredit.objects.create(
            organization=org,
            contact=contact,
            bill=bill,
            entry_date=payload.get("entry_date"),
            currency=currency_get(payload.get("currency")),
            fx_rate=payload.get("fx_rate") or 1,
            total=payload.get("total") or 0,
            base_total=payload.get("base_total") or 0,
        )
        for line in payload.get("lines") or []:
            src = org_get_optional(BillLine, org, line.get("bill_line_id"))
            if src and bill and src.bill_id != bill.id:
                raise AuthAPIError("cross_organization", "Bill line not found")
            item = org_get(Item, org, line.get("item_id")) if line.get("item_id") else (src.item if src else None)
            expense = org_get(Account, org, line.get("expense_account_id") or (item.expense_account_id if item else None))
            VendorCreditLine.objects.create(
                credit=cn,
                organization=org,
                bill_line=src,
                item=item,
                quantity=line.get("quantity") or 0,
                price_only=bool(line.get("price_only")),
                description=line.get("description") or "",
                expense_account=expense,
                net=line.get("net") or 0,
                tax_amount=line.get("tax_amount") or 0,
                total=line.get("total") or 0,
                base_net=line.get("base_net") or 0,
                base_tax=line.get("base_tax") or 0,
                base_total=line.get("base_total") or 0,
                tax_payable_account=org_get_optional(Account, org, line.get("tax_payable_account_id")),
            )
        posted = post_vendor_credit(user_id=user_id, org=org, credit=cn, idempotency_key=f"{idempotency_key}:post")
        finish_command(rec, resource_type="vendor_credit", resource_id=posted.id, journal=posted.journal)
        return posted


def create_and_post_vendor_payment(*, user_id, org, payload, idempotency_key):
    from apps.finance.models import Contact

    body = {
        "contact_id": payload.get("contact_id"),
        "bank_account_id": payload.get("bank_account_id"),
        "entry_date": payload.get("entry_date"),
        "currency": payload.get("currency"),
        "amount": str(payload.get("amount") or 0),
        "allocations": payload.get("allocations") or [],
    }
    with finance_tx(user_id=user_id, organization_id=org.id):
        rec, replay = begin_command(org, "vendor_payment.command", idempotency_key, body)
        if replay:
            return replay_resource(rec, VendorPayment)
        pay = VendorPayment.objects.create(
            organization=org,
            contact=org_get(Contact, org, payload.get("contact_id")),
            bank_account=org_get(Account, org, payload.get("bank_account_id")),
            entry_date=payload.get("entry_date"),
            currency=currency_get(payload.get("currency")),
            fx_rate=payload.get("fx_rate") or 1,
            amount=payload.get("amount"),
        )
        posted = post_vendor_payment(
            user_id=user_id,
            org=org,
            payment=pay,
            allocations=payload.get("allocations") or [],
            idempotency_key=f"{idempotency_key}:post",
        )
        finish_command(rec, resource_type="vendor_payment", resource_id=posted.id, journal=posted.journal)
        return posted


def post_vendor_payment(*, user_id, org, payment: VendorPayment, allocations: list, idempotency_key):
    settings = _settings(org)
    require_ap(settings)
    exponent = settings.base_currency.exponent
    if not settings.vendor_advance_account_id:
        raise AuthAPIError("validation_error", "Vendor advance account is not configured")
    with finance_tx(user_id=user_id, organization_id=org.id):
        pay = VendorPayment.objects.select_for_update().get(pk=payment.pk)
        fx = resolve_rate(org, pay.currency_id, pay.entry_date, settings.base_currency_id, pay.fx_rate)
        cash_base = to_base(pay.amount, fx, exponent)
        remaining_pay = pay.amount
        ap_base = Decimal("0")
        created = []
        for alloc in allocations:
            bill = Bill.objects.select_for_update().filter(
                id=alloc["bill_id"], organization=org, status=Bill.Status.POSTED
            ).first()
            if not bill:
                raise AuthAPIError("cross_organization", "Bill not found")
            amt = Decimal(str(alloc["amount"]))
            if amt <= 0:
                raise AuthAPIError("validation_error", "Allocation must be positive")
            remain = outstanding(bill)
            if amt > remain or amt > remaining_pay:
                raise AuthAPIError("over_allocation", "Allocation exceeds available amount")
            base_amt = to_base(amt, bill.fx_rate, exponent)
            created.append((bill, amt, base_amt))
            remaining_pay -= amt
            ap_base += base_amt
        advance_foreign = remaining_pay
        advance_base = to_base(advance_foreign, fx, exponent)
        gl = []
        if ap_base:
            gl.append({"account_id": settings.ap_account_id, "debit": str(ap_base), "credit": "0", "description": "AP"})
        if advance_base:
            gl.append({"account_id": settings.vendor_advance_account_id, "debit": str(advance_base), "credit": "0", "description": "advance"})
        gl.append({"account_id": pay.bank_account_id, "debit": "0", "credit": str(cash_base), "description": "bank"})
        fx_diff = cash_base - ap_base - advance_base
        if fx_diff != 0:
            gain = settings.fx_gain_account_id
            loss = settings.fx_loss_account_id
            if fx_diff > 0:
                if not loss:
                    raise AuthAPIError("validation_error", "FX loss account is not configured")
                gl.append({"account_id": loss, "debit": str(fx_diff), "credit": "0", "description": "fx"})
            else:
                if not gain:
                    raise AuthAPIError("validation_error", "FX gain account is not configured")
                gl.append({"account_id": gain, "debit": "0", "credit": str(-fx_diff), "description": "fx"})
        posted = post_generated(
            user_id=user_id, org=org, entry_date=pay.entry_date, source_type=JournalEntry.Source.VENDOR_PAYMENT,
            memo="vendor payment", gl_lines=gl, idempotency_key=idempotency_key,
            body={"payment_id": pay.id, "allocations": allocations},
        )
        pay.status = VendorPayment.Status.POSTED
        pay.fx_rate = fx
        pay.journal = posted
        pay.save()
        for bill, amt, base_amt in created:
            BillAllocation.objects.create(
                organization=org, bill=bill, payment=pay, amount=amt, base_amount=base_amt, entry_date=pay.entry_date
            )
        return pay


def refund_vendor_payment(*, user_id, org, payment: VendorPayment, amount, bank_account_id, entry_date, idempotency_key):
    settings = _settings(org)
    if not settings.vendor_advance_account_id:
        raise AuthAPIError("validation_error", "Vendor advance account is not configured")
    amt = Decimal(str(amount))
    if amt <= 0:
        raise AuthAPIError("validation_error", "Refund must be positive")
    with finance_tx(user_id=user_id, organization_id=org.id):
        pay = VendorPayment.objects.select_for_update().filter(pk=payment.pk, organization=org).first()
        if not pay:
            raise AuthAPIError("cross_organization", "Payment not found")
        bank = org_get(Account, org, bank_account_id)
        allocated = BillAllocation.objects.filter(payment=pay).aggregate(s=Sum("amount"))["s"] or Decimal("0")
        refunded = VendorRefund.objects.filter(payment=pay).aggregate(s=Sum("amount"))["s"] or Decimal("0")
        available = pay.amount - allocated - refunded
        if amt > available:
            raise AuthAPIError("over_allocation", "Refund exceeds remaining advance")
        exponent = settings.base_currency.exponent
        base = to_base(amt, pay.fx_rate, exponent)
        posted = post_generated(
            user_id=user_id, org=org, entry_date=entry_date, source_type=JournalEntry.Source.VENDOR_REFUND,
            memo="vendor refund",
            gl_lines=[
                {"account_id": bank.id, "debit": str(base), "credit": "0", "description": "bank"},
                {"account_id": settings.vendor_advance_account_id, "debit": "0", "credit": str(base), "description": "advance"},
            ],
            idempotency_key=idempotency_key,
            body={"payment_id": pay.id, "amount": str(amt)},
        )
        return VendorRefund.objects.create(
            organization=org, payment=pay, amount=amt, entry_date=entry_date,
            bank_account=bank, journal=posted,
        )


def post_expense(*, user_id, org, contact_id, bank_account_id, entry_date, currency_id, fx_rate, lines, idempotency_key):
    from apps.finance.models import Contact

    contact = org_get(Contact, org, contact_id)
    bank = org_get(Account, org, bank_account_id)
    currency = currency_get(currency_id)
    settings = _settings(org)
    exponent = settings.base_currency.exponent
    fx = resolve_rate(org, currency.code, entry_date, settings.base_currency_id, fx_rate)
    gl = []
    total = Decimal("0")
    base_total = Decimal("0")
    prepared = []
    for raw in lines:
        net = Decimal(str(raw.get("net") or 0))
        tax_amt = Decimal(str(raw.get("tax_amount") or 0))
        line_total = net + tax_amt
        base_net = to_base(net, fx, exponent)
        base_tax = to_base(tax_amt, fx, exponent)
        base_line = to_base(line_total, fx, exponent)
        total += line_total
        base_total += base_line
        expense = org_get(Account, org, raw.get("expense_account_id"))
        tax_acct = org_get_optional(Account, org, raw.get("tax_payable_account_id"))
        prepared.append((raw, net, tax_amt, line_total, base_net, base_tax, base_line, expense.id, tax_acct.id if tax_acct else None))
        gl.append({"account_id": expense.id, "debit": str(base_net), "credit": "0", "description": raw.get("description") or "expense"})
        if base_tax and tax_acct:
            gl.append({"account_id": tax_acct.id, "debit": str(base_tax), "credit": "0", "description": "tax"})
    gl.append({"account_id": bank.id, "debit": "0", "credit": str(base_total), "description": "bank"})
    with finance_tx(user_id=user_id, organization_id=org.id):
        posted = post_generated(
            user_id=user_id, org=org, entry_date=entry_date, source_type=JournalEntry.Source.EXPENSE,
            memo="expense", gl_lines=gl, idempotency_key=idempotency_key,
            body={"contact_id": contact.id, "amount": str(total), "lines": lines},
        )
        exp = PaidExpense.objects.create(
            organization=org, contact=contact, bank_account=bank,
            number=next_document_number(org, "expense", "EXP-"),
            entry_date=entry_date, currency=currency, fx_rate=fx,
            total=total, base_total=base_total, journal=posted,
        )
        for raw, net, tax_amt, line_total, base_net, base_tax, base_line, expense_id, tax_id in prepared:
            PaidExpenseLine.objects.create(
                expense=exp, organization=org, description=raw.get("description") or "",
                expense_account_id=expense_id,
                net=net, tax_amount=tax_amt, total=line_total,
                base_net=base_net, base_tax=base_tax, base_total=base_line,
                tax_payable_account_id=tax_id,
            )
        return exp


def convert_po(po: PurchaseOrder) -> Bill:
    if po.status != PurchaseOrder.Status.DRAFT:
        raise AuthAPIError("po_not_convertible", "Purchase order already converted")
    bill = Bill.objects.create(
        organization=po.organization,
        contact=po.contact,
        purchase_order=po,
        entry_date=po.entry_date,
        due_date=po.entry_date,
        currency=po.currency,
        fx_rate=1,
    )
    set_bill_lines(
        bill,
        [
            {
                "item_id": line.item_id,
                "quantity": line.quantity,
                "unit_price": line.unit_price,
                "tax_rate_id": line.tax_rate_id,
                "description": line.description,
            }
            for line in po.lines.all()
        ],
    )
    po.status = PurchaseOrder.Status.CONVERTED
    po.save(update_fields=["status"])
    return bill


def post_payment_run(*, user_id, org, bank_account_id, entry_date, currency_id, items, idempotency_key):
    if not idempotency_key:
        raise AuthAPIError("validation_error", "Idempotency-Key required")
    if not items:
        raise AuthAPIError("validation_error", "Payment run is empty")
    existing = PaymentRun.objects.filter(organization=org, idempotency_key=idempotency_key).first()
    if existing:
        return existing
    grouped = {}
    for raw in items:
        bill = Bill.objects.filter(id=raw.get("bill_id"), organization=org, status=Bill.Status.POSTED).first()
        if not bill:
            raise AuthAPIError("cross_organization", "Bill not found")
        grouped.setdefault(bill.contact_id, []).append({"bill_id": bill.id, "amount": str(raw.get("amount"))})
    with finance_tx(user_id=user_id, organization_id=org.id):
        run = PaymentRun.objects.create(
            organization=org,
            bank_account_id=bank_account_id,
            entry_date=entry_date,
            currency_id=currency_id,
            idempotency_key=idempotency_key,
        )
        for contact_id, allocs in grouped.items():
            amount = sum(Decimal(str(a["amount"])) for a in allocs)
            pay = VendorPayment.objects.create(
                organization=org,
                contact_id=contact_id,
                bank_account_id=bank_account_id,
                entry_date=entry_date,
                currency_id=currency_id,
                amount=amount,
            )
            posted = post_vendor_payment(
                user_id=user_id, org=org, payment=pay, allocations=allocs,
                idempotency_key=f"{idempotency_key}:{contact_id}",
            )
            for alloc in allocs:
                PaymentRunLine.objects.create(
                    payment_run=run, organization=org, bill_id=alloc["bill_id"],
                    amount=alloc["amount"], payment=posted,
                )
        run.status = PaymentRun.Status.POSTED
        run.number = next_document_number(org, "payment_run", "PR-")
        run.save(update_fields=["status", "number"])
        return run


def vendor_statement(*, org, contact_id, start, end):
    from apps.finance.models import Contact

    contact = Contact.objects.filter(id=contact_id, organization=org).first()
    if not contact:
        raise AuthAPIError("cross_organization", "Contact not found")
    items = []
    for bill in Bill.objects.filter(
        organization=org, contact_id=contact_id, status=Bill.Status.POSTED,
        entry_date__gte=start, entry_date__lte=end,
    ):
        items.append(
            {
                "type": "bill", "id": bill.id, "number": bill.number,
                "entry_date": bill.entry_date.isoformat(), "amount": str(bill.total),
                "outstanding": str(outstanding(bill)),
            }
        )
    for pay in VendorPayment.objects.filter(
        organization=org, contact_id=contact_id, status=VendorPayment.Status.POSTED,
        entry_date__gte=start, entry_date__lte=end,
    ):
        items.append(
            {
                "type": "payment", "id": pay.id, "number": "",
                "entry_date": pay.entry_date.isoformat(), "amount": str(pay.amount),
                "outstanding": "0",
            }
        )
    for cred in VendorCredit.objects.filter(
        organization=org, contact_id=contact_id, status=VendorCredit.Status.POSTED,
        entry_date__gte=start, entry_date__lte=end,
    ):
        items.append(
            {
                "type": "credit", "id": cred.id, "number": cred.number,
                "entry_date": cred.entry_date.isoformat(), "amount": str(cred.total),
                "outstanding": "0",
            }
        )
    items.sort(key=lambda row: row["entry_date"])
    return {"contact_id": contact_id, "items": items}

