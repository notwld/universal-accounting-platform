from django.urls import path

from apps.authentication.api.v1.views import (
    AuthContextAPIView,
    BootstrapAPIView,
    MeAPIView,
    SecurityEventListAPIView,
    SessionListAPIView,
    SwitchContextAPIView,
)

urlpatterns = [
    path("bootstrap", BootstrapAPIView.as_view(), name="auth-bootstrap"),
    path("me", MeAPIView.as_view(), name="auth-me"),
    path("context", AuthContextAPIView.as_view(), name="auth-context"),
    path("context/switch", SwitchContextAPIView.as_view(), name="auth-context-switch"),
    path("sessions", SessionListAPIView.as_view(), name="auth-sessions"),
    path("security-events", SecurityEventListAPIView.as_view(), name="auth-security-events"),
]
