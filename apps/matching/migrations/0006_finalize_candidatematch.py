"""
Final migration for CandidateMatch model to complete the transition to TalentSheet relationship.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("matching", "0005_populate_talent_sheet"),
    ]

    operations = [
        # First, remove nullability constraint from talent_sheet
        migrations.AlterField(
            model_name="candidatematch",
            name="talent_sheet",
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE,
                related_name="job_matches",
                to="job_seekers.talentsheet",
            ),
        ),
        # Remove the old unique_together constraint
        migrations.AlterUniqueTogether(
            name="candidatematch",
            unique_together=set(),
        ),
        # Remove the job_seeker field
        migrations.RemoveField(
            model_name="candidatematch",
            name="job_seeker",
        ),
        # Add the new unique_together constraint
        migrations.AlterUniqueTogether(
            name="candidatematch",
            unique_together={("job_opening", "talent_sheet", "match_type")},
        ),
    ]
