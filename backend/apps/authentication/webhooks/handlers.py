"""Webhook event handlers (MD §79)."""

# Concrete handling lives in tasks.webhook_tasks; this module is the extension point
# for per-event-type sync handlers imported by the worker.
HANDLERS = {
    "user.created": "upsert_user",
    "user.updated": "upsert_user",
    "user.deleted": "anonymize_user",
    "session.revoked": "end_session",
    "session.ended": "end_session",
}
