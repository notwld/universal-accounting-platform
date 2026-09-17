from pathlib import Path

from django.db import migrations

from apps.finance.models.config import ISO_CURRENCIES


def seed_currencies(apps, schema_editor):
    Currency = apps.get_model("finance", "Currency")
    Currency.objects.bulk_create(
        [Currency(code=code, exponent=exp, name=name) for code, exp, name in ISO_CURRENCIES],
        ignore_conflicts=True,
    )


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
        ("finance", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_currencies, migrations.RunPython.noop),
        migrations.RunPython(apply_rls, migrations.RunPython.noop),
    ]
