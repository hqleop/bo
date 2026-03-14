from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0048_tender_invitations_and_invited_emails"),
    ]

    operations = [
        migrations.AddField(
            model_name="approvalmodelrole",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="branch",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="category",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="department",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="expensearticle",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="tenderattribute",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="tendercriterion",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
    ]
