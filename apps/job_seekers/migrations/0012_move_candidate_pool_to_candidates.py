"""Move CandidatePool model ownership to the candidates app."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Update state so CandidatePool lives in the candidates app."""

    dependencies = [
        ("candidates", "0001_initial"),
        ("job_seekers", "0011_alter_talentsheet_skills"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name="CandidatePool"),
            ],
            database_operations=[],
        ),
        migrations.AlterField(
            model_name="jobseekerprofile",
            name="candidate_pool",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="job_seeker_profiles",
                to="candidates.candidatepool",
            ),
        ),
    ]
