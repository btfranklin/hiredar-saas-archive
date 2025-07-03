from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("recruiters", "0008_alter_recruiterprofile_total_candidates_shortlisted"),
    ]

    operations = [
        migrations.AddField(
            model_name="recruiterprofile",
            name="total_interest_requests_sent",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Total initial interest requests (new conversations) sent to candidates",
            ),
        ),
        migrations.AddField(
            model_name="recruiterprofile",
            name="total_messages_sent",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Total chat messages sent by the recruiter",
            ),
        ),
    ]
