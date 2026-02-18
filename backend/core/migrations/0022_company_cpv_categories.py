from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0021_unitofmeasure_short_name_ua_short_name_en"),
    ]

    operations = [
        migrations.AddField(
            model_name="company",
            name="cpv_categories",
            field=models.ManyToManyField(
                blank=True,
                help_text="CPV-категорії, закріплені за компанією",
                related_name="companies_by_cpvs",
                to="core.cpvdictionary",
            ),
        ),
    ]

