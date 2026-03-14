from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0047_tenderproposal_created_by_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="procurementtender",
            name="invited_emails",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="salestender",
            name="invited_emails",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.CreateModel(
            name="ProcurementTenderInvitation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("supplier_company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="invited_procurement_tenders", to="core.company")),
                ("tender", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="invited_supplier_links", to="core.procurementtender")),
            ],
            options={
                "verbose_name": "Запрошений контрагент тендера на закупівлю",
                "verbose_name_plural": "Запрошені контрагенти тендерів на закупівлю",
                "ordering": ["supplier_company__name", "id"],
                "unique_together": {("tender", "supplier_company")},
            },
        ),
        migrations.CreateModel(
            name="SalesTenderInvitation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("supplier_company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="invited_sales_tenders", to="core.company")),
                ("tender", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="invited_supplier_links", to="core.salestender")),
            ],
            options={
                "verbose_name": "Запрошений контрагент тендера на продаж",
                "verbose_name_plural": "Запрошені контрагенти тендерів на продаж",
                "ordering": ["supplier_company__name", "id"],
                "unique_together": {("tender", "supplier_company")},
            },
        ),
    ]
