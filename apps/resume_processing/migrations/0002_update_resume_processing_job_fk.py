"""Historical no-op migration retained for compatibility."""

from django.db import migrations


class Migration(migrations.Migration):
    """Migration left intentionally empty after schema realignment."""

    dependencies = [
        ("resume_processing", "0001_initial"),
    ]

    operations = []
