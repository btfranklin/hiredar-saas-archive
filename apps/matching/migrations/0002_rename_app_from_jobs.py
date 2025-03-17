"""
Migration to rename app from jobs to matching.

This migration updates the ContentType table and handles data migration
from jobs.CandidateMatch to matching.CandidateMatch.
"""

from django.db import migrations


def update_content_types(apps, schema_editor):
    """
    Update content types to use the new app name.

    This function updates the ContentType entries to use 'matching' instead of 'jobs'
    for models now in the matching app.
    """
    ContentType = apps.get_model("contenttypes", "ContentType")

    # Update ContentType for CandidateMatch
    ContentType.objects.filter(app_label="jobs", model="candidatematch").update(
        app_label="matching"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("matching", "0001_initial"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(update_content_types),
    ]
