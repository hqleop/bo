from django.db import migrations, models


def fill_currency_code_iso(apps, schema_editor):
    Currency = apps.get_model("core", "Currency")
    iso_by_code = {
        "UAH": "980",
        "USD": "840",
        "EUR": "978",
    }
    for code, code_iso in iso_by_code.items():
        Currency.objects.filter(code=code).update(code_iso=code_iso)


def clear_currency_code_iso(apps, schema_editor):
    Currency = apps.get_model("core", "Currency")
    Currency.objects.filter(code__in=["UAH", "USD", "EUR"]).update(code_iso=None)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0027_add_proposal_created_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="currency",
            name="code_iso",
            field=models.CharField(blank=True, db_index=True, max_length=3, null=True),
        ),
        migrations.RunPython(fill_currency_code_iso, clear_currency_code_iso),
    ]

