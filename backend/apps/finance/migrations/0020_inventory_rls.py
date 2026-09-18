
from django.db import migrations


def apply_rls(apps, schema_editor):
    from apps.finance.sql.apply import apply_rls_sql
    apply_rls_sql(schema_editor)


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0019_inventory_stock"),
    ]

    operations = [
        migrations.RunPython(apply_rls, migrations.RunPython.noop),
    ]
