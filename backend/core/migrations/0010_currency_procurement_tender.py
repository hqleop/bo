# Generated manually for Currency and ProcurementTender

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def create_currencies(apps, schema_editor):
    Currency = apps.get_model("core", "Currency")
    Currency.objects.bulk_create([
        Currency(code="UAH", name="Гривня"),
        Currency(code="USD", name="Долар США"),
        Currency(code="EUR", name="Євро"),
    ])


def remove_currencies(apps, schema_editor):
    apps.get_model("core", "Currency").objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0009_add_tender_criterion"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Currency",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=10, unique=True)),
                ("name", models.CharField(max_length=100)),
            ],
            options={
                "verbose_name": "Валюта",
                "verbose_name_plural": "Валюти",
                "ordering": ["code"],
            },
        ),
        migrations.RunPython(create_currencies, remove_currencies),
        migrations.CreateModel(
            name="ProcurementTender",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tour_number", models.PositiveIntegerField(default=1)),
                ("number", models.PositiveIntegerField(blank=True, help_text="Порядковий номер тендера в компанії (присвоюється при першому збереженні)", null=True)),
                ("name", models.CharField(max_length=500)),
                ("stage", models.CharField(choices=[("passport", "Паспорт тендера"), ("preparation", "Підготовка процедури"), ("acceptance", "Прийом пропозицій"), ("decision", "Вибір рішення"), ("approval", "Затвердження"), ("completed", "Завершений")], default="passport", max_length=20)),
                ("estimated_budget", models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True)),
                ("conduct_type", models.CharField(choices=[("registration", "Реєстрація закупівлі"), ("rfx", "Збір пропозицій (RFx)"), ("online_auction", "Онлайн торги")], default="rfx", max_length=20)),
                ("publication_type", models.CharField(choices=[("open", "Відкрита процедура"), ("closed", "Закрита процедура")], default="open", max_length=20)),
                ("general_terms", models.TextField(blank=True, default="")),
                ("start_at", models.DateTimeField(blank=True, null=True)),
                ("end_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("branch", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="procurement_tenders", to="core.branch")),
                ("category", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="procurement_tenders", to="core.category")),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="procurement_tenders", to="core.company")),
                ("cpv_category", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="procurement_tenders", to="core.cpvdictionary")),
                ("currency", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="procurement_tenders", to="core.currency")),
                ("department", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="procurement_tenders", to="core.department")),
                ("expense_article", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="procurement_tenders", to="core.expensearticle")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_procurement_tenders", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Тендер на закупівлю",
                "verbose_name_plural": "Тендери на закупівлю",
                "ordering": ["-created_at"],
                "unique_together": {("company", "number", "tour_number")},
            },
        ),
        migrations.AddField(
            model_name="procurementtender",
            name="parent",
            field=models.ForeignKey(blank=True, help_text="Попередній тур, якщо це наступний тур того ж тендера", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="next_tours", to="core.procurementtender"),
        ),
    ]
