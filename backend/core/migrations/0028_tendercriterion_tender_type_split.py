from django.db import migrations, models


def set_tender_type_for_existing_criteria(apps, schema_editor):
    TenderCriterion = apps.get_model("core", "TenderCriterion")
    for criterion in TenderCriterion.objects.all():
        has_sales = criterion.sales_tenders.exists()
        has_procurement = criterion.procurement_tenders.exists()
        if has_sales and not has_procurement:
            criterion.tender_type = "sales"
        else:
            criterion.tender_type = "procurement"
        criterion.save(update_fields=["tender_type"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0028_currency_code_iso"),
    ]

    operations = [
        migrations.AddField(
            model_name="tendercriterion",
            name="tender_type",
            field=models.CharField(
                choices=[("procurement", "Procurement"), ("sales", "Sales")],
                default="procurement",
                help_text="Tender type for criterion dictionary: procurement or sales.",
                max_length=20,
            ),
        ),
        migrations.RunPython(
            set_tender_type_for_existing_criteria,
            migrations.RunPython.noop,
        ),
        migrations.AlterUniqueTogether(
            name="tendercriterion",
            unique_together={("company", "name", "type", "tender_type")},
        ),
    ]
