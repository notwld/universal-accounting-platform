import logging
import time

from django.utils.deprecation import MiddlewareMixin

from apps.authentication import metrics

logger = logging.getLogger("apps.authentication.access")


class AccessLogMiddleware(MiddlewareMixin):
    """Structured per-request access log (MD §58). Never logs JWT/secrets."""

    def process_request(self, request):
        request._auth_access_start = time.perf_counter()

    def process_response(self, request, response):
        start = getattr(request, "_auth_access_start", None)
        duration_ms = round((time.perf_counter() - start) * 1000, 2) if start else None
        path = request.path
        if path.startswith("/api/"):
            logger.info(
                "access",
                extra={
                    "path": path,
                    "method": request.method,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                    "request_id": getattr(request, "request_id", None),
                    "organization_id": getattr(request, "organization_id", None)
                    if getattr(request, "trusted_context", False)
                    else None,
                },
            )
            if path.startswith("/api/v1/auth/"):
                metrics.incr("auth_http_requests_total", path=path, status=response.status_code)
            elif path.startswith("/api/v1/finance/"):
                metrics.incr("finance_http_requests_total", status=response.status_code)
        response["X-Request-ID"] = getattr(request, "request_id", response.get("X-Request-ID", ""))
        if path.startswith("/api/v1/auth/"):
            response.setdefault("Cache-Control", "no-store")
            response.setdefault("Pragma", "no-cache")
        return response
