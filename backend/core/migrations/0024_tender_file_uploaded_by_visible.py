# Add uploaded_by and visible_to_participants to tender file models only

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_tender_files_uploaded_by_visible'),
    ]

    operations = [
        migrations.AddField(
            model_name='procurementtenderfile',
            name='uploaded_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='procurementtenderfile',
            name='visible_to_participants',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='salestenderfile',
            name='uploaded_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='salestenderfile',
            name='visible_to_participants',
            field=models.BooleanField(default=True),
        ),
    ]
