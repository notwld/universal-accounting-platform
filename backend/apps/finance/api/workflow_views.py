from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView

from apps.authentication.exceptions import AuthAPIError, envelope_success
from apps.authentication.permissions.authenticated import IsApplicationUser
from apps.finance.api.views import ORG_HEADER, _org_action
from apps.finance.models import FinanceException, ReportingTag, SavedFilter
from apps.finance.services.workflow import create_saved_filter, resolve_exception


class SavedFilterListCreateView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request):
        _, org = _org_action(request, "finance.journal.read")
        items = [
            {"id": f.id, "name": f.name, "resource": f.resource, "params": f.params}
            for f in SavedFilter.objects.filter(organization=org)
        ]
        return envelope_success(request, {"items": items})

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        user, org = _org_action(request, "finance.settings.configure")
        row = create_saved_filter(user_id=user.id, org=org, payload=request.data)
        return envelope_success(
            request,
            {"id": row.id, "name": row.name, "resource": row.resource, "params": row.params},
            http_status=201,
        )


class TagListCreateView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request):
        _, org = _org_action(request, "finance.journal.read")
        items = [{"id": t.id, "name": t.name} for t in ReportingTag.objects.filter(organization=org)]
        return envelope_success(request, {"items": items})

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        _, org = _org_action(request, "finance.settings.configure")
        name = (request.data.get("name") or "").strip()
        if not name:
            raise AuthAPIError("validation_error", "Name is required")
        tag, _ = ReportingTag.objects.get_or_create(organization=org, name=name[:100])
        return envelope_success(request, {"id": tag.id, "name": tag.name}, http_status=201)


class ExceptionListView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request):
        _, org = _org_action(request, "finance.journal.read")
        qs = FinanceException.objects.filter(organization=org)
        status = request.query_params.get("status")
        if status:
            qs = qs.filter(status=status)
        items = [
            {
                "id": e.id,
                "kind": e.kind,
                "object_type": e.object_type,
                "object_id": e.object_id,
                "reason": e.reason,
                "status": e.status,
            }
            for e in qs.order_by("-created_at")
        ]
        return envelope_success(request, {"items": items})


class ExceptionResolveView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request, exception_id: str):
        user, org = _org_action(request, "finance.settings.configure")
        row = resolve_exception(
            user_id=user.id, org=org, exception_id=exception_id, reason=request.data.get("reason")
        )
        return envelope_success(request, {"id": row.id, "status": row.status, "reason": row.reason})
