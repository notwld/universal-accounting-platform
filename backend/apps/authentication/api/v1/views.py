from django.conf import settings
from django.core.cache import cache
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.authentication.api.v1.serializers import BootstrapSerializer, SwitchContextSerializer
from apps.authentication.authenticators.clerk import ClerkPrincipal
from apps.authentication.exceptions import AuthAPIError, envelope_success
from apps.authentication.models import AuthUser, SecurityEvent, SessionProjection
from apps.authentication.services import (
    BootstrapService,
    ContextService,
    IdempotencyService,
    IdentityService,
    SecurityService,
    SessionService,
)

ORG_HEADER = OpenApiParameter(
    name="X-Organization-ID",
    type=str,
    location=OpenApiParameter.HEADER,
    required=False,
)
LOC_HEADER = OpenApiParameter(
    name="X-Location-ID",
    type=str,
    location=OpenApiParameter.HEADER,
    required=False,
)
IDEMPOTENCY_HEADER = OpenApiParameter(
    name="Idempotency-Key",
    type=str,
    location=OpenApiParameter.HEADER,
    required=False,
)
REQUEST_ID_HEADER = OpenApiParameter(
    name="X-Request-ID",
    type=str,
    location=OpenApiParameter.HEADER,
    required=False,
)


def _enforce_rate(request, *, scope: str, limit: str):
    try:
        count_s, period = limit.split("/")
        max_count = int(count_s)
    except ValueError:
        return
    window = 60 if period.startswith("m") else 1
    ident = getattr(request.user, "id", None) or request.META.get("REMOTE_ADDR", "anon")
    key = f"rl:{scope}:{ident}"
    try:
        current = cache.get(key, 0)
        if current >= max_count:
            raise AuthAPIError("rate_limit_exceeded", "Too many requests")
        if current == 0:
            cache.set(key, 1, timeout=window)
        else:
            try:
                cache.incr(key)
            except ValueError:
                cache.set(key, current + 1, timeout=window)
    except AuthAPIError:
        raise
    except Exception:  # noqa: BLE001 — Redis down: continue (degrade)
        pass


def _claims(request) -> dict:
    claims = getattr(request, "clerk_claims", None) or getattr(request, "auth", None)
    if not isinstance(claims, dict):
        raise AuthAPIError("authentication_required", "Missing authentication")
    return claims


def _app_user(request) -> AuthUser:
    user = request.user
    if isinstance(user, ClerkPrincipal) or not getattr(user, "id", None):
        raise AuthAPIError("bootstrap_required", "Call /auth/bootstrap before this endpoint")
    return user


def _cursor_slice(qs, request, *, default_limit=20, max_limit=100):
    try:
        limit = min(int(request.query_params.get("limit", default_limit)), max_limit)
    except ValueError:
        limit = default_limit
    cursor = request.query_params.get("cursor")
    if cursor:
        qs = qs.filter(id__lt=cursor)
    items = list(qs[: limit + 1])
    has_more = len(items) > limit
    items = items[:limit]
    next_cursor = items[-1].id if has_more and items else None
    return items, has_more, next_cursor


class BootstrapAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth"],
        summary="Bootstrap application identity after Clerk auth",
        request=BootstrapSerializer,
        parameters=[IDEMPOTENCY_HEADER, REQUEST_ID_HEADER],
        responses={200: OpenApiResponse(description="Bootstrap envelope")},
    )
    def post(self, request):
        _enforce_rate(request, scope="bootstrap", limit=settings.AUTH_BOOTSTRAP_RATE_LIMIT)
        claims = _claims(request)
        ser = BootstrapSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        idem = IdempotencyService()
        record = idem.begin(
            key=request.headers.get("Idempotency-Key"),
            user_id=claims.get("sub", ""),
            body=ser.validated_data,
            method="POST",
            path="/api/v1/auth/bootstrap",
        )
        if record and record.response_body is not None:
            return envelope_success(
                request, record.response_body["data"], http_status=record.response_status
            )
        data = BootstrapService().run(request=request, claims=claims, payload=ser.validated_data)
        request.user = AuthUser.objects.get(id=data["user"]["id"])
        resp = envelope_success(request, data)
        idem.complete(record, resp.status_code, resp.data)
        return resp


class MeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth"],
        summary="Current application user",
        parameters=[ORG_HEADER, LOC_HEADER, REQUEST_ID_HEADER],
        responses={200: OpenApiResponse(description="Me envelope")},
    )
    def get(self, request):
        _enforce_rate(request, scope="me", limit=settings.AUTH_ME_RATE_LIMIT)
        user = _app_user(request)
        org, loc, roles = ContextService().validate_access(
            user, getattr(request, "organization_id", None), getattr(request, "location_id", None)
        )
        email = IdentityService().email_plaintext(user)
        return envelope_success(
            request,
            {
                "id": user.id,
                "identity": {
                    "clerk_user_id": user.clerk_user_id,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": email,
                    "email_verified": user.email_verified,
                    "avatar_url": user.avatar_url or None,
                },
                "preferences": {"timezone": user.timezone, "locale": user.locale},
                "status": user.status,
                "current_context": {
                    "organization_id": org.id if org else None,
                    "location_id": loc.id if loc else None,
                },
                "authorization": {"version": user.authorization_version, "roles": roles},
            },
        )


class AuthContextAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth"],
        summary="Current tenant/location auth context",
        parameters=[ORG_HEADER, LOC_HEADER, REQUEST_ID_HEADER],
        responses={200: OpenApiResponse(description="Context envelope")},
    )
    def get(self, request):
        _enforce_rate(request, scope="context", limit=settings.AUTH_CONTEXT_RATE_LIMIT)
        user = _app_user(request)
        org, loc, roles = ContextService().validate_access(
            user, getattr(request, "organization_id", None), getattr(request, "location_id", None)
        )
        if not org:
            raise AuthAPIError("context_not_found", "No organization context")
        return envelope_success(
            request,
            {
                "organization": {"id": org.id, "name": org.name},
                "location": {"id": loc.id, "name": loc.name} if loc else None,
                "authorization": {"version": user.authorization_version, "roles": roles},
            },
        )


class SwitchContextAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth"],
        summary="Switch organization/location context",
        request=SwitchContextSerializer,
        parameters=[IDEMPOTENCY_HEADER, REQUEST_ID_HEADER],
        responses={200: OpenApiResponse(description="Switch envelope")},
    )
    def post(self, request):
        _enforce_rate(request, scope="context_switch", limit=settings.AUTH_CONTEXT_SWITCH_RATE_LIMIT)
        user = _app_user(request)
        ser = SwitchContextSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        idem = IdempotencyService()
        record = idem.begin(
            key=request.headers.get("Idempotency-Key"),
            user_id=user.id,
            body=ser.validated_data,
            method="POST",
            path="/api/v1/auth/context/switch",
            organization_id=ser.validated_data.get("organization_id", ""),
        )
        if record and record.response_body is not None:
            return envelope_success(
                request, record.response_body["data"], http_status=record.response_status
            )
        org, loc, roles, version = ContextService().switch(
            user,
            ser.validated_data["organization_id"],
            ser.validated_data.get("location_id"),
        )
        SecurityService().record(
            user=user,
            event_type=SecurityService.EVENT_CONTEXT_SWITCH,
            request=request,
            organization_id=org.id,
            location_id=loc.id if loc else "",
            metadata={"roles": roles},
            notify_email=True,
        )
        data = {
            "organization_id": org.id,
            "location_id": loc.id if loc else None,
            "authorization_version": version,
            "roles": roles,
        }
        resp = envelope_success(request, data)
        idem.complete(record, resp.status_code, resp.data)
        return resp


class SessionListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth"],
        summary="List session projections",
        parameters=[REQUEST_ID_HEADER],
        responses={200: OpenApiResponse(description="Sessions envelope")},
    )
    def get(self, request):
        _enforce_rate(
            request,
            scope="sessions",
            limit=getattr(settings, "AUTH_SESSIONS_RATE_LIMIT", "60/m"),
        )
        user = _app_user(request)
        qs = SessionService().list_for_user(user)
        items, has_more, next_cursor = _cursor_slice(qs, request, default_limit=20, max_limit=50)
        current_sid = getattr(request, "clerk_session_id", None)
        return envelope_success(
            request,
            [
                {
                    "id": s.id,
                    "device_name": s.device_name,
                    "platform": s.device_platform,
                    "browser": s.browser_family,
                    "current": bool(current_sid and s.clerk_session_id == current_sid),
                    "status": s.status,
                    "last_seen_at": s.last_seen_at.isoformat() if s.last_seen_at else None,
                }
                for s in items
            ],
            meta_extra={"has_more": has_more, "next_cursor": next_cursor},
        )


class SecurityEventListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth"],
        summary="List user-visible security events",
        parameters=[REQUEST_ID_HEADER],
        responses={200: OpenApiResponse(description="Security events envelope")},
    )
    def get(self, request):
        _enforce_rate(request, scope="security_events", limit=settings.AUTH_SECURITY_EVENTS_RATE_LIMIT)
        user = _app_user(request)
        qs = SecurityEvent.objects.filter(user=user).order_by("-occurred_at", "-id")
        items, has_more, next_cursor = _cursor_slice(qs, request, default_limit=50, max_limit=100)
        return envelope_success(
            request,
            [
                {
                    "id": e.id,
                    "event_type": e.event_type,
                    "organization_id": e.organization_id or None,
                    "location_id": e.location_id or None,
                    "occurred_at": e.occurred_at.isoformat(),
                    "severity": e.severity,
                }
                for e in items
            ],
            meta_extra={"has_more": has_more, "next_cursor": next_cursor},
        )
