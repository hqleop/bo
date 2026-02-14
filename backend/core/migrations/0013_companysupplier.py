# Generated migration for CompanySupplier

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0012_add_cpv_categories_m2m"),
    ]

    operations = [
        migrations.CreateModel(
            name="CompanySupplier",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "source",
                    models.CharField(
                        choices=[("manual", "Додано вручну"), ("participation", "Участь у тендері")],
                        default="manual",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "owner_company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="supplier_relations",
                        to="core.company",
                    ),
                ),
                (
                    "supplier_company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="as_supplier_for",
                        to="core.company",
                    ),
                ),
            ],
            options={
                "verbose_name": "Постачальник компанії",
                "verbose_name_plural": "Постачальники компанії",
                "ordering": ["-created_at"],
                "unique_together": {("owner_company", "supplier_company")},
            },
        ),
    ]
