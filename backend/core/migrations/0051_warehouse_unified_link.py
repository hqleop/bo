from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0050_warehouse_and_tender_position_warehouses"),
    ]

    operations = [
        migrations.AddField(
            model_name="warehouse",
            name="is_unified",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="warehouse",
            name="linked_warehouse",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="linked_warehouse_reverse",
                to="core.warehouse",
            ),
        ),
    ]
