"""
Data migration to populate the talent_sheet field in CandidateMatch model.
"""

from django.db import migrations


def populate_talent_sheet(apps, schema_editor):
    """
    Populate the talent_sheet field using job_seeker relationships.

    For each CandidateMatch, find the TalentSheet that belongs to the job_seeker
    and associate it with the match.
    """
    CandidateMatch = apps.get_model("matching", "CandidateMatch")
    TalentSheet = apps.get_model("job_seekers", "TalentSheet")

    # Get all candidate matches
    for match in CandidateMatch.objects.all():
        if match.job_seeker:
            try:
                # Find the talent sheet for this job seeker
                talent_sheet = TalentSheet.objects.get(job_seeker=match.job_seeker)
                match.talent_sheet = talent_sheet
                match.save(update_fields=["talent_sheet"])
            except TalentSheet.DoesNotExist:
                # No talent sheet exists for this job seeker
                print(f"No talent sheet found for job seeker ID {match.job_seeker.id}")
            except TalentSheet.MultipleObjectsReturned:
                # Multiple talent sheets exist - use the most recently created one
                talent_sheet = (
                    TalentSheet.objects.filter(job_seeker=match.job_seeker)
                    .order_by("-created_at")
                    .first()
                )
                match.talent_sheet = talent_sheet
                match.save(update_fields=["talent_sheet"])
                print(
                    f"Multiple talent sheets found for job seeker ID {match.job_seeker.id}, using most recent"
                )


def reverse_migration(apps, schema_editor):
    """
    No-op reverse migration.

    We're not reverting the talent_sheet field since we keep both fields for now.
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("matching", "0004_add_talent_sheet_field"),
    ]

    operations = [
        migrations.RunPython(populate_talent_sheet, reverse_migration),
    ]
