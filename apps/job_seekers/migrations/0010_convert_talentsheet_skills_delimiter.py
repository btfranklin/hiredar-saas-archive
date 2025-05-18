from django.db import migrations


def convert_pipe_to_newline(apps, schema_editor):
    """
    Convert existing TalentSheet.skills from pipe-delimited to newline-delimited format.
    """
    TalentSheet = apps.get_model("job_seekers", "TalentSheet")
    for sheet in TalentSheet.objects.all():
        if sheet.skills and "|" in sheet.skills:
            lines = [s.strip() for s in sheet.skills.split("|") if s.strip()]
            sheet.skills = "\n".join(lines)
            sheet.save(update_fields=["skills"])


class Migration(migrations.Migration):

    dependencies = [
        ("job_seekers", "0009_alter_jobseekerprofile_skills"),
    ]

    operations = [
        migrations.RunPython(convert_pipe_to_newline, migrations.RunPython.noop),
    ]
