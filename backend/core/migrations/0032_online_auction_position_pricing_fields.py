from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0031_tender_criteria_snapshots"),
    ]

    operations = [
        migrations.AddField(
            model_name="procurementtenderposition",
            name="max_bid_step",
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                help_text="Максимальний крок ставки для класичних торгів.",
                max_digits=18,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="procurementtenderposition",
            name="min_bid_step",
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                help_text="Мінімальний крок ставки для класичних торгів.",
                max_digits=18,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="procurementtenderposition",
            name="start_price",
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                help_text="Стартова ціна для класичних торгів.",
                max_digits=18,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="salestenderposition",
            name="max_bid_step",
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                help_text="Максимальний крок ставки для класичних торгів.",
                max_digits=18,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="salestenderposition",
            name="min_bid_step",
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                help_text="Мінімальний крок ставки для класичних торгів.",
                max_digits=18,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="salestenderposition",
            name="start_price",
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                help_text="Стартова ціна для класичних торгів.",
                max_digits=18,
                null=True,
            ),
        ),
    ]
