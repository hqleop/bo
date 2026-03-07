from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0039_alter_expensearticle_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="procurementtender",
            name="price_criterion_vat_percent",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Відсоток ПДВ для режиму with_vat, наприклад 20.00",
                max_digits=5,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="salestender",
            name="price_criterion_vat_percent",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Відсоток ПДВ для режиму with_vat, наприклад 20.00",
                max_digits=5,
                null=True,
            ),
        ),
    ]
