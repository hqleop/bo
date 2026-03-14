from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0045_salestenderproposal_disqualification_comment_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="tenderchatthread",
            name="owner_last_read_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="tenderchatthread",
            name="supplier_last_read_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
