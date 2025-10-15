"""Align ResumeProcessingJob with CandidateProfile."""

import django.db.models.deletion
from django.db import migrations, models


def clear_resume_processing_jobs(apps, schema_editor) -> None:
    """Remove legacy rows that pointed at JobSeekerProfile records."""
    ResumeProcessingJob = apps.get_model(
        "resume_processing", "ResumeProcessingJob"
    )
    ResumeProcessingJob.objects.all().delete()


class Migration(migrations.Migration):
    """Switch ResumeProcessingJob to reference CandidateProfile."""

    dependencies = [
        ("job_seekers", "0012_move_candidate_pool_to_candidates"),
        ("candidates", "0005_alter_candidateprofile_options"),
        ("resume_processing", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            clear_resume_processing_jobs, migrations.RunPython.noop
        ),
        migrations.RenameField(
            model_name="resumeprocessingjob",
            old_name="job_seeker_profile",
            new_name="candidate_profile",
        ),
        migrations.AlterField(
            model_name="resumeprocessingjob",
            name="candidate_profile",
            field=models.ForeignKey(
                help_text="Candidate profile that was processed",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="processing_jobs",
                to="candidates.candidateprofile",
            ),
        ),
    ]
