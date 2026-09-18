from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView

from apps.authentication.exceptions import AuthAPIError, envelope_success
from apps.authentication.permissions.authenticated import IsApplicationUser
from apps.finance.api.views import ORG_HEADER, _org_action
from apps.finance.models import FinanceWebhookDelivery, FinanceWebhookEndpoint
from apps.finance.services.adjustments import post_adjustment, reverse_due
from apps.finance.services.cutover import run_cutover
from apps.finance.services.fx import revalue
from apps.finance.services.webhooks import create_endpoint, deliver_due


class AdjustmentCreateView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        user, org = _org_action(request, "finance.journal.post")
        adj = post_adjustment(
            user_id=user.id,
            org=org,
            payload=request.data,
            idempotency_key=request.headers.get("Idempotency-Key") or "",
        )
        return envelope_success(
            request,
            {"id": adj.id, "journal_id": adj.journal_id, "kind": adj.kind, "amount": str(adj.amount)},
            http_status=201,
        )


class AdjustmentReverseView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        user, org = _org_action(request, "finance.journal.reverse")
        as_of = request.data.get("as_of")
        if not as_of:
            raise AuthAPIError("validation_error", "as_of is required")
        ids = reverse_due(
            user_id=user.id,
            org=org,
            as_of=as_of,
            idempotency_key=request.headers.get("Idempotency-Key") or f"adj-rev:{as_of}",
        )
        return envelope_success(request, {"reversed": ids})


class FxRevalueView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        user, org = _org_action(request, "finance.journal.post")
        as_of = request.data.get("as_of")
        if not as_of:
            raise AuthAPIError("validation_error", "as_of is required")
        row = revalue(
            user_id=user.id,
            org=org,
            as_of=as_of,
            idempotency_key=request.headers.get("Idempotency-Key") or "",
        )
        return envelope_success(
            request,
            {"id": row.id, "as_of": str(row.as_of)[:10], "amount": str(row.amount), "journal_id": row.journal_id},
        )


class CutoverView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        user, org = _org_action(request, "finance.settings.configure")
        result = run_cutover(
            user_id=user.id,
            org=org,
            mode=request.data.get("mode") or "",
            stage=request.data.get("stage") or "",
            dry_run=str(request.data.get("dry_run") or "").lower() in ("1", "true", "yes"),
            rows=request.data.get("rows") or [],
        )
        return envelope_success(request, result, http_status=200 if result["dry_run"] else 201)


class WebhookListCreateView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request):
        _, org = _org_action(request, "finance.settings.configure")
        items = [
            {"id": e.id, "url": e.url, "enabled": e.enabled, "events": e.events}
            for e in FinanceWebhookEndpoint.objects.filter(organization=org)
        ]
        return envelope_success(request, {"items": items})

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        _, org = _org_action(request, "finance.settings.configure")
        ep = create_endpoint(
            org=org, url=request.data.get("url"), events=request.data.get("events") or [], secret=request.data.get("secret") or ""
        )
        return envelope_success(request, {"id": ep.id, "url": ep.url, "secret": ep.secret, "events": ep.events}, http_status=201)


class WebhookDeliverView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        _, org = _org_action(request, "finance.settings.configure")
        return envelope_success(request, {"items": deliver_due(org=org)})


class OpsMetricsView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request):
        _, org = _org_action(request, "finance.report.view")
        qs = FinanceWebhookDelivery.objects.filter(organization=org)
        return envelope_success(
            request,
            {
                "as_of": timezone.now().isoformat(),
                "webhooks_pending": qs.filter(status=FinanceWebhookDelivery.Status.PENDING).count(),
                "webhooks_dead": qs.filter(status=FinanceWebhookDelivery.Status.DEAD).count(),
            },
        )
