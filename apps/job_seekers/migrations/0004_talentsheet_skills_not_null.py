from django.db import migrations, models


def backfill_skills(apps, schema_editor):
    TalentSheet = apps.get_model("job_seekers", "TalentSheet")
    TalentSheet.objects.filter(skills__isnull=True).update(skills="")


class Migration(migrations.Migration):

    dependencies = [
        ("job_seekers", "0003_talentsheet_add_skills"),
    ]

    operations = [
        migrations.RunPython(backfill_skills, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="talentsheet",
            name="skills",
            field=models.TextField(
                blank=True,
                help_text="Pipe-separated list of skills copied from JobSeekerProfile.skills for matching purposes",
            ),
        ),
    ]
