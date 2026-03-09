from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0041_tenderproposalposition_price_without_vat"),
    ]

    operations = [
        migrations.AddField(
            model_name="company",
            name="primary_color",
            field=models.CharField(
                default="#3b82f6",
                help_text="Primary UI color in HEX format (#RRGGBB).",
                max_length=7,
            ),
        ),
    ]
