from django.db import migrations, models


def copy_skills_from_profile(apps, schema_editor):
    TalentSheet = apps.get_model("job_seekers", "TalentSheet")
    JobSeekerProfile = apps.get_model("job_seekers", "JobSeekerProfile")

    for sheet in TalentSheet.objects.all():
        try:
            profile = JobSeekerProfile.objects.get(pk=sheet.job_seeker_id)
            sheet.skills = profile.skills or ""
            sheet.save(update_fields=["skills"])
        except JobSeekerProfile.DoesNotExist:
            continue


class Migration(migrations.Migration):

    dependencies = [
        ("job_seekers", "0002_jobseekerprofile_jobseekerprofile_skills_trgm"),
    ]

    operations = [
        migrations.AddField(
            model_name="talentsheet",
            name="skills",
            field=models.TextField(
                blank=True,
                null=True,
                help_text="Pipe-separated list of skills copied from JobSeekerProfile.skills for matching purposes",
            ),
        ),
        migrations.RunPython(copy_skills_from_profile, migrations.RunPython.noop),
    ]
