from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0032_online_auction_position_pricing_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="TenderAttribute",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("type", models.CharField(choices=[("numeric", "Числовий"), ("text", "Текстовий"), ("date", "Дата")], max_length=20)),
                ("tender_type", models.CharField(choices=[("procurement", "Procurement"), ("sales", "Sales")], default="procurement", help_text="Tender type for attribute dictionary: procurement or sales.", max_length=20)),
                ("is_required", models.BooleanField(default=False, help_text="Ознака обов'язковості заповнення атрибута в позиції.")),
                ("options", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("category", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="tender_attributes", to="core.category")),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tender_attributes", to="core.company")),
            ],
            options={
                "verbose_name": "Атрибут тендеру",
                "verbose_name_plural": "Атрибути тендерів",
                "ordering": ["name"],
                "unique_together": {("company", "name", "type", "tender_type")},
            },
        ),
        migrations.AlterField(
            model_name="tendercriterion",
            name="type",
            field=models.CharField(choices=[("numeric", "Числовий"), ("text", "Текстовий"), ("date", "Дата"), ("file", "Файловий"), ("boolean", "Булевий (Так/Ні)")], max_length=20),
        ),
        migrations.AlterField(
            model_name="procurementtendercriterion",
            name="type",
            field=models.CharField(choices=[("numeric", "Числовий"), ("text", "Текстовий"), ("date", "Дата"), ("file", "Файловий"), ("boolean", "Булевий (Так/Ні)")], max_length=20),
        ),
        migrations.AlterField(
            model_name="salestendercriterion",
            name="type",
            field=models.CharField(choices=[("numeric", "Числовий"), ("text", "Текстовий"), ("date", "Дата"), ("file", "Файловий"), ("boolean", "Булевий (Так/Ні)")], max_length=20),
        ),
    ]
