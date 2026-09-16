import logging
from datetime import datetime, timezone

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.authentication.constants import ERROR_CATALOGUE

logger = logging.getLogger(__name__)


class AuthAPIError(Exception):
    def __init__(self, code: str, message: str, http_status: int | None = None, field_errors=None):
        self.code = code
        self.message = message
        self.http_status = http_status or ERROR_CATALOGUE.get(code, 400)
        self.field_errors = field_errors
        super().__init__(message)


def _apply_auth_headers(response: Response, *, http_status: int):
    response["Cache-Control"] = "no-store"
    response["Pragma"] = "no-cache"
    if http_status in (401, 403):
        response["WWW-Authenticate"] = "Bearer"
    if http_status == 429:
        response.setdefault("Retry-After", "30")
    return response


def envelope_error(request, code: str, message: str, field_errors=None, http_status=400):
    request_id = getattr(request, "request_id", None)
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    response = Response(
        {
            "error": {
                "code": code,
                "message": message,
                "field_errors": field_errors,
                "request_id": request_id,
                "timestamp": ts,
            }
        },
        status=http_status,
    )
    return _apply_auth_headers(response, http_status=http_status)


def envelope_success(request, data, http_status=200, meta_extra=None):
    request_id = getattr(request, "request_id", None)
    meta = {
        "request_id": request_id,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    if meta_extra:
        meta.update(meta_extra)
    response = Response({"data": data, "meta": meta}, status=http_status)
    return _apply_auth_headers(response, http_status=http_status)


def api_exception_handler(exc, context):
    from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated, PermissionDenied
    from rest_framework.views import exception_handler as drf_exception_handler

    request = context.get("request")
    if isinstance(exc, AuthAPIError):
        return envelope_error(
            request,
            exc.code,
            exc.message,
            field_errors=exc.field_errors,
            http_status=exc.http_status,
        )

    if isinstance(exc, ValidationError):
        return envelope_error(
            request,
            "validation_error",
            "Payload validation failure",
            field_errors=exc.detail if isinstance(exc.detail, dict) else {"non_field_errors": exc.detail},
            http_status=422,
        )

    if isinstance(exc, AuthenticationFailed):
        detail = exc.detail
        if isinstance(detail, dict) and "code" in detail:
            return envelope_error(
                request, detail["code"], detail.get("message", "Authentication failed"), http_status=401
            )
        return envelope_error(request, "invalid_token", str(detail), http_status=401)

    if isinstance(exc, NotAuthenticated):
        return envelope_error(request, "authentication_required", "Authentication required", http_status=401)

    if isinstance(exc, PermissionDenied):
        detail = exc.detail
        if isinstance(detail, dict) and "code" in detail:
            return envelope_error(
                request, detail["code"], detail.get("message", "Forbidden"), http_status=403
            )
        return envelope_error(request, "permission_denied", str(detail), http_status=403)

    response = drf_exception_handler(exc, context)
    if response is None:
        logger.exception("unhandled_api_error")
        return envelope_error(
            request,
            "internal_error",
            "Unexpected error",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    detail = response.data
    code = "authentication_required" if response.status_code == 401 else "permission_denied"
    message = "Request failed"
    field_errors = None
    if isinstance(detail, dict):
        if "code" in detail and "message" in detail:
            code = detail["code"]
            message = detail["message"]
        elif "detail" in detail:
            message = str(detail["detail"])
        else:
            field_errors = detail
            code = "validation_error" if response.status_code == 400 else code
            message = "Request failed"
            if response.status_code == 400:
                response.status_code = 422
    return envelope_error(
        request, code, message, field_errors=field_errors, http_status=response.status_code
    )
