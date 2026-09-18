from datetime import date

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.views import APIView

from apps.authentication.exceptions import AuthAPIError, envelope_success
from apps.authentication.models import AuthUser
from apps.authentication.permissions.authenticated import IsApplicationUser
from apps.authentication.services.context_service import ContextService
from apps.authentication.services.step_up import require_step_up
from apps.finance.models import (
    Account,
    FinanceAuditEvent,
    FinanceGrant,
    FinanceRole,
    FinanceSettings,
    FiscalPeriodLock,
    JournalEntry,
)
from apps.finance.selectors import reports as report_selectors
from apps.finance.services.access import require_permission
from apps.finance.services.posting import post_journal, replace_draft_lines, reverse_journal
from apps.finance.services.setup import create_organization, upsert_settings
from apps.tenancy.models import Membership

ORG_HEADER = OpenApiParameter(
    name="X-Organization-ID", type=str, location=OpenApiParameter.HEADER, required=True
)


def _user(request) -> AuthUser:
    user = request.user
    if not isinstance(user, AuthUser) or not user.id:
        raise AuthAPIError("bootstrap_required", "Call /auth/bootstrap before this endpoint")
    return user


def _org_action(request, action: str):
    user = _user(request)
    org_id = request.headers.get("X-Organization-ID") or getattr(request, "organization_id", None)
    if not org_id:
        raise AuthAPIError("missing_context", "Organization context required")
    loc_id = request.headers.get("X-Location-ID") or getattr(request, "location_id", None)
    try:
        org, _loc, _roles = ContextService().validate_access(user, org_id, loc_id)
    except AuthAPIError:
        raise
    if org is None:
        raise AuthAPIError("missing_context", "Organization context required")
    require_permission(user.id, org.id, action)
    return user, org


def _dec(value) -> str:
    return str(value)


def _journal_payload(journal: JournalEntry) -> dict:
    lines = [
        {
            "id": line.id,
            "account_id": line.account_id,
            "description": line.description,
            "debit": _dec(line.debit),
            "credit": _dec(line.credit),
            "tag_id": line.tag_id,
        }
        for line in journal.lines.all()
    ]
    return {
        "id": journal.id,
        "status": journal.status,
        "entry_date": journal.entry_date.isoformat(),
        "number": journal.number,
        "memo": journal.memo,
        "source_type": journal.source_type,
        "version": journal.version,
        "reverses_id": journal.reverses_id,
        "reversed_by_id": journal.reversed_by_id,
        "lines": lines,
    }


class OrganizationListCreateView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"])
    def get(self, request):
        user = _user(request)
        memberships = Membership.objects.filter(
            user_id=user.id, status=Membership.Status.ACTIVE
        ).select_related("organization")
        items = []
        for m in memberships:
            settings = FinanceSettings.objects.filter(organization=m.organization).first()
            grant = FinanceGrant.objects.filter(
                user_id=user.id, organization=m.organization
            ).select_related("role").first()
            items.append(
                {
                    "id": m.organization.id,
                    "name": m.organization.name,
                    "status": m.organization.status,
                    "finance_setup_complete": settings is not None,
                    "finance_role_slug": grant.role.slug if grant else None,
                }
            )
        return envelope_success(request, {"items": items})

    @extend_schema(tags=["Finance"])
    def post(self, request):
        user = _user(request)
        org = create_organization(user_id=user.id, name=request.data.get("name"))
        return envelope_success(
            request, {"id": org.id, "name": org.name, "status": org.status}, http_status=201
        )


class SettingsView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request):
        user, org = _org_action(request, "finance.report.view")
        settings = FinanceSettings.objects.filter(organization=org).first()
        if not settings:
            if not FinanceGrant.objects.filter(user_id=user.id, organization=org, role__slug="owner").exists():
                require_permission(user.id, org.id, "finance.settings.configure")
            return envelope_success(request, None)
        return envelope_success(request, _settings_payload(settings))

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def put(self, request):
        user, org = _org_action(request, "finance.settings.configure")
        existing = FinanceSettings.objects.filter(organization=org).first()
        new_ccy = request.data.get("base_currency")
        if (
            existing
            and new_ccy
            and new_ccy != existing.base_currency_id
            and JournalEntry.objects.filter(organization=org, status=JournalEntry.Status.POSTED).exists()
        ):
            require_step_up(request)
        settings = upsert_settings(org=org, payload=request.data)
        FinanceAuditEvent.objects.create(
            organization=org,
            actor_user_id=user.id,
            action="settings.update",
            object_type="settings",
            object_id=org.id,
        )
        return envelope_success(request, _settings_payload(settings))


def _settings_payload(settings: FinanceSettings) -> dict:
    return {
        "country_code": settings.country_code,
        "base_currency": settings.base_currency_id,
        "fiscal_year_start_month": settings.fiscal_year_start_month,
        "timezone": settings.timezone,
        "locale": settings.locale,
        "tax_registration_applies": settings.tax_registration_applies,
        "ar_account_id": settings.ar_account_id,
        "advance_account_id": settings.advance_account_id,
        "fx_gain_account_id": settings.fx_gain_account_id,
        "fx_loss_account_id": settings.fx_loss_account_id,
        "ap_account_id": settings.ap_account_id,
        "vendor_advance_account_id": settings.vendor_advance_account_id,
        "inventory_account_id": settings.inventory_account_id,
        "cogs_account_id": settings.cogs_account_id,
        "retained_earnings_account_id": settings.retained_earnings_account_id,
        "require_document_approval": settings.require_document_approval,
        "allow_self_approve": settings.allow_self_approve,
        "approval_threshold": str(settings.approval_threshold),
        "approval_levels": settings.approval_levels,
    }


class RoleListCreateView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request):
        _, org = _org_action(request, "finance.access.manage")
        roles = FinanceRole.objects.filter(organization=org).order_by("slug")
        return envelope_success(
            request,
            {
                "items": [
                    {
                        "id": r.id,
                        "slug": r.slug,
                        "name": r.name,
                        "permissions": r.permissions,
                        "is_preset": r.is_preset,
                    }
                    for r in roles
                ]
            },
        )

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        user, org = _org_action(request, "finance.access.manage")
        require_step_up(request)
        name = (request.data.get("name") or "").strip()
        perms = request.data.get("permissions") or []
        if not name or not isinstance(perms, list):
            raise AuthAPIError("validation_error", "name and permissions[] required")
        slug = name.lower().replace(" ", "_")[:64]
        role = FinanceRole.objects.create(
            organization=org, slug=slug, name=name, permissions=perms, is_preset=False
        )
        FinanceAuditEvent.objects.create(
            organization=org,
            actor_user_id=user.id,
            action="access.grant",
            object_type="role",
            object_id=role.id,
        )
        return envelope_success(
            request, {"id": role.id, "slug": role.slug, "name": role.name, "permissions": role.permissions},
            http_status=201,
        )


class GrantListView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request):
        _, org = _org_action(request, "finance.access.manage")
        grants = FinanceGrant.objects.filter(organization=org).select_related("role")
        return envelope_success(
            request,
            {
                "items": [
                    {"user_id": g.user_id, "role_slug": g.role.slug} for g in grants
                ]
            },
        )


class GrantDetailView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def put(self, request, user_id: str):
        actor, org = _org_action(request, "finance.access.manage")
        require_step_up(request)
        if not AuthUser.objects.filter(id=user_id).exists():
            raise AuthAPIError("validation_error", "Unknown user")
        slug = request.data.get("role_slug")
        actor_grant = FinanceGrant.objects.filter(user_id=actor.id, organization=org).select_related("role").first()
        if slug == "owner" and actor.id == user_id and (not actor_grant or actor_grant.role.slug != "owner"):
            raise AuthAPIError("permission_denied", "Cannot self-grant owner")
        if slug is None:
            FinanceGrant.objects.filter(organization=org, user_id=user_id).delete()
            FinanceAuditEvent.objects.create(
                organization=org, actor_user_id=actor.id, action="access.grant",
                object_type="grant", object_id=user_id, payload={"role_slug": None},
            )
            return envelope_success(request, {"user_id": user_id, "role_slug": None})
        role = FinanceRole.objects.filter(organization=org, slug=slug).first()
        if not role:
            raise AuthAPIError("validation_error", "Unknown role")
        Membership.objects.get_or_create(
            user_id=user_id,
            organization=org,
            defaults={"status": Membership.Status.ACTIVE, "roles": []},
        )
        grant, _ = FinanceGrant.objects.update_or_create(
            organization=org, user_id=user_id, defaults={"role": role}
        )
        FinanceAuditEvent.objects.create(
            organization=org, actor_user_id=actor.id, action="access.grant",
            object_type="grant", object_id=user_id, payload={"role_slug": slug},
        )
        return envelope_success(request, {"user_id": grant.user_id, "role_slug": role.slug})


class AccountListCreateView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request):
        _, org = _org_action(request, "finance.journal.read")
        accounts = Account.objects.filter(organization=org).order_by("code")
        return envelope_success(request, {"items": [_account_payload(a) for a in accounts]})

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        _, org = _org_action(request, "finance.account.maintain")
        account = Account.objects.create(
            organization=org,
            code=request.data.get("code"),
            name=request.data.get("name"),
            classification=request.data.get("classification"),
            is_control=bool(request.data.get("is_control")),
            control_kind=request.data.get("control_kind") or "",
            cashflow_kind=request.data.get("cashflow_kind") or "",
        )
        return envelope_success(request, _account_payload(account), http_status=201)


class AccountDetailView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def patch(self, request, account_id: str):
        _, org = _org_action(request, "finance.account.maintain")
        account = Account.objects.filter(id=account_id, organization=org).first()
        if not account:
            raise AuthAPIError("cross_organization", "Account not found")
        if request.data.get("version") is not None and int(request.data["version"]) != account.version:
            raise AuthAPIError("stale_version", "Account version mismatch")
        for field in ("code", "name", "classification", "control_kind", "cashflow_kind", "status"):
            if field in request.data:
                setattr(account, field, request.data[field])
        if "is_control" in request.data:
            account.is_control = bool(request.data["is_control"])
        account.version += 1
        account.save()
        return envelope_success(request, _account_payload(account))


def _account_payload(account: Account) -> dict:
    return {
        "id": account.id,
        "code": account.code,
        "name": account.name,
        "classification": account.classification,
        "is_control": account.is_control,
        "control_kind": account.control_kind,
        "cashflow_kind": account.cashflow_kind,
        "status": account.status,
        "version": account.version,
    }


class JournalListCreateView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request):
        _, org = _org_action(request, "finance.journal.read")
        qs = JournalEntry.objects.filter(organization=org).prefetch_related("lines")
        if request.query_params.get("status"):
            qs = qs.filter(status=request.query_params["status"])
        if request.query_params.get("from"):
            qs = qs.filter(entry_date__gte=request.query_params["from"])
        if request.query_params.get("to"):
            qs = qs.filter(entry_date__lte=request.query_params["to"])
        return envelope_success(request, {"items": [_journal_payload(j) for j in qs.order_by("-entry_date")]})

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        _, org = _org_action(request, "finance.journal.create")
        source = request.data.get("source_type") or JournalEntry.Source.MANUAL
        journal = JournalEntry.objects.create(
            organization=org,
            entry_date=request.data.get("entry_date"),
            memo=request.data.get("memo") or "",
            source_type=source,
        )
        replace_draft_lines(journal, request.data.get("lines") or [])
        journal.refresh_from_db()
        return envelope_success(request, _journal_payload(journal), http_status=201)


class JournalDetailView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def patch(self, request, journal_id: str):
        _, org = _org_action(request, "finance.journal.create")
        journal = JournalEntry.objects.filter(id=journal_id, organization=org).first()
        if not journal:
            raise AuthAPIError("cross_organization", "Journal not found")
        if journal.status != JournalEntry.Status.DRAFT:
            raise AuthAPIError("validation_error", "Posted journals cannot be edited")
        if request.data.get("version") is not None and int(request.data["version"]) != journal.version:
            raise AuthAPIError("stale_version", "Journal version mismatch")
        if request.data.get("entry_date"):
            journal.entry_date = request.data["entry_date"]
        if "memo" in request.data:
            journal.memo = request.data["memo"] or ""
        if request.data.get("lines") is not None:
            replace_draft_lines(journal, request.data["lines"])
        journal.version += 1
        journal.save(update_fields=["entry_date", "memo", "version", "updated_at"])
        return envelope_success(request, _journal_payload(journal))


class JournalPostView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request, journal_id: str):
        user, org = _org_action(request, "finance.journal.post")
        journal = JournalEntry.objects.filter(id=journal_id, organization=org).first()
        if not journal:
            raise AuthAPIError("cross_organization", "Journal not found")
        version = int(request.data.get("version") or journal.version)
        posted = post_journal(
            user_id=user.id,
            org=org,
            journal_id=journal.id,
            version=version,
            idempotency_key=request.headers.get("Idempotency-Key"),
            body={"journal_id": journal.id, "version": version},
        )
        return envelope_success(request, _journal_payload(posted))


class JournalReverseView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request, journal_id: str):
        user, org = _org_action(request, "finance.journal.reverse")
        entry_date = request.data.get("entry_date")
        posted = reverse_journal(
            user_id=user.id,
            org=org,
            journal_id=journal_id,
            reason=request.data.get("reason") or "",
            entry_date=entry_date,
            idempotency_key=request.headers.get("Idempotency-Key"),
            body={"journal_id": journal_id, "reason": request.data.get("reason"), "entry_date": entry_date},
        )
        return envelope_success(request, _journal_payload(posted), http_status=201)


class PeriodListCreateView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request):
        _, org = _org_action(request, "finance.report.view")
        periods = FiscalPeriodLock.objects.filter(organization=org).order_by("start_on")
        return envelope_success(request, {"items": [_period_payload(p) for p in periods]})

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        user, org = _org_action(request, "finance.period.lock")
        start_on = date.fromisoformat(request.data["start_on"])
        end_on = date.fromisoformat(request.data["end_on"])
        overlap = FiscalPeriodLock.objects.filter(
            organization=org, start_on__lte=end_on, end_on__gte=start_on
        ).exists()
        if overlap:
            raise AuthAPIError("validation_error", "Period overlaps an existing range")
        period = FiscalPeriodLock.objects.create(organization=org, start_on=start_on, end_on=end_on)
        FinanceAuditEvent.objects.create(
            organization=org, actor_user_id=user.id, action="period.lock",
            object_type="period", object_id=period.id, payload={"created": True},
        )
        return envelope_success(request, _period_payload(period), http_status=201)


class PeriodLockView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request, period_id: str):
        user, org = _org_action(request, "finance.period.lock")
        from apps.finance.services.periods import lock_period

        year_end = bool(request.data.get("year_end")) if request.body else False
        period = lock_period(
            user_id=user.id,
            org=org,
            period_id=period_id,
            year_end=year_end,
            idempotency_key=request.headers.get("Idempotency-Key") or "",
        )
        from apps.finance.models import FinanceAuditEvent

        FinanceAuditEvent.objects.create(
            organization=org, actor_user_id=user.id, action="period.lock",
            object_type="period", object_id=period.id,
            payload={"year_end": year_end},
        )
        return envelope_success(request, _period_payload(period))


class PeriodReopenView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request, period_id: str):
        user, org = _org_action(request, "finance.period.reopen")
        require_step_up(request)
        reason = (request.data.get("reason") or "").strip()
        if not reason:
            raise AuthAPIError("validation_error", "Reopen reason is required")
        period = FiscalPeriodLock.objects.filter(id=period_id, organization=org).first()
        if not period:
            raise AuthAPIError("cross_organization", "Period not found")
        from django.utils import timezone

        period.status = FiscalPeriodLock.Status.OPEN
        period.reopen_reason = reason
        period.reopened_by = user.id
        period.reopened_at = timezone.now()
        period.save()
        FinanceAuditEvent.objects.create(
            organization=org, actor_user_id=user.id, action="period.reopen",
            object_type="period", object_id=period.id, payload={"reason": reason},
        )
        return envelope_success(request, _period_payload(period))


def _period_payload(period: FiscalPeriodLock) -> dict:
    return {
        "id": period.id,
        "start_on": period.start_on.isoformat(),
        "end_on": period.end_on.isoformat(),
        "status": period.status,
        "reopen_reason": period.reopen_reason,
    }


class TrialBalanceView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request):
        _, org = _org_action(request, "finance.report.view")
        settings = FinanceSettings.objects.select_related("base_currency").filter(organization=org).first()
        if not settings:
            raise AuthAPIError("validation_error", "Finance setup is incomplete")
        start = request.query_params.get("from")
        end = request.query_params.get("to")
        if not start or not end:
            raise AuthAPIError("validation_error", "from and to are required")
        rows = report_selectors.trial_balance(
            org=org, start=start, end=end, exponent=settings.base_currency.exponent,
            tag_id=request.query_params.get("tag_id"),
        )
        table = _table_response(request, rows, "trial-balance")
        if table is not None:
            return table
        return envelope_success(request, {"items": rows})


class GeneralLedgerView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request):
        _, org = _org_action(request, "finance.report.view")
        start = request.query_params.get("from")
        end = request.query_params.get("to")
        if not start or not end:
            raise AuthAPIError("validation_error", "from and to are required")
        rows = report_selectors.general_ledger(
            org=org, start=start, end=end, account_id=request.query_params.get("account_id"),
            tag_id=request.query_params.get("tag_id"),
        )
        return envelope_success(request, {"items": rows})


class ProfitLossView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request):
        _, org = _org_action(request, "finance.report.view")
        settings = FinanceSettings.objects.select_related("base_currency").filter(organization=org).first()
        if not settings:
            raise AuthAPIError("validation_error", "Finance setup is incomplete")
        start = request.query_params.get("from")
        end = request.query_params.get("to")
        if not start or not end:
            raise AuthAPIError("validation_error", "from and to are required")
        data = report_selectors.profit_loss(
            org=org, start=start, end=end, exponent=settings.base_currency.exponent,
            tag_id=request.query_params.get("tag_id"),
        )
        if request.query_params.get("compare_from") and request.query_params.get("compare_to"):
            data["prior"] = report_selectors.profit_loss(
                org=org,
                start=request.query_params["compare_from"],
                end=request.query_params["compare_to"],
                exponent=settings.base_currency.exponent,
                tag_id=request.query_params.get("tag_id"),
            )
        return envelope_success(request, data)


class BalanceSheetView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request):
        _, org = _org_action(request, "finance.report.view")
        settings = FinanceSettings.objects.select_related("base_currency").filter(organization=org).first()
        if not settings:
            raise AuthAPIError("validation_error", "Finance setup is incomplete")
        as_of = request.query_params.get("as_of")
        if not as_of:
            raise AuthAPIError("validation_error", "as_of is required")
        data = report_selectors.balance_sheet(org=org, as_of=as_of, exponent=settings.base_currency.exponent)
        if request.query_params.get("compare_as_of"):
            data["prior"] = report_selectors.balance_sheet(
                org=org, as_of=request.query_params["compare_as_of"], exponent=settings.base_currency.exponent
            )
        return envelope_success(request, data)


class CashFlowView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request):
        _, org = _org_action(request, "finance.report.view")
        settings = FinanceSettings.objects.select_related("base_currency").filter(organization=org).first()
        if not settings:
            raise AuthAPIError("validation_error", "Finance setup is incomplete")
        start = request.query_params.get("from")
        end = request.query_params.get("to")
        if not start or not end:
            raise AuthAPIError("validation_error", "from and to are required")
        return envelope_success(
            request,
            report_selectors.cash_flow(org=org, start=start, end=end, exponent=settings.base_currency.exponent),
        )


class TaxSummaryView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request):
        _, org = _org_action(request, "finance.report.view")
        settings = FinanceSettings.objects.select_related("base_currency").filter(organization=org).first()
        if not settings:
            raise AuthAPIError("validation_error", "Finance setup is incomplete")
        start = request.query_params.get("from")
        end = request.query_params.get("to")
        if not start or not end:
            raise AuthAPIError("validation_error", "from and to are required")
        return envelope_success(
            request,
            report_selectors.tax_summary(org=org, start=start, end=end, exponent=settings.base_currency.exponent),
        )


def _table_response(request, rows, filename):
    fmt = (request.query_params.get("export") or "").lower()
    if fmt not in ("csv", "xlsx", "pdf"):
        return None
    from django.http import HttpResponse

    if fmt == "csv":
        body = report_selectors.as_csv(rows)
        resp = HttpResponse(body, content_type="text/csv")
        resp["Content-Disposition"] = f'attachment; filename="{filename}.csv"'
        return resp
    if fmt == "pdf":
        body = report_selectors.as_pdf(filename, rows)
        resp = HttpResponse(body, content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="{filename}.pdf"'
        return resp
    body = report_selectors.as_xlsx(rows)
    resp = HttpResponse(body, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    resp["Content-Disposition"] = f'attachment; filename="{filename}.xlsx"'
    return resp


class EquityMovementView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request):
        _, org = _org_action(request, "finance.report.view")
        settings = FinanceSettings.objects.select_related("base_currency").filter(organization=org).first()
        if not settings:
            raise AuthAPIError("validation_error", "Finance setup is incomplete")
        start = request.query_params.get("from")
        end = request.query_params.get("to")
        if not start or not end:
            raise AuthAPIError("validation_error", "from and to are required")
        return envelope_success(
            request,
            report_selectors.equity_movement(
                org=org, start=start, end=end, exponent=settings.base_currency.exponent
            ),
        )


class BooksExportView(APIView):
    permission_classes = [IsApplicationUser]
    throttle_classes = []

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request):
        from rest_framework.throttling import UserRateThrottle

        class ExportThrottle(UserRateThrottle):
            rate = "30/min"

        self.throttle_classes = [ExportThrottle]
        self.check_throttles(request)
        user, org = _org_action(request, "finance.report.view")
        require_step_up(request)
        from apps.finance.models import Contact, Item, TaxRate

        settings = FinanceSettings.objects.filter(organization=org).first()
        return envelope_success(
            request,
            {
                "settings": None if not settings else _settings_payload(settings),
                "accounts": [_account_payload(a) for a in Account.objects.filter(organization=org).order_by("code")],
                "contacts": [{"id": c.id, "name": c.name} for c in Contact.objects.filter(organization=org)],
                "items": [{"id": i.id, "sku": i.sku, "name": i.name} for i in Item.objects.filter(organization=org)],
                "tax_rates": [{"id": t.id, "name": t.name, "rate": str(t.rate)} for t in TaxRate.objects.filter(organization=org)],
            },
        )
