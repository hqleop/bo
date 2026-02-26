from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0028_tendercriterion_tender_type_split"),
    ]

    operations = [
        migrations.CreateModel(
            name="CountryBusinessNumber",
            fields=[
                ("number_code", models.CharField(max_length=50, primary_key=True, serialize=False)),
                ("country_code", models.CharField(blank=True, default="", max_length=20)),
                ("number_name", models.CharField(max_length=255)),
            ],
            options={
                "db_table": "countrybusinessnumber",
                "managed": False,
                "ordering": ["number_name", "number_code"],
            },
        ),
        migrations.AddField(
            model_name="company",
            name="agree_participation_visibility",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="company",
            name="agree_privacy_policy",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="company",
            name="agree_trade_rules",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="company",
            name="company_address",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
        migrations.AddField(
            model_name="company",
            name="identity_document",
            field=models.FileField(blank=True, null=True, upload_to="company_registration_docs/%Y/%m/"),
        ),
        migrations.AddField(
            model_name="company",
            name="registration_country",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
        migrations.AddField(
            model_name="company",
            name="subject_type",
            field=models.CharField(
                choices=[
                    ("fop_resident", "ФОП (Резидент)"),
                    ("legal_resident", "Юридична особа (Резидент)"),
                    ("non_resident", "Не резидент"),
                    ("individual", "Фізична особа"),
                ],
                default="legal_resident",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="registration_step",
            field=models.PositiveSmallIntegerField(db_index=True, default=4),
        ),
    ]
