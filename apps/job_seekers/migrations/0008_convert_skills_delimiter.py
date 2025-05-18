from django.db import migrations


def convert_pipe_to_newline(apps, schema_editor):
    """
    Convert existing JobSeekerProfile.skills from pipe-delimited to newline-delimited format.
    """
    JobSeekerProfile = apps.get_model("job_seekers", "JobSeekerProfile")
    for profile in JobSeekerProfile.objects.all():
        if profile.skills:
            lines = [s.strip() for s in profile.skills.split("|") if s.strip()]
            profile.skills = "\n".join(lines)
            profile.save(update_fields=["skills"])


class Migration(migrations.Migration):

    dependencies = [
        ("job_seekers", "0007_alter_talentsheet_experience_overview"),
    ]

    operations = [
        migrations.RunPython(convert_pipe_to_newline, migrations.RunPython.noop),
    ]
