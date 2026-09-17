"""Postgres isolation/concurrency gates. Skipped unless DATABASE_URL is PostgreSQL."""

import pytest
from django.db import connection


pytestmark = pytest.mark.skipif(
    connection.vendor != "postgresql",
    reason="RLS and concurrent posting require PostgreSQL",
)


def test_rls_policies_exist():
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT tablename FROM pg_policies WHERE tablename LIKE 'finance_%'"
        )
        tables = {row[0] for row in cursor.fetchall()}
    assert "finance_journal" in tables
    assert "finance_account" in tables
