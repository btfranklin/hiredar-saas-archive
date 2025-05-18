from django.db import migrations


def convert_pipe_to_newline(apps, schema_editor):
    """
    Convert existing JobOpening.required_skills and JobOpening.soft_skills from pipe-delimited
    to newline-delimited format.
    """
    JobOpening = apps.get_model("recruiters", "JobOpening")
    for job in JobOpening.objects.all():
        updated_fields = []
        if job.required_skills:
            lines = [s.strip() for s in job.required_skills.split("|") if s.strip()]
            job.required_skills = "\n".join(lines)
            updated_fields.append("required_skills")
        if job.soft_skills:
            lines = [s.strip() for s in job.soft_skills.split("|") if s.strip()]
            job.soft_skills = "\n".join(lines)
            updated_fields.append("soft_skills")
        if updated_fields:
            job.save(update_fields=updated_fields)


class Migration(migrations.Migration):

    dependencies = [
        ("recruiters", "0004_alter_bulkresumeupload_zip_file"),
    ]

    operations = [
        migrations.RunPython(convert_pipe_to_newline, migrations.RunPython.noop),
    ]
