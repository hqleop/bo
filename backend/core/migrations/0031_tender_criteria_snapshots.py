from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0030_tendercriterion_is_required"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProcurementTenderCriterion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("type", models.CharField(choices=[("numeric", "Числовий"), ("text", "Текстовий"), ("file", "Файловий"), ("boolean", "Булевий (Так/Ні)")], max_length=20)),
                ("application", models.CharField(choices=[("general", "Загальний"), ("individual", "Індивідуальний")], default="individual", max_length=20)),
                ("is_required", models.BooleanField(default=False)),
                ("options", models.JSONField(blank=True, default=dict)),
                ("reference_criterion", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="procurement_tender_snapshots", to="core.tendercriterion")),
                ("tender", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="criteria_items", to="core.procurementtender")),
            ],
            options={
                "verbose_name": "Критерій тендера на закупівлю (знімок)",
                "verbose_name_plural": "Критерії тендера на закупівлю (знімки)",
                "ordering": ["id"],
                "unique_together": {("tender", "reference_criterion")},
            },
        ),
        migrations.CreateModel(
            name="SalesTenderCriterion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("type", models.CharField(choices=[("numeric", "Числовий"), ("text", "Текстовий"), ("file", "Файловий"), ("boolean", "Булевий (Так/Ні)")], max_length=20)),
                ("application", models.CharField(choices=[("general", "Загальний"), ("individual", "Індивідуальний")], default="individual", max_length=20)),
                ("is_required", models.BooleanField(default=False)),
                ("options", models.JSONField(blank=True, default=dict)),
                ("reference_criterion", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sales_tender_snapshots", to="core.tendercriterion")),
                ("tender", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="criteria_items", to="core.salestender")),
            ],
            options={
                "verbose_name": "Критерій тендера на продаж (знімок)",
                "verbose_name_plural": "Критерії тендера на продаж (знімки)",
                "ordering": ["id"],
                "unique_together": {("tender", "reference_criterion")},
            },
        ),
    ]
