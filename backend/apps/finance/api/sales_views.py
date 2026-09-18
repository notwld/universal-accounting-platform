from datetime import date

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView

from apps.authentication.exceptions import AuthAPIError, envelope_success
from apps.authentication.permissions.authenticated import IsApplicationUser
from apps.finance.api.views import ORG_HEADER, _org_action
from apps.finance.models import (
    Account,
    Contact,
    CustomerPayment,
    ExchangeRate,
    Invoice,
    Item,
    PaymentTerm,
    Quote,
    QuoteLine,
    TaxRate,
)
from apps.finance.models.config import FinanceCountryPack
from apps.finance.selectors.aging import ar_aging
from apps.finance.services.resolve import currency_get, org_get, org_get_optional
from apps.finance.services.sales import (
    convert_quote,
    create_and_post_credit,
    create_and_post_payment,
    invoice_preview,
    post_invoice,
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
            email=str(request.data.get("email") or "")[:255],
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
            kind=request.data.get("kind") or (Item.Kind.GOOD if request.data.get("tracked") else Item.Kind.SERVICE),
            unit_price=request.data.get("unit_price") or 0,
            income_account=org_get(Account, org, request.data.get("income_account_id")),
            expense_account=org_get_optional(Account, org, request.data.get("expense_account_id")),
            default_tax=org_get_optional(TaxRate, org, request.data.get("tax_rate_id")),
            tracked=bool(request.data.get("tracked")),
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
        kind = request.data.get("kind") or "standard"
        if kind not in ("standard", "reverse_charge", "withholding", "exempt"):
            raise AuthAPIError("validation_error", "Invalid tax kind")
        compound_base = request.data.get("compound_base") or "running"
        if compound_base not in ("net", "running"):
            raise AuthAPIError("validation_error", "compound_base must be net or running")
        t = TaxRate.objects.create(
            organization=org,
            name=request.data.get("name"),
            rate=request.data.get("rate"),
            method=request.data.get("method") or TaxRate.Method.EXCLUSIVE,
            kind=kind,
            payable_account=org_get(Account, org, request.data.get("payable_account_id")),
            recoverable_account=org_get_optional(Account, org, request.data.get("recoverable_account_id")),
            recoverable_rate=request.data.get("recoverable_rate") if request.data.get("recoverable_rate") is not None else 1,
            compound_on=org_get_optional(TaxRate, org, request.data.get("compound_on_id")),
            compound_base=compound_base,
            valid_from=request.data.get("valid_from") or date.today().isoformat(),
            valid_to=request.data.get("valid_to") or None,
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
        from decimal import Decimal

        rate = Decimal(str(request.data.get("rate") or 0))
        if rate <= 0:
            raise AuthAPIError("validation_error", "Exchange rate must be positive")
        r = ExchangeRate.objects.create(
            organization=org,
            currency=currency_get(request.data.get("currency")),
            rate=rate,
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
            contact=org_get(Contact, org, request.data.get("contact_id")),
            entry_date=request.data.get("entry_date"),
            currency=currency_get(request.data.get("currency")),
        )
        for line in request.data.get("lines") or []:
            QuoteLine.objects.create(
                quote=q, organization=org, item=org_get(Item, org, line.get("item_id")),
                description=line.get("description") or "", quantity=line.get("quantity") or 1,
                unit_price=line.get("unit_price"), tax_rate=org_get_optional(TaxRate, org, line.get("tax_rate_id")),
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
        from apps.finance.services.workflow import apply_saved_filter

        qs = apply_saved_filter(
            Invoice.objects.filter(organization=org),
            org=org,
            resource="invoice",
            filter_id=request.query_params.get("saved_filter_id"),
        )
        return envelope_success(request, {"items": [_invoice(i) for i in qs]})

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        user, org = _org_action(request, "finance.invoice.create")
        due = request.data.get("due_date") or request.data.get("entry_date")
        inv = Invoice.objects.create(
            organization=org,
            contact=org_get(Contact, org, request.data.get("contact_id")),
            entry_date=request.data.get("entry_date"),
            due_date=due,
            currency=currency_get(request.data.get("currency")),
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
        posted = create_and_post_credit(
            user_id=user.id, org=org, payload=request.data,
            idempotency_key=request.headers.get("Idempotency-Key"),
        )
        return envelope_success(request, {"id": posted.id, "status": posted.status, "number": posted.number}, http_status=201)


class PaymentListCreateView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        user, org = _org_action(request, "finance.payment.record")
        posted = create_and_post_payment(
            user_id=user.id, org=org, payload=request.data,
            idempotency_key=request.headers.get("Idempotency-Key"),
        )
        return envelope_success(request, {"id": posted.id, "status": posted.status, "amount": str(posted.amount)}, http_status=201)


class RefundCreateView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        user, org = _org_action(request, "finance.payment.record")
        pay = org_get(CustomerPayment, org, request.data.get("payment_id"), "Payment not found")
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
        return envelope_success(request, ar_aging(org=org, as_of=as_of))


def _contact(c):
    return {"id": c.id, "name": c.name, "email": c.email, "is_customer": c.is_customer, "is_vendor": c.is_vendor, "status": c.status}


def _item(i):
    return {
        "id": i.id, "sku": i.sku, "name": i.name, "kind": i.kind, "tracked": i.tracked,
        "unit_price": str(i.unit_price),
        "income_account_id": i.income_account_id, "expense_account_id": i.expense_account_id,
    }


def _tax(t):
    return {
        "id": t.id,
        "name": t.name,
        "rate": str(t.rate),
        "method": t.method,
        "kind": t.kind,
        "payable_account_id": t.payable_account_id,
        "recoverable_account_id": t.recoverable_account_id,
        "recoverable_rate": str(t.recoverable_rate),
        "compound_on_id": t.compound_on_id,
        "compound_base": t.compound_base,
        "valid_from": str(t.valid_from),
        "valid_to": None if not t.valid_to else str(t.valid_to),
    }


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
                "tax_kind": ln.tax_kind, "tax_components": ln.tax_components,
            }
            for ln in inv.lines.all()
        ],
    }


class CountryPackListView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request):
        _, org = _org_action(request, "finance.settings.configure")
        from apps.finance.services.country import catalog

        enabled = {
            p.country_code: {"enabled": p.enabled, "reviewed_at": None if not p.reviewed_at else p.reviewed_at.isoformat()}
            for p in FinanceCountryPack.objects.filter(organization=org)
        }
        items = []
        for row in catalog():
            extra = enabled.get(row["code"], {"enabled": False, "reviewed_at": None})
            items.append({**row, **extra})
        return envelope_success(request, {"items": items})

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        user, org = _org_action(request, "finance.settings.configure")
        from apps.finance.services.country import PACKS

        code = str(request.data.get("country_code") or "").strip().lower()
        if code not in PACKS:
            raise AuthAPIError("validation_error", "Unknown country pack")
        if not request.data.get("reviewed"):
            raise AuthAPIError("validation_error", "Accountant review is required to enable a country pack")
        pack, _ = FinanceCountryPack.objects.update_or_create(
            organization=org,
            country_code=code,
            defaults={
                "enabled": True,
                "reviewed_at": timezone.now(),
                "reviewed_by": user.id,
                "capabilities": PACKS[code],
            },
        )
        return envelope_success(
            request,
            {"country_code": pack.country_code, "enabled": pack.enabled, "reviewed_at": pack.reviewed_at.isoformat()},
            http_status=201,
        )
