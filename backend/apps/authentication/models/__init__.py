from django.db import models

from apps.authentication.ids import new_uuid


class AuthUser(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"
        DELETED = "deleted", "Deleted"

    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    clerk_user_id = models.CharField(max_length=64, unique=True)
    primary_email_hash = models.CharField(max_length=64, db_index=True)
    primary_email_ciphertext = models.TextField(blank=True, default="")
    first_name = models.CharField(max_length=150, blank=True, default="")
    last_name = models.CharField(max_length=150, blank=True, default="")
    avatar_url = models.TextField(blank=True, default="")
    email_verified = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    authorization_version = models.BigIntegerField(default=1)
    timezone = models.CharField(max_length=64, blank=True, default="")
    locale = models.CharField(max_length=20, blank=True, default="")
    last_authenticated_at = models.DateTimeField(null=True, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "app_auth_user"
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["authorization_version"]),
        ]

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_anonymous(self) -> bool:
        return False


class SessionProjection(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        ENDED = "ended", "Ended"
        EXPIRED = "expired", "Expired"
        UNKNOWN = "unknown", "Unknown"

    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    user = models.ForeignKey(AuthUser, on_delete=models.CASCADE, related_name="sessions")
    clerk_session_id = models.CharField(max_length=128, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    device_name = models.CharField(max_length=100, blank=True, default="")
    device_platform = models.CharField(max_length=40, blank=True, default="")
    browser_family = models.CharField(max_length=50, blank=True, default="")
    app_version = models.CharField(max_length=30, blank=True, default="")
    ip_hash = models.CharField(max_length=64, blank=True, default="")
    user_agent_hash = models.CharField(max_length=64, blank=True, default="")
    last_seen_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "auth_session_projection"
        indexes = [
            models.Index(fields=["user", "-last_seen_at"]),
        ]


class SecurityEvent(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    user = models.ForeignKey(
        AuthUser, on_delete=models.CASCADE, related_name="security_events", null=True
    )
    event_type = models.CharField(max_length=64, db_index=True)
    organization_id = models.CharField(max_length=36, blank=True, default="")
    location_id = models.CharField(max_length=36, blank=True, default="")
    request_id = models.CharField(max_length=64, blank=True, default="", db_index=True)
    clerk_session_id = models.CharField(max_length=128, blank=True, default="")
    severity = models.CharField(max_length=20, blank=True, default="info")
    ip_hash = models.CharField(max_length=64, blank=True, default="")
    user_agent_hash = models.CharField(max_length=64, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "auth_security_event"
        indexes = [
            models.Index(fields=["user", "-occurred_at"]),
            models.Index(fields=["event_type", "-occurred_at"]),
        ]


class ProviderEvent(models.Model):
    class Status(models.TextChoices):
        RECEIVED = "received", "Received"
        PROCESSING = "processing", "Processing"
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Failed"
        DUPLICATE = "duplicate", "Duplicate"

    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    provider = models.CharField(max_length=30, default="clerk")
    external_event_id = models.CharField(max_length=150)
    event_type = models.CharField(max_length=100)
    payload_hash = models.CharField(max_length=64, blank=True, default="")
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.RECEIVED)
    attempts = models.PositiveIntegerField(default=0)
    received_at = models.DateTimeField(auto_now_add=True)
    processing_started_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    error_code = models.CharField(max_length=100, blank=True, default="")
    error_summary = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "auth_provider_event"
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "external_event_id"],
                name="uniq_provider_event",
            )
        ]


class IdempotencyRecord(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    key = models.CharField(max_length=128)
    key_hash = models.CharField(max_length=64, blank=True, default="")
    user_id = models.CharField(max_length=36, blank=True, default="")
    method = models.CharField(max_length=10, blank=True, default="")
    path = models.CharField(max_length=255, blank=True, default="")
    organization_id = models.CharField(max_length=36, blank=True, default="")
    request_hash = models.CharField(max_length=64)
    response_status = models.PositiveIntegerField(null=True, blank=True)
    response_body = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = "auth_idempotency"
        constraints = [
            models.UniqueConstraint(fields=["key", "user_id"], name="uniq_idempotency_key_user")
        ]
