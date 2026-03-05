from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0036_proposal_status_updated_at"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="tenderproposal",
            index=models.Index(
                fields=["tender", "status_updated_at"],
                name="tp_tender_status_u_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="salestenderproposal",
            index=models.Index(
                fields=["tender", "status_updated_at"],
                name="stp_tender_status_u_idx",
            ),
        ),
    ]
