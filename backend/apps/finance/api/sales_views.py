from datetime import date

from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView

from apps.authentication.exceptions import AuthAPIError, envelope_success
from apps.authentication.permissions.authenticated import IsApplicationUser
from apps.finance.api.views import ORG_HEADER, _org_action
from apps.finance.models import (
    Contact,
    CreditNote,
    CreditNoteLine,
    CustomerPayment,
    ExchangeRate,
    Invoice,
    Item,
    PaymentTerm,
    Quote,
    QuoteLine,
    TaxRate,
)
from apps.finance.selectors.aging import ar_aging
from apps.finance.services.sales import (
    convert_quote,
    invoice_preview,
    post_credit,
    post_invoice,
    post_payment,
    refund_payment,
    set_invoice_lines,
)


class ContactListCreateView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request):
        _, org = _org_action(request, "finance.invoice.create")
        items = Contact.objects.filter(organization=org)
        return envelope_success(request, {"items": [_contact(c) for c in items]})

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        _, org = _org_action(request, "finance.contact.maintain")
        c = Contact.objects.create(
            organization=org,
            name=request.data.get("name"),
            is_customer=bool(request.data.get("is_customer", not request.data.get("is_vendor"))),
            is_vendor=bool(request.data.get("is_vendor")),
        )
        return envelope_success(request, _contact(c), http_status=201)


class ItemListCreateView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request):
        _, org = _org_action(request, "finance.invoice.create")
        return envelope_success(request, {"items": [_item(i) for i in Item.objects.filter(organization=org)]})

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        _, org = _org_action(request, "finance.item.maintain")
        i = Item.objects.create(
            organization=org,
            sku=request.data.get("sku"),
            name=request.data.get("name"),
            kind=request.data.get("kind") or Item.Kind.SERVICE,
            unit_price=request.data.get("unit_price") or 0,
            income_account_id=request.data.get("income_account_id"),
            expense_account_id=request.data.get("expense_account_id"),
            default_tax_id=request.data.get("tax_rate_id"),
        )
        return envelope_success(request, _item(i), http_status=201)


class TaxRateListCreateView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request):
        _, org = _org_action(request, "finance.invoice.create")
        return envelope_success(request, {"items": [_tax(t) for t in TaxRate.objects.filter(organization=org)]})

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        _, org = _org_action(request, "finance.settings.configure")
        t = TaxRate.objects.create(
            organization=org,
            name=request.data.get("name"),
            rate=request.data.get("rate"),
            method=request.data.get("method") or TaxRate.Method.EXCLUSIVE,
            payable_account_id=request.data.get("payable_account_id"),
            valid_from=request.data.get("valid_from") or date.today().isoformat(),
        )
        return envelope_success(request, _tax(t), http_status=201)


class PaymentTermListCreateView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request):
        _, org = _org_action(request, "finance.invoice.create")
        return envelope_success(
            request, {"items": [{"id": t.id, "name": t.name, "days": t.days} for t in PaymentTerm.objects.filter(organization=org)]}
        )

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        _, org = _org_action(request, "finance.settings.configure")
        t = PaymentTerm.objects.create(
            organization=org, name=request.data.get("name"), days=int(request.data.get("days") or 0)
        )
        return envelope_success(request, {"id": t.id, "name": t.name, "days": t.days}, http_status=201)


class ExchangeRateListCreateView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request):
        _, org = _org_action(request, "finance.invoice.create")
        rows = ExchangeRate.objects.filter(organization=org)
        return envelope_success(
            request,
            {"items": [{"id": r.id, "currency": r.currency_id, "rate": str(r.rate), "as_of": str(r.as_of)[:10]} for r in rows]},
        )

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        _, org = _org_action(request, "finance.settings.configure")
        r = ExchangeRate.objects.create(
            organization=org,
            currency_id=request.data.get("currency"),
            rate=request.data.get("rate"),
            as_of=request.data.get("as_of"),
        )
        return envelope_success(
            request, {"id": r.id, "currency": r.currency_id, "rate": str(r.rate), "as_of": str(r.as_of)[:10]}, http_status=201
        )


class QuoteListCreateView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request):
        _, org = _org_action(request, "finance.invoice.create")
        return envelope_success(request, {"items": [_quote(q) for q in Quote.objects.filter(organization=org)]})

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        _, org = _org_action(request, "finance.invoice.create")
        q = Quote.objects.create(
            organization=org,
            contact_id=request.data.get("contact_id"),
            entry_date=request.data.get("entry_date"),
            currency_id=request.data.get("currency"),
        )
        for line in request.data.get("lines") or []:
            QuoteLine.objects.create(
                quote=q, organization=org, item_id=line.get("item_id"),
                description=line.get("description") or "", quantity=line.get("quantity") or 1,
                unit_price=line.get("unit_price"), tax_rate_id=line.get("tax_rate_id"),
            )
        return envelope_success(request, _quote(q), http_status=201)


class QuoteConvertView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request, quote_id: str):
        _, org = _org_action(request, "finance.invoice.create")
        q = Quote.objects.filter(id=quote_id, organization=org).first()
        if not q:
            raise AuthAPIError("cross_organization", "Quote not found")
        return envelope_success(request, _invoice(convert_quote(q)), http_status=201)


class InvoiceListCreateView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request):
        _, org = _org_action(request, "finance.invoice.create")
        return envelope_success(request, {"items": [_invoice(i) for i in Invoice.objects.filter(organization=org)]})

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        user, org = _org_action(request, "finance.invoice.create")
        due = request.data.get("due_date") or request.data.get("entry_date")
        inv = Invoice.objects.create(
            organization=org,
            contact_id=request.data.get("contact_id"),
            entry_date=request.data.get("entry_date"),
            due_date=due,
            currency_id=request.data.get("currency"),
            fx_rate=request.data.get("fx_rate") or 1,
            created_by=user.id,
        )
        set_invoice_lines(inv, request.data.get("lines") or [])
        return envelope_success(request, _invoice(inv), http_status=201)


class InvoicePreviewView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request, invoice_id: str):
        _, org = _org_action(request, "finance.invoice.create")
        inv = Invoice.objects.filter(id=invoice_id, organization=org).first()
        if not inv:
            raise AuthAPIError("cross_organization", "Invoice not found")
        return envelope_success(request, {"lines": invoice_preview(inv)})


class InvoicePostView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request, invoice_id: str):
        user, org = _org_action(request, "finance.document.post")
        inv = Invoice.objects.filter(id=invoice_id, organization=org).first()
        if not inv:
            raise AuthAPIError("cross_organization", "Invoice not found")
        posted = post_invoice(
            user_id=user.id, org=org, invoice=inv,
            idempotency_key=request.headers.get("Idempotency-Key"),
        )
        return envelope_success(request, _invoice(posted))


class InvoiceSubmitView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request, invoice_id: str):
        user, org = _org_action(request, "finance.invoice.create")
        from apps.finance.services.approvals import submit_document
        return envelope_success(request, _invoice(submit_document(user_id=user.id, org=org, model=Invoice, doc_id=invoice_id)))


class InvoiceApproveView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request, invoice_id: str):
        user, org = _org_action(request, "finance.document.approve")
        from apps.finance.services.approvals import approve_document
        return envelope_success(request, _invoice(approve_document(user_id=user.id, org=org, model=Invoice, doc_id=invoice_id)))


class InvoiceRejectView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request, invoice_id: str):
        user, org = _org_action(request, "finance.document.approve")
        from apps.finance.services.approvals import reject_document
        return envelope_success(
            request,
            _invoice(reject_document(user_id=user.id, org=org, model=Invoice, doc_id=invoice_id, reason=request.data.get("reason"))),
        )


class CreditNoteListCreateView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        user, org = _org_action(request, "finance.document.post")
        cn = CreditNote.objects.create(
            organization=org,
            contact_id=request.data.get("contact_id"),
            invoice_id=request.data.get("invoice_id"),
            entry_date=request.data.get("entry_date"),
            currency_id=request.data.get("currency"),
            fx_rate=request.data.get("fx_rate") or 1,
            total=request.data.get("total") or 0,
            base_total=request.data.get("base_total") or 0,
        )
        for line in request.data.get("lines") or []:
            CreditNoteLine.objects.create(
                credit_note=cn, organization=org,
                description=line.get("description") or "",
                income_account_id=line.get("income_account_id"),
                net=line.get("net") or 0, tax_amount=line.get("tax_amount") or 0,
                total=line.get("total") or 0, base_net=line.get("base_net") or 0,
                base_tax=line.get("base_tax") or 0, base_total=line.get("base_total") or 0,
                tax_payable_account_id=line.get("tax_payable_account_id"),
            )
        posted = post_credit(
            user_id=user.id, org=org, credit=cn,
            idempotency_key=request.headers.get("Idempotency-Key"),
        )
        return envelope_success(request, {"id": posted.id, "status": posted.status, "number": posted.number}, http_status=201)


class PaymentListCreateView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        user, org = _org_action(request, "finance.payment.record")
        pay = CustomerPayment.objects.create(
            organization=org,
            contact_id=request.data.get("contact_id"),
            bank_account_id=request.data.get("bank_account_id"),
            entry_date=request.data.get("entry_date"),
            currency_id=request.data.get("currency"),
            fx_rate=request.data.get("fx_rate") or 1,
            amount=request.data.get("amount"),
        )
        posted = post_payment(
            user_id=user.id, org=org, payment=pay,
            allocations=request.data.get("allocations") or [],
            idempotency_key=request.headers.get("Idempotency-Key"),
        )
        return envelope_success(request, {"id": posted.id, "status": posted.status, "amount": str(posted.amount)}, http_status=201)


class RefundCreateView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        user, org = _org_action(request, "finance.payment.record")
        pay = CustomerPayment.objects.filter(id=request.data.get("payment_id"), organization=org).first()
        if not pay:
            raise AuthAPIError("cross_organization", "Payment not found")
        ref = refund_payment(
            user_id=user.id, org=org, payment=pay, amount=request.data.get("amount"),
            bank_account_id=request.data.get("bank_account_id"),
            entry_date=request.data.get("entry_date"),
            idempotency_key=request.headers.get("Idempotency-Key"),
        )
        return envelope_success(request, {"id": ref.id, "amount": str(ref.amount)}, http_status=201)


class ARAgingView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request):
        _, org = _org_action(request, "finance.report.view")
        as_of = request.query_params.get("as_of")
        if not as_of:
            raise AuthAPIError("validation_error", "as_of is required")
        return envelope_success(request, {"items": ar_aging(org=org, as_of=as_of)})


def _contact(c):
    return {"id": c.id, "name": c.name, "is_customer": c.is_customer, "is_vendor": c.is_vendor, "status": c.status}


def _item(i):
    return {
        "id": i.id, "sku": i.sku, "name": i.name, "unit_price": str(i.unit_price),
        "income_account_id": i.income_account_id, "expense_account_id": i.expense_account_id,
    }


def _tax(t):
    return {"id": t.id, "name": t.name, "rate": str(t.rate), "method": t.method}


def _quote(q):
    q = Quote.objects.prefetch_related("lines").get(pk=q.pk)
    return {
        "id": q.id, "status": q.status, "contact_id": q.contact_id, "currency": q.currency_id,
        "lines": [{"item_id": ln.item_id, "quantity": str(ln.quantity), "unit_price": str(ln.unit_price)} for ln in q.lines.all()],
    }


def _invoice(inv):
    inv = Invoice.objects.prefetch_related("lines").get(pk=inv.pk)
    return {
        "id": inv.id, "status": inv.status, "number": inv.number, "contact_id": inv.contact_id,
        "contact_name": inv.contact_name, "total": str(inv.total), "base_total": str(inv.base_total),
        "currency": inv.currency_id, "fx_rate": str(inv.fx_rate), "journal_id": inv.journal_id,
        "lines": [
            {
                "description": ln.description, "net": str(ln.net), "tax_amount": str(ln.tax_amount),
                "total": str(ln.total), "tax_rate_value": str(ln.tax_rate_value), "tax_name": ln.tax_name,
            }
            for ln in inv.lines.all()
        ],
    }
