from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0043_approvalrangematrix_is_active"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TenderConditionTemplate",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("content", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tender_condition_templates",
                        to="core.company",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_tender_condition_templates",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Шаблон умов тендера",
                "verbose_name_plural": "Шаблони умов тендера",
                "ordering": ["name", "id"],
                "unique_together": {("company", "name")},
            },
        ),
        migrations.AddField(
            model_name="procurementtender",
            name="auction_model",
            field=models.CharField(
                choices=[("classic_auction", "Класичний аукціон")],
                default="classic_auction",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="procurementtender",
            name="planned_end_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="procurementtender",
            name="planned_start_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="salestender",
            name="auction_model",
            field=models.CharField(
                choices=[("classic_auction", "Класичний аукціон")],
                default="classic_auction",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="salestender",
            name="planned_end_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="salestender",
            name="planned_start_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
