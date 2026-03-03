from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0034_tender_attributes_on_tenders_and_positions"),
    ]

    operations = [
        migrations.CreateModel(
            name="ApprovalModelRole",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("application", models.CharField(choices=[("procurement", "Тендер-Закупівля"), ("sales", "Тендер-Продаж")], default="procurement", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="approval_model_roles", to="core.company")),
            ],
            options={
                "verbose_name": "Роль моделі погодження",
                "verbose_name_plural": "Ролі моделей погодження",
                "ordering": ["name"],
                "unique_together": {("company", "name", "application")},
            },
        ),
        migrations.CreateModel(
            name="ApprovalRangeMatrix",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("budget_from", models.DecimalField(decimal_places=2, max_digits=18)),
                ("budget_to", models.DecimalField(decimal_places=2, max_digits=18)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="approval_range_matrix_items", to="core.company")),
                ("currency", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="approval_range_matrix_items", to="core.currency")),
            ],
            options={
                "verbose_name": "Діапазон матриці погодження",
                "verbose_name_plural": "Діапазони матриці погодження",
                "ordering": ["budget_from", "budget_to", "id"],
            },
        ),
        migrations.CreateModel(
            name="ApprovalModel",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("application", models.CharField(choices=[("procurement", "Тендер-Закупівля"), ("sales", "Тендер-Продаж")], default="procurement", max_length=20)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("categories", models.ManyToManyField(blank=True, related_name="approval_models", to="core.category")),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="approval_models", to="core.company")),
                ("ranges", models.ManyToManyField(blank=True, related_name="approval_models", to="core.approvalrangematrix")),
            ],
            options={
                "verbose_name": "Модель погодження",
                "verbose_name_plural": "Моделі погодження",
                "ordering": ["name"],
                "unique_together": {("company", "name", "application")},
            },
        ),
        migrations.CreateModel(
            name="ApprovalModelRoleUser",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("role", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="role_users", to="core.approvalmodelrole")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="approval_model_role_memberships", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Користувач ролі моделі погодження",
                "verbose_name_plural": "Користувачі ролей моделей погодження",
                "ordering": ["id"],
                "unique_together": {("role", "user")},
            },
        ),
        migrations.CreateModel(
            name="ApprovalModelStep",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order", models.PositiveIntegerField(default=1)),
                ("preparation_rule", models.CharField(choices=[("one_of", "Один зі"), ("all", "Усі")], default="one_of", max_length=20)),
                ("approval_rule", models.CharField(choices=[("one_of", "Один зі"), ("all", "Усі")], default="one_of", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("model", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="steps", to="core.approvalmodel")),
                ("role", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="model_steps", to="core.approvalmodelrole")),
            ],
            options={
                "verbose_name": "Крок моделі погодження",
                "verbose_name_plural": "Кроки моделі погодження",
                "ordering": ["order", "id"],
                "unique_together": {("model", "role", "order")},
            },
        ),
        migrations.AddField(
            model_name="procurementtender",
            name="approval_model",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="procurement_tenders", to="core.approvalmodel"),
        ),
        migrations.AddField(
            model_name="salestender",
            name="approval_model",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sales_tenders", to="core.approvalmodel"),
        ),
        migrations.CreateModel(
            name="TenderApprovalJournal",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("stage", models.CharField(blank=True, default="", max_length=20)),
                ("action", models.CharField(choices=[("approved", "Погоджено"), ("rejected", "Скасовано")], max_length=20)),
                ("comment", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("procurement_tender", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="approval_journal_entries", to="core.procurementtender")),
                ("sales_tender", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="approval_journal_entries", to="core.salestender")),
            ],
            options={
                "verbose_name": "Запис журналу погодження",
                "verbose_name_plural": "Журнал погодження",
                "ordering": ["-created_at", "-id"],
            },
        ),
    ]
