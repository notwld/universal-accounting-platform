from django.contrib import admin

from apps.authentication.models import (
    AuthUser,
    IdempotencyRecord,
    ProviderEvent,
    SecurityEvent,
    SessionProjection,
)

admin.site.register(AuthUser)
admin.site.register(SessionProjection)
admin.site.register(SecurityEvent)
admin.site.register(ProviderEvent)
admin.site.register(IdempotencyRecord)
