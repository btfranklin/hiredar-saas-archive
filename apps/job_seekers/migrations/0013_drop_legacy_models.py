"""Drop the remaining job seeker tables."""

from django.db import migrations


class Migration(migrations.Migration):
    """Remove legacy JobSeeker models now handled by the candidates app."""

    dependencies = [
        ("resume_processing", "0002_update_resume_processing_job_fk"),
        ("job_seekers", "0012_move_candidate_pool_to_candidates"),
    ]

    operations = [
        migrations.DeleteModel(name="TalentSheet"),
        migrations.DeleteModel(name="RoleRecommendation"),
        migrations.DeleteModel(name="JobSeekerProfile"),
    ]
