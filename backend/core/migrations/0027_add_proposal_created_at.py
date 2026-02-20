from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0026_add_proposal_submitted_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="tenderproposal",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, blank=True, null=True),
        ),
        migrations.AddField(
            model_name="salestenderproposal",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, blank=True, null=True),
        ),
    ]

