from django.db import migrations


def recalculate_years_of_experience(apps, schema_editor):
    # Get the historical model
    JobSeekerProfile = apps.get_model("job_seekers", "JobSeekerProfile")
    # Import the new calculation function
    from apps.resume_processing.utils.xml_parser import calculate_years_experience

    for profile in JobSeekerProfile.objects.all():
        xml_content = profile.resume_xml or ""
        if not xml_content:
            continue
        try:
            years = calculate_years_experience(xml_content)
            profile.years_of_experience = years
            profile.save(update_fields=["years_of_experience"])
        except Exception:
            # Skip any profiles that error out, leave them unchanged
            continue


class Migration(migrations.Migration):
    dependencies = [
        ("job_seekers", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            recalculate_years_of_experience,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
