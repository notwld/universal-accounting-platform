from django.http import FileResponse
from drf_spectacular.utils import extend_schema
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.views import APIView

from apps.authentication.exceptions import AuthAPIError, envelope_success
from apps.authentication.permissions.authenticated import IsApplicationUser
from apps.finance.api.views import ORG_HEADER, _org_action
from apps.finance.models import (
    Bill,
    Contact,
    CreditNote,
    FinanceAttachment,
    Invoice,
    Item,
    PaidExpense,
    PaymentRun,
    PurchaseOrder,
    PurchaseOrderLine,
    TaxRate,
    VendorCredit,
    VendorPayment,
)
from apps.finance.models.attachments import ALLOWED_TYPES, MAX_BYTES
from apps.finance.selectors.aging import ap_aging
from apps.finance.services.purchases import (
    bill_preview,
    convert_po,
    create_and_post_vendor_credit,
    create_and_post_vendor_payment,
    post_bill,
    post_expense,
    post_payment_run,
    refund_vendor_payment,
    set_bill_lines,
    vendor_statement,
)
from apps.finance.services.resolve import currency_get, org_get, org_get_optional


class BillListCreateView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request):
        _, org = _org_action(request, "finance.bill.create")
        from apps.finance.services.workflow import apply_saved_filter

        qs = apply_saved_filter(
            Bill.objects.filter(organization=org),
            org=org,
            resource="bill",
            filter_id=request.query_params.get("saved_filter_id"),
        )
        return envelope_success(request, {"items": [_bill(b) for b in qs]})

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        user, org = _org_action(request, "finance.bill.create")
        due = request.data.get("due_date") or request.data.get("entry_date")
        bill = Bill.objects.create(
            organization=org,
            contact=org_get(Contact, org, request.data.get("contact_id")),
            entry_date=request.data.get("entry_date"),
            due_date=due,
            currency=currency_get(request.data.get("currency")),
            fx_rate=request.data.get("fx_rate") or 1,
            created_by=user.id,
        )
        set_bill_lines(bill, request.data.get("lines") or [])
        return envelope_success(request, _bill(bill), http_status=201)


class BillPreviewView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request, bill_id: str):
        _, org = _org_action(request, "finance.bill.create")
        bill = Bill.objects.filter(id=bill_id, organization=org).first()
        if not bill:
            raise AuthAPIError("cross_organization", "Bill not found")
        return envelope_success(request, {"lines": bill_preview(bill)})


class BillPostView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request, bill_id: str):
        user, org = _org_action(request, "finance.document.post")
        bill = Bill.objects.filter(id=bill_id, organization=org).first()
        if not bill:
            raise AuthAPIError("cross_organization", "Bill not found")
        posted = post_bill(
            user_id=user.id, org=org, bill=bill,
            idempotency_key=request.headers.get("Idempotency-Key"),
        )
        return envelope_success(request, _bill(posted))


class BillSubmitView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request, bill_id: str):
        user, org = _org_action(request, "finance.bill.create")
        from apps.finance.services.approvals import submit_document
        return envelope_success(request, _bill(submit_document(user_id=user.id, org=org, model=Bill, doc_id=bill_id)))


class BillApproveView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request, bill_id: str):
        user, org = _org_action(request, "finance.document.approve")
        from apps.finance.services.approvals import approve_document
        return envelope_success(request, _bill(approve_document(user_id=user.id, org=org, model=Bill, doc_id=bill_id)))


class BillRejectView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request, bill_id: str):
        user, org = _org_action(request, "finance.document.approve")
        from apps.finance.services.approvals import reject_document
        return envelope_success(
            request,
            _bill(reject_document(user_id=user.id, org=org, model=Bill, doc_id=bill_id, reason=request.data.get("reason"))),
        )


class VendorCreditCreateView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        user, org = _org_action(request, "finance.document.post")
        posted = create_and_post_vendor_credit(
            user_id=user.id, org=org, payload=request.data,
            idempotency_key=request.headers.get("Idempotency-Key"),
        )
        return envelope_success(request, {"id": posted.id, "status": posted.status, "number": posted.number}, http_status=201)


class VendorPaymentCreateView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        user, org = _org_action(request, "finance.payment.record")
        posted = create_and_post_vendor_payment(
            user_id=user.id, org=org, payload=request.data,
            idempotency_key=request.headers.get("Idempotency-Key"),
        )
        return envelope_success(request, {"id": posted.id, "status": posted.status, "amount": str(posted.amount)}, http_status=201)


class VendorRefundCreateView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        user, org = _org_action(request, "finance.payment.record")
        pay = org_get(VendorPayment, org, request.data.get("payment_id"), "Payment not found")
        ref = refund_vendor_payment(
            user_id=user.id, org=org, payment=pay, amount=request.data.get("amount"),
            bank_account_id=request.data.get("bank_account_id"),
            entry_date=request.data.get("entry_date"),
            idempotency_key=request.headers.get("Idempotency-Key"),
        )
        return envelope_success(request, {"id": ref.id, "amount": str(ref.amount)}, http_status=201)


class ExpenseCreateView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        user, org = _org_action(request, "finance.payment.record")
        exp = post_expense(
            user_id=user.id, org=org,
            contact_id=request.data.get("contact_id"),
            bank_account_id=request.data.get("bank_account_id"),
            entry_date=request.data.get("entry_date"),
            currency_id=request.data.get("currency"),
            fx_rate=request.data.get("fx_rate") or 1,
            lines=request.data.get("lines") or [],
            idempotency_key=request.headers.get("Idempotency-Key"),
        )
        return envelope_success(
            request,
            {"id": exp.id, "number": exp.number, "total": str(exp.total), "journal_id": exp.journal_id},
            http_status=201,
        )


class APAgingView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request):
        _, org = _org_action(request, "finance.report.view")
        as_of = request.query_params.get("as_of")
        if not as_of:
            raise AuthAPIError("validation_error", "as_of is required")
        return envelope_success(request, ap_aging(org=org, as_of=as_of))


class PurchaseOrderListCreateView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request):
        _, org = _org_action(request, "finance.bill.create")
        rows = PurchaseOrder.objects.filter(organization=org)
        return envelope_success(request, {"items": [_po(p) for p in rows]})

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        _, org = _org_action(request, "finance.bill.create")
        po = PurchaseOrder.objects.create(
            organization=org,
            contact=org_get(Contact, org, request.data.get("contact_id")),
            entry_date=request.data.get("entry_date"),
            currency=currency_get(request.data.get("currency")),
        )
        for line in request.data.get("lines") or []:
            PurchaseOrderLine.objects.create(
                purchase_order=po, organization=org, item=org_get(Item, org, line.get("item_id")),
                description=line.get("description") or "", quantity=line.get("quantity") or 1,
                unit_price=line.get("unit_price"), tax_rate=org_get_optional(TaxRate, org, line.get("tax_rate_id")),
            )
        return envelope_success(request, _po(po), http_status=201)


class PurchaseOrderConvertView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request, po_id: str):
        _, org = _org_action(request, "finance.bill.create")
        po = PurchaseOrder.objects.filter(id=po_id, organization=org).first()
        if not po:
            raise AuthAPIError("cross_organization", "Purchase order not found")
        return envelope_success(request, _bill(convert_po(po)), http_status=201)


class PaymentRunCreateView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        user, org = _org_action(request, "finance.payment.record")
        run = post_payment_run(
            user_id=user.id, org=org,
            bank_account_id=request.data.get("bank_account_id"),
            entry_date=request.data.get("entry_date"),
            currency_id=request.data.get("currency"),
            items=request.data.get("items") or [],
            idempotency_key=request.headers.get("Idempotency-Key"),
        )
        return envelope_success(
            request,
            {"id": run.id, "status": run.status, "number": run.number},
            http_status=201,
        )


class VendorStatementView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request, contact_id: str):
        _, org = _org_action(request, "finance.report.view")
        start = request.query_params.get("from")
        end = request.query_params.get("to")
        if not start or not end:
            raise AuthAPIError("validation_error", "from and to are required")
        return envelope_success(request, vendor_statement(org=org, contact_id=contact_id, start=start, end=end))


class AttachmentListCreateView(APIView):
    permission_classes = [IsApplicationUser]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request):
        _, org = _org_action(request, "finance.journal.read")
        qs = FinanceAttachment.objects.filter(organization=org)
        object_type = request.query_params.get("object_type")
        object_id = request.query_params.get("object_id")
        if object_type:
            qs = qs.filter(object_type=object_type)
        if object_id:
            qs = qs.filter(object_id=object_id)
        return envelope_success(request, {"items": [_attachment(a) for a in qs]})

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        user, org = _org_action(request, "finance.journal.read")
        object_type = request.data.get("object_type")
        object_id = request.data.get("object_id")
        uploaded = request.FILES.get("file")
        if not uploaded:
            raise AuthAPIError("validation_error", "file is required")
        _require_host(org, object_type, object_id)
        content_type = uploaded.content_type or ""
        if content_type not in ALLOWED_TYPES:
            raise AuthAPIError("validation_error", "File type is not allowed")
        head = uploaded.read(16)
        uploaded.seek(0)
        sniffed = ""
        if head.startswith(b"%PDF"):
            sniffed = "application/pdf"
        elif head.startswith(b"\x89PNG"):
            sniffed = "image/png"
        elif head.startswith(b"\xff\xd8"):
            sniffed = "image/jpeg"
        elif head.startswith(b"RIFF") and b"WEBP" in head:
            sniffed = "image/webp"
        if sniffed != content_type:
            raise AuthAPIError("validation_error", "File type is not allowed")
        if uploaded.size > MAX_BYTES:
            raise AuthAPIError("validation_error", "File is too large")
        att = FinanceAttachment(
            organization=org,
            object_type=object_type,
            object_id=object_id,
            original_name=uploaded.name[:255],
            content_type=content_type,
            size=uploaded.size,
            uploaded_by=user.id,
        )
        att.file = uploaded
        att.save()
        return envelope_success(request, _attachment(att), http_status=201)


class AttachmentDownloadView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request, attachment_id: str):
        _, org = _org_action(request, "finance.journal.read")
        att = FinanceAttachment.objects.filter(id=attachment_id, organization=org).first()
        if not att:
            raise AuthAPIError("cross_organization", "Attachment not found")
        return FileResponse(att.file.open("rb"), as_attachment=True, filename=att.original_name)


def _require_host(org, object_type, object_id):
    models = {
        "invoice": Invoice,
        "bill": Bill,
        "purchase_order": PurchaseOrder,
        "expense": PaidExpense,
        "credit_note": CreditNote,
        "vendor_credit": VendorCredit,
    }
    model = models.get(object_type)
    if not model:
        raise AuthAPIError("validation_error", "Unknown attachment target")
    if not model.objects.filter(id=object_id, organization=org).exists():
        raise AuthAPIError("cross_organization", "Document not found")


def _attachment(a):
    return {
        "id": a.id, "object_type": a.object_type, "object_id": a.object_id,
        "original_name": a.original_name, "content_type": a.content_type, "size": a.size,
    }


def _po(po):
    po = PurchaseOrder.objects.prefetch_related("lines").get(pk=po.pk)
    return {
        "id": po.id, "status": po.status, "contact_id": po.contact_id, "currency": po.currency_id,
        "lines": [{"item_id": ln.item_id, "quantity": str(ln.quantity), "unit_price": str(ln.unit_price)} for ln in po.lines.all()],
    }


def _bill(bill):
    bill = Bill.objects.prefetch_related("lines").get(pk=bill.pk)
    return {
        "id": bill.id, "status": bill.status, "number": bill.number, "contact_id": bill.contact_id,
        "contact_name": bill.contact_name, "total": str(bill.total), "base_total": str(bill.base_total),
        "currency": bill.currency_id, "fx_rate": str(bill.fx_rate), "journal_id": bill.journal_id,
        "lines": [
            {
                "description": ln.description, "net": str(ln.net), "tax_amount": str(ln.tax_amount),
                "total": str(ln.total), "tax_rate_value": str(ln.tax_rate_value), "tax_name": ln.tax_name,
                "tax_kind": ln.tax_kind, "tax_components": ln.tax_components,
            }
            for ln in bill.lines.all()
        ],
    }
