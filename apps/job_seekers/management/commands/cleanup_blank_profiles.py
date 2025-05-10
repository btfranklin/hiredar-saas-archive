from django.core.management.base import BaseCommand

from apps.job_seekers.models import JobSeekerProfile


class Command(BaseCommand):
    """Delete junk JobSeekerProfile rows that have no meaningful data.

    A profile is considered *blank* if **both** of the following are true:
    1. `candidate_name` is empty/null
    2. `skills` is empty/null
    """

    help = "Remove blank JobSeekerProfile rows"

    def handle(self, *args: str, **options):  # noqa: D401 – management command entry
        blank_profiles = JobSeekerProfile.objects.filter(candidate_name="", skills="")
        total = blank_profiles.count()
        if total == 0:
            self.stdout.write(
                self.style.SUCCESS("No blank profiles found – nothing to do.")
            )
            return

        # Collect IDs for logging before deletion
        ids = list(blank_profiles.values_list("id", flat=True))
        blank_profiles.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {total} blank JobSeekerProfile rows (IDs: {', '.join(map(str, ids))})."
            )
        )
