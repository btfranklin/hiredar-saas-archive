"""Remove salary expectation field from CandidateProfile."""

from django.db import migrations


class Migration(migrations.Migration):
    """Drop the salary_min column now that candidates come solely from resumes."""

    dependencies = [
        ("candidates", "0002_candidateprofile"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="candidateprofile",
            name="salary_min",
        ),
    ]

