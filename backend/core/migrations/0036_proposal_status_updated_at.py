from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0035_approval_models_and_journal"),
    ]

    operations = [
        migrations.AddField(
            model_name="tenderproposal",
            name="status_updated_at",
            field=models.DateTimeField(
                auto_now=True,
                db_index=True,
                default=django.utils.timezone.now,
                help_text="Timestamp for delta sync of acceptance status changes.",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="salestenderproposal",
            name="status_updated_at",
            field=models.DateTimeField(
                auto_now=True,
                db_index=True,
                default=django.utils.timezone.now,
                help_text="Timestamp for delta sync of acceptance status changes.",
            ),
            preserve_default=False,
        ),
    ]
