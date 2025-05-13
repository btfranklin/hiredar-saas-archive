from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("job_seekers", "0005_talentsheet_add_qualifications"),
    ]

    operations = [
        migrations.RenameField(
            model_name="talentsheet",
            old_name="skill_overview",
            new_name="experience_overview",
        ),
    ]
