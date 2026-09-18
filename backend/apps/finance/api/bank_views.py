from drf_spectacular.utils import extend_schema
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.views import APIView

from apps.authentication.exceptions import AuthAPIError, envelope_success
from apps.authentication.permissions.authenticated import IsApplicationUser
from apps.finance.api.views import ORG_HEADER, _org_action
from apps.finance.models import BankFeed, BankLine, BankReconciliation, BankRule
from apps.finance.services.banking import (
    apply_bank_rules,
    categorize_line,
    complete_reconciliation,
    create_bank_feed,
    create_bank_rule,
    create_reconciliation,
    fetch_bank_feed,
    import_statement,
    match_line,
    recon_evidence,
    reopen_reconciliation,
    update_bank_rule,
)


def _iso(value):
    return value if isinstance(value, str) else value.isoformat()


def _line(line: BankLine):
    return {
        "id": line.id,
        "statement_id": line.statement_id,
        "account_id": line.account_id,
        "entry_date": _iso(line.entry_date),
        "amount": str(line.amount),
        "description": line.description,
        "status": line.status,
        "customer_payment_id": line.customer_payment_id,
        "vendor_payment_id": line.vendor_payment_id,
        "journal_id": line.journal_id,
    }


def _recon(rec: BankReconciliation):
    pack = recon_evidence(rec.organization, rec)
    return {
        "id": rec.id,
        "account_id": rec.account_id,
        "start_on": _iso(rec.start_on),
        "end_on": _iso(rec.end_on),
        "opening": str(rec.opening),
        "closing": str(rec.closing),
        "book_balance": str(rec.book_balance),
        "status": rec.status,
        "reopen_reason": rec.reopen_reason,
        "cleared_count": pack["cleared_count"],
        "outstanding_statement": pack["outstanding_statement"],
        "uncleared_book": pack["uncleared_book"],
        "difference": pack["difference"],
    }


class BankStatementImportView(APIView):
    permission_classes = [IsApplicationUser]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        user, org = _org_action(request, "finance.payment.record")
        uploaded = request.FILES.get("file")
        if not uploaded:
            raise AuthAPIError("validation_error", "file is required")
        statement, created, duplicates, categorized = import_statement(
            user_id=user.id,
            org=org,
            account_id=request.data.get("account_id"),
            uploaded=uploaded,
            dry_run=str(request.data.get("dry_run") or "").lower() in ("1", "true", "yes"),
        )
        payload = {
            "id": None if statement is None else statement.id,
            "account_id": request.data.get("account_id"),
            "created": created if statement is None else [_line(x) for x in created],
            "duplicates": duplicates,
            "categorized": [] if statement is None else [_line(x) for x in categorized],
            "dry_run": statement is None,
        }
        return envelope_success(request, payload, http_status=200 if statement is None else 201)


class BankLineListView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request):
        _, org = _org_action(request, "finance.payment.record")
        qs = BankLine.objects.filter(organization=org)
        from apps.finance.services.workflow import apply_saved_filter

        qs = apply_saved_filter(
            qs, org=org, resource="bank_line", filter_id=request.query_params.get("saved_filter_id")
        )
        account_id = request.query_params.get("account_id")
        if account_id:
            qs = qs.filter(account_id=account_id)
        return envelope_success(request, {"items": [_line(x) for x in qs.order_by("entry_date", "id")]})


class BankLineMatchView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request, line_id: str):
        user, org = _org_action(request, "finance.payment.record")
        line = match_line(
            user_id=user.id,
            org=org,
            line_id=line_id,
            customer_payment_id=request.data.get("customer_payment_id"),
            vendor_payment_id=request.data.get("vendor_payment_id"),
        )
        return envelope_success(request, _line(line))


class BankLineCategorizeView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request, line_id: str):
        user, org = _org_action(request, "finance.payment.record")
        line = categorize_line(
            user_id=user.id,
            org=org,
            line_id=line_id,
            account_id=request.data.get("account_id"),
            idempotency_key=request.headers.get("Idempotency-Key"),
        )
        return envelope_success(request, _line(line))


class BankReconciliationCreateView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        user, org = _org_action(request, "finance.payment.record")
        rec = create_reconciliation(
            user_id=user.id,
            org=org,
            account_id=request.data.get("account_id"),
            start_on=request.data.get("start_on"),
            end_on=request.data.get("end_on"),
            opening=request.data.get("opening") or 0,
            closing=request.data.get("closing") or 0,
        )
        return envelope_success(request, _recon(rec), http_status=201)


class BankReconciliationCompleteView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request, recon_id: str):
        user, org = _org_action(request, "finance.payment.record")
        return envelope_success(
            request, _recon(complete_reconciliation(user_id=user.id, org=org, recon_id=recon_id))
        )


class BankReconciliationReopenView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request, recon_id: str):
        user, org = _org_action(request, "finance.payment.record")
        return envelope_success(
            request,
            _recon(
                reopen_reconciliation(
                    user_id=user.id, org=org, recon_id=recon_id, reason=request.data.get("reason")
                )
            ),
        )


def _rule(rule: BankRule):
    return {
        "id": rule.id,
        "pattern": rule.pattern,
        "match_kind": rule.match_kind,
        "amount_min": None if rule.amount_min is None else str(rule.amount_min),
        "amount_max": None if rule.amount_max is None else str(rule.amount_max),
        "account_id": rule.account_id,
        "direction": rule.direction,
        "priority": rule.priority,
        "active": rule.active,
    }


class BankRuleListCreateView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request):
        _, org = _org_action(request, "finance.payment.record")
        items = [_rule(r) for r in BankRule.objects.filter(organization=org).order_by("priority", "id")]
        return envelope_success(request, {"items": items})

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        user, org = _org_action(request, "finance.payment.record")
        return envelope_success(
            request, _rule(create_bank_rule(user_id=user.id, org=org, payload=request.data)), http_status=201
        )


class BankRuleDetailView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def patch(self, request, rule_id: str):
        user, org = _org_action(request, "finance.payment.record")
        return envelope_success(
            request, _rule(update_bank_rule(user_id=user.id, org=org, rule_id=rule_id, payload=request.data))
        )


class BankRuleApplyView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        user, org = _org_action(request, "finance.payment.record")
        lines = apply_bank_rules(user_id=user.id, org=org, account_id=request.data.get("account_id"))
        return envelope_success(request, {"categorized": [_line(x) for x in lines]})


def _feed(feed: BankFeed):
    return {
        "id": feed.id,
        "account_id": feed.account_id,
        "url": feed.url,
        "active": feed.active,
        "last_fetched_at": None if not feed.last_fetched_at else _iso(feed.last_fetched_at),
        "last_error": feed.last_error,
    }


class BankFeedListCreateView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request):
        _, org = _org_action(request, "finance.payment.record")
        items = [_feed(f) for f in BankFeed.objects.filter(organization=org)]
        return envelope_success(request, {"items": items})

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        user, org = _org_action(request, "finance.payment.record")
        return envelope_success(
            request, _feed(create_bank_feed(user_id=user.id, org=org, payload=request.data)), http_status=201
        )


class BankFeedFetchView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request, feed_id: str):
        user, org = _org_action(request, "finance.payment.record")
        statement, created, duplicates, categorized = fetch_bank_feed(
            user_id=user.id, org=org, feed_id=feed_id
        )
        return envelope_success(
            request,
            {
                "id": statement.id,
                "created": [_line(x) for x in created],
                "duplicates": duplicates,
                "categorized": [_line(x) for x in categorized],
            },
        )
