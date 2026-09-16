"""PostgreSQL RLS session helpers (MD §49–51)."""

from django.db import connection


def set_rls_context(*, user_id: str | None, organization_id: str | None, location_id: str | None):
    if connection.vendor != "postgresql":
        return
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.user_id', %s, true)", [user_id or ""])
        cursor.execute(
            "SELECT set_config('app.organization_id', %s, true)", [organization_id or ""]
        )
        cursor.execute("SELECT set_config('app.location_id', %s, true)", [location_id or ""])


def clear_rls_context():
    set_rls_context(user_id=None, organization_id=None, location_id=None)


def celery_rls_context(*, user_id: str | None = None, organization_id: str | None = None):
    """Context manager-style helper for Celery tasks that touch tenant data."""
    set_rls_context(user_id=user_id, organization_id=organization_id, location_id=None)
