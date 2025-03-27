import logging

from django.core.management.base import BaseCommand

from apps.matching.models import CandidateMatch

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Delete all candidate matches from the system"

    def add_arguments(self, parser):
        # Add verbosity option
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show detailed information about deleted matches",
        )

    def handle(self, *args, **options):
        verbose = options.get("verbose", False)
        verbosity = options.get("verbosity", 1)

        try:
            # Get total count before deletion
            total_matches = CandidateMatch.objects.count()

            if total_matches == 0:
                self.stdout.write(
                    self.style.WARNING("No candidate matches found in the system.")
                )
                return

            # Display information about what will be deleted
            self.stdout.write(
                self.style.WARNING(
                    f"About to delete {total_matches} candidate matches from the system."
                )
            )

            if verbose and verbosity >= 2:
                # Show breakdown by job opening
                job_counts = {}
                for match in CandidateMatch.objects.all():
                    job_id = match.job_opening.id if match.job_opening else "Unknown"
                    job_title = (
                        match.job_opening.title if match.job_opening else "Unknown"
                    )
                    key = f"{job_id} ({job_title})"
                    job_counts[key] = job_counts.get(key, 0) + 1

                self.stdout.write("\nMatches by job opening:")
                for job, count in job_counts.items():
                    self.stdout.write(f"  - {job}: {count} matches")

            # Confirm deletion
            if verbosity >= 2:
                confirm = input(
                    "\nAre you sure you want to delete all matches? [y/N]: "
                )
                if confirm.lower() != "y":
                    self.stdout.write(self.style.WARNING("Operation cancelled."))
                    return

            # Perform deletion
            CandidateMatch.objects.all().delete()

            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully deleted {total_matches} candidate matches."
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error flushing candidate matches: {str(e)}")
            )
            if verbosity >= 2:
                raise
