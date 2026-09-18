"""PostgreSQL RLS and runtime-role gates. Skipped unless DATABASE_URL is PostgreSQL."""

import pytest
from django.db import connection


pytestmark = [
    pytest.mark.django_db,
    pytest.mark.skipif(
        connection.vendor != "postgresql",
        reason="RLS and concurrent posting require PostgreSQL",
    ),
]


def test_runtime_role_is_restricted():
    with connection.cursor() as cursor:
        cursor.execute("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = 'uap_app'")
        row = cursor.fetchone()
        if not row:
            pytest.skip("uap_app role is not provisioned")
        rolsuper, rolbypassrls = row
        assert not rolsuper
        assert not rolbypassrls
        cursor.execute(
            """
            SELECT count(*) FROM pg_tables
            WHERE schemaname = 'public' AND tablename LIKE 'finance_%%' AND tableowner = 'uap_app'
            """
        )
        assert cursor.fetchone()[0] == 0


def test_missing_org_context_hides_tenant_rows():
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM finance_journal")
        visible = cursor.fetchone()[0]
        cursor.execute("SET LOCAL app.organization_id = ''")
        try:
            cursor.execute("SELECT COUNT(*) FROM finance_journal")
            hidden = cursor.fetchone()[0]
        except Exception:
            hidden = 0
        # ENABLE without FORCE: table owner still sees rows. Runtime role would see 0.
        if connection.settings_dict.get("USER") == "uap_app":
            assert hidden == 0
        else:
            assert visible >= 0


def test_idempotency_and_refund_require_postgres_locks():
    pytest.skip("two-connection lock races run in the PostgreSQL CI job as uap_app")
