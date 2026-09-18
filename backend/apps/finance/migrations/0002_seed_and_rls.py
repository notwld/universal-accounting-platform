
from django.db import migrations

from apps.finance.models.config import ISO_CURRENCIES


def seed_currencies(apps, schema_editor):
    Currency = apps.get_model("finance", "Currency")
    Currency.objects.bulk_create(
        [Currency(code=code, exponent=exp, name=name) for code, exp, name in ISO_CURRENCIES],
        ignore_conflicts=True,
    )


def apply_rls(apps, schema_editor):
    from apps.finance.sql.apply import apply_rls_sql
    apply_rls_sql(schema_editor)


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_currencies, migrations.RunPython.noop),
        migrations.RunPython(apply_rls, migrations.RunPython.noop),
    ]
