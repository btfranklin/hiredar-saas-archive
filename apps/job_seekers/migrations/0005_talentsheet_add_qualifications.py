from django.db import migrations, models


def backfill_qualifications(apps, schema_editor):
    TalentSheet = apps.get_model("job_seekers", "TalentSheet")
    JobSeekerProfile = apps.get_model("job_seekers", "JobSeekerProfile")

    for sheet in TalentSheet.objects.all():
        try:
            profile = JobSeekerProfile.objects.get(pk=sheet.job_seeker_id)
        except JobSeekerProfile.DoesNotExist:
            continue

        education = profile.education or ""
        certifications = profile.certifications or ""
        parts = []
        if education:
            parts.append(education.strip())
        if certifications:
            parts.append(certifications.strip())
        qualifications = "\n\n".join(parts)
        sheet.qualifications = qualifications
        sheet.save(update_fields=["qualifications"])  # noqa: PERF401


class Migration(migrations.Migration):

    dependencies = [
        ("job_seekers", "0004_talentsheet_skills_not_null"),
    ]

    operations = [
        migrations.AddField(
            model_name="talentsheet",
            name="qualifications",
            field=models.TextField(
                blank=True,
                null=True,
                default="",
                help_text="Education and certifications concatenated from JobSeekerProfile for matching purposes",
            ),
        ),
        migrations.RunPython(backfill_qualifications, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="talentsheet",
            name="qualifications",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Education and certifications concatenated from JobSeekerProfile for matching purposes",
            ),
        ),
    ]
