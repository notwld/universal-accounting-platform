from pathlib import Path

from django.db import migrations


def apply_rls(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    sql_path = Path(__file__).resolve().parents[1] / "sql" / "rls.sql"
    lines = [line for line in sql_path.read_text(encoding="utf-8").splitlines() if not line.strip().startswith("--")]
    statements = [stmt.strip() for stmt in "\n".join(lines).split(";") if stmt.strip()]
    with schema_editor.connection.cursor() as cursor:
        for stmt in statements:
            cursor.execute(stmt)


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0009_banking"),
    ]

    operations = [
        migrations.RunPython(apply_rls, migrations.RunPython.noop),
    ]
