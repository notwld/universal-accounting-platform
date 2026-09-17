from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework.permissions import AllowAny

from apps.authentication.api.health import HealthView, MetricsView, ReadinessView
from apps.finance.api.views import OrganizationListCreateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", HealthView.as_view(), name="health"),
    path("ready/", ReadinessView.as_view(), name="ready"),
    path("metrics/", MetricsView.as_view(), name="metrics"),
    path("api/v1/auth/", include("apps.authentication.api.v1.urls")),
    path("api/v1/organizations", OrganizationListCreateView.as_view(), name="organizations"),
    path("api/v1/finance/", include("apps.finance.api.urls")),
    path("api/v1/webhooks/", include("apps.authentication.webhooks.urls")),
    path(
        "api/schema/",
        SpectacularAPIView.as_view(permission_classes=[AllowAny]),
        name="schema",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema", permission_classes=[AllowAny]),
        name="redoc",
    ),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema", permission_classes=[AllowAny]),
        name="swagger-ui",
    ),
]
