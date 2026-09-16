"""Auth module constants / event catalogue (MD §45, §55)."""

SECURITY_EVENT_TYPES = (
    "auth.application_bootstrap",
    "auth.session_seen",
    "auth.account_suspended",
    "auth.account_reactivated",
    "auth.invalid_token",
    "auth.invalid_authorized_party",
    "auth.organization_denied",
    "auth.location_denied",
    "auth.permission_denied",
    "auth.context_switched",
    "auth.webhook_received",
    "auth.webhook_processed",
    "auth.webhook_failed",
    "auth.webhook_duplicate",
)

# MD §45 — Authentication Error Catalogue
ERROR_CATALOGUE = {
    "authentication_required": 401,
    "invalid_token": 401,
    "expired_token": 401,
    "invalid_token_issuer": 401,
    "invalid_authorized_party": 401,
    "invalid_session": 401,
    "account_suspended": 403,
    "organization_access_denied": 403,
    "location_access_denied": 403,
    "permission_denied": 403,
    "context_not_found": 404,
    "idempotency_conflict": 409,
    "validation_error": 422,
    "rate_limit_exceeded": 429,
    "identity_dependency_unavailable": 503,
    "misconfigured": 503,
    "webhook_invalid": 401,
    "bootstrap_required": 401,
    "internal_error": 500,
}
