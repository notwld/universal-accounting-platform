from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.views import View
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.authentication import metrics


class HealthView(View):
    """Liveness — process is up (MD §40)."""

    def get(self, request):
        return JsonResponse({"status": "ok"})


class ReadinessView(View):
    """Readiness — DB reachable."""

    def get(self, request):
        try:
            connection.ensure_connection()
            return JsonResponse({"status": "ready", "database": connection.vendor})
        except Exception as exc:  # noqa: BLE001
            return JsonResponse(
                {"status": "not_ready", "error": type(exc).__name__}, status=503
            )


class MetricsView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return HttpResponse(metrics.render_prometheus(), content_type="text/plain; version=0.0.4")
