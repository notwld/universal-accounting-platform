from datetime import date

from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView

from apps.authentication.exceptions import envelope_success
from apps.authentication.permissions.authenticated import IsApplicationUser
from apps.finance.api.views import ORG_HEADER, _org_action
from apps.finance.models import Reminder, ReminderRule
from apps.finance.services.reminders import create_rule, run_reminders


class ReminderRuleListCreateView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request):
        _, org = _org_action(request, "finance.journal.read")
        items = [
            {"id": r.id, "document_kind": r.document_kind, "days_before_due": r.days_before_due, "active": r.active}
            for r in ReminderRule.objects.filter(organization=org)
        ]
        return envelope_success(request, {"items": items})

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        user, org = _org_action(request, "finance.settings.configure")
        rule = create_rule(user_id=user.id, org=org, payload=request.data)
        return envelope_success(
            request,
            {"id": rule.id, "document_kind": rule.document_kind, "days_before_due": rule.days_before_due},
            http_status=201,
        )


class ReminderListView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request):
        _, org = _org_action(request, "finance.journal.read")
        items = [
            {
                "id": r.id, "object_type": r.object_type, "object_id": r.object_id,
                "due_date": r.due_date.isoformat() if not isinstance(r.due_date, str) else r.due_date,
                "as_of": r.as_of.isoformat() if not isinstance(r.as_of, str) else r.as_of,
            }
            for r in Reminder.objects.filter(organization=org)
        ]
        return envelope_success(request, {"items": items})


class ReminderRunView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        user, org = _org_action(request, "finance.journal.read")
        as_of = request.data.get("as_of") or date.today().isoformat()
        created = run_reminders(user_id=user.id, org=org, as_of=date.fromisoformat(str(as_of)[:10]))
        return envelope_success(
            request,
            {
                "created": [
                    {"id": r.id, "object_id": r.object_id, "emailed": bool(r.emailed_at)} for r in created
                ]
            },
        )
