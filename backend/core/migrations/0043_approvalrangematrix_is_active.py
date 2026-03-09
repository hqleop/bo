from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0042_company_primary_color"),
    ]

    operations = [
        migrations.AddField(
            model_name="approvalrangematrix",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
    ]
