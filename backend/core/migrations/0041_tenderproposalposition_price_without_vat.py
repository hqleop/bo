from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0040_tender_price_criterion_vat_percent"),
    ]

    operations = [
        migrations.AddField(
            model_name="tenderproposalposition",
            name="price_without_vat",
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                max_digits=18,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="salestenderproposalposition",
            name="price_without_vat",
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                max_digits=18,
                null=True,
            ),
        ),
    ]

