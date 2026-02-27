from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0029_registration_flow_update"),
    ]

    operations = [
        migrations.AddField(
            model_name="tendercriterion",
            name="is_required",
            field=models.BooleanField(
                default=False,
                help_text="Ознака обов'язковості заповнення критерію при подачі пропозиції.",
            ),
        ),
    ]
