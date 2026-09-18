from pathlib import Path

from django.db.utils import ProgrammingError


def apply_rls_sql(schema_editor):
    """Apply finance/sql/rls.sql, skipping statements for tables not yet created."""
    if schema_editor.connection.vendor != "postgresql":
        return
    sql_path = Path(__file__).resolve().parent / "rls.sql"
    lines = [
        line
        for line in sql_path.read_text(encoding="utf-8").splitlines()
        if not line.strip().startswith("--")
    ]
    statements = [stmt.strip() for stmt in "\n".join(lines).split(";") if stmt.strip()]
    with schema_editor.connection.cursor() as cursor:
        for stmt in statements:
            cursor.execute("SAVEPOINT rls_stmt")
            try:
                cursor.execute(stmt)
                cursor.execute("RELEASE SAVEPOINT rls_stmt")
            except ProgrammingError as exc:
                cursor.execute("ROLLBACK TO SAVEPOINT rls_stmt")
                msg = str(exc).lower()
                if "does not exist" not in msg:
                    raise
