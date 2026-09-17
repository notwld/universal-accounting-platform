from datetime import date

from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView

from apps.authentication.exceptions import AuthAPIError, envelope_success
from apps.authentication.permissions.authenticated import IsApplicationUser
from apps.finance.api.views import ORG_HEADER, _org_action
from apps.finance.models import RecurringSchedule
from apps.finance.services.access import require_permission
from apps.finance.services.recurring import (
    KIND_ACTION,
    allowed_kinds,
    create_schedule,
    run_due,
    set_status,
)


def _payload(sched: RecurringSchedule):
    return {
        "id": sched.id,
        "kind": sched.kind,
        "status": sched.status,
        "contact_id": sched.contact_id,
        "currency": sched.currency_id,
        "day_of_month": sched.day_of_month,
        "weekday": sched.weekday,
        "month_of_year": sched.month_of_year,
        "frequency": sched.frequency,
        "auto_post": sched.auto_post,
        "start_on": sched.start_on.isoformat() if not isinstance(sched.start_on, str) else sched.start_on,
        "next_on": sched.next_on.isoformat() if not isinstance(sched.next_on, str) else sched.next_on,
        "end_on": None if not sched.end_on else (sched.end_on if isinstance(sched.end_on, str) else sched.end_on.isoformat()),
        "bank_account_id": sched.bank_account_id,
    }


class RecurringListCreateView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request):
        user, org = _org_action(request, "finance.journal.read")
        kinds = allowed_kinds(user.id, org.id)
        qs = RecurringSchedule.objects.filter(organization=org)
        if kinds:
            qs = qs.filter(kind__in=kinds)
        else:
            qs = qs.none()
        return envelope_success(request, {"items": [_payload(s) for s in qs]})

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        user, org = _org_action(request, "finance.journal.read")
        kind = request.data.get("kind")
        action = KIND_ACTION.get(kind)
        if not action:
            raise AuthAPIError("validation_error", "kind must be invoice, bill, or expense")
        require_permission(user.id, org.id, action)
        sched = create_schedule(user_id=user.id, org=org, payload=request.data)
        return envelope_success(request, _payload(sched), http_status=201)


class RecurringPauseView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request, schedule_id: str):
        user, org = _org_action(request, "finance.journal.read")
        sched = RecurringSchedule.objects.filter(id=schedule_id, organization=org).first()
        if not sched:
            raise AuthAPIError("cross_organization", "Schedule not found")
        require_permission(user.id, org.id, KIND_ACTION[sched.kind])
        return envelope_success(
            request, _payload(set_status(user_id=user.id, org=org, schedule_id=schedule_id, status=RecurringSchedule.Status.PAUSED))
        )


class RecurringResumeView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request, schedule_id: str):
        user, org = _org_action(request, "finance.journal.read")
        sched = RecurringSchedule.objects.filter(id=schedule_id, organization=org).first()
        if not sched:
            raise AuthAPIError("cross_organization", "Schedule not found")
        require_permission(user.id, org.id, KIND_ACTION[sched.kind])
        return envelope_success(
            request, _payload(set_status(user_id=user.id, org=org, schedule_id=schedule_id, status=RecurringSchedule.Status.ACTIVE))
        )


class RecurringRunView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        user, org = _org_action(request, "finance.journal.read")
        kinds = allowed_kinds(user.id, org.id)
        as_of = request.data.get("as_of") or date.today().isoformat()
        created = run_due(user_id=user.id, org=org, as_of=date.fromisoformat(str(as_of)[:10]), kinds=kinds)
        return envelope_success(
            request,
            {
                "created": [
                    {
                        "id": occ.id,
                        "occurs_on": occ.occurs_on.isoformat() if not isinstance(occ.occurs_on, str) else occ.occurs_on,
                        "invoice_id": occ.invoice_id,
                        "bill_id": occ.bill_id,
                        "expense_id": occ.expense_id,
                    }
                    for occ in created
                ]
            },
        )
