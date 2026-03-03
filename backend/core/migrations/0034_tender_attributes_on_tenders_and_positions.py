from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0033_tender_attributes_and_criterion_date"),
    ]

    operations = [
        migrations.AddField(
            model_name="procurementtender",
            name="tender_attributes",
            field=models.ManyToManyField(
                blank=True,
                help_text="Атрибути тендера для позицій",
                related_name="procurement_tenders",
                to="core.tenderattribute",
            ),
        ),
        migrations.AddField(
            model_name="salestender",
            name="tender_attributes",
            field=models.ManyToManyField(
                blank=True,
                help_text="Атрибути тендера для позицій",
                related_name="sales_tenders",
                to="core.tenderattribute",
            ),
        ),
        migrations.AddField(
            model_name="procurementtenderposition",
            name="attribute_values",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="salestenderposition",
            name="attribute_values",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
