from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0049_reference_entities_is_active"),
    ]

    operations = [
        migrations.CreateModel(
            name="Warehouse",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "warehouse_type",
                    models.CharField(
                        choices=[
                            ("shipment", "Склад відвантаження"),
                            ("delivery", "Склад для поставки"),
                        ],
                        default="shipment",
                        max_length=20,
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("region", models.CharField(blank=True, default="", max_length=255)),
                ("locality", models.CharField(blank=True, default="", max_length=255)),
                ("street", models.CharField(blank=True, default="", max_length=255)),
                ("building", models.CharField(blank=True, default="", max_length=255)),
                ("unit", models.CharField(blank=True, default="", max_length=255)),
                ("postal_code", models.CharField(blank=True, default="", max_length=32)),
                ("full_address", models.TextField(blank=True, default="")),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="warehouses",
                        to="core.company",
                    ),
                ),
            ],
            options={
                "verbose_name": "Склад",
                "verbose_name_plural": "Склади",
                "ordering": ["warehouse_type", "region", "locality", "name", "id"],
                "unique_together": {("company", "warehouse_type", "name")},
            },
        ),
        migrations.AddField(
            model_name="procurementtender",
            name="uses_position_warehouses",
            field=models.BooleanField(
                default=False,
                help_text="Ознака використання складів по позиціях тендера.",
            ),
        ),
        migrations.AddField(
            model_name="salestender",
            name="uses_position_warehouses",
            field=models.BooleanField(
                default=False,
                help_text="Ознака використання складів по позиціях тендера.",
            ),
        ),
        migrations.AddField(
            model_name="procurementtenderposition",
            name="warehouse",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="procurement_tender_positions",
                to="core.warehouse",
            ),
        ),
        migrations.AddField(
            model_name="salestenderposition",
            name="warehouse",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="sales_tender_positions",
                to="core.warehouse",
            ),
        ),
    ]
