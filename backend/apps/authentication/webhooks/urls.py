from django.urls import path

from apps.authentication.webhooks.clerk import ClerkWebhookAPIView

urlpatterns = [
    path("clerk", ClerkWebhookAPIView.as_view(), name="clerk-webhook"),
]
