"""
Management command to delete job embeddings.

This command can be used to manually delete embeddings for job openings.
"""

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    """Delete embeddings for job openings."""

    help = "Delete embeddings for job openings"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--job_id",
            type=int,
            help="Delete embeddings for a specific job opening ID",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Delete embeddings for all job openings",
        )

    def handle(self, *args, **options):
        """Execute the command."""
        # Import task here to avoid loading issues during Django startup
        from apps.matching.tasks import remove_job_opening_embeddings

        # Get the JobOpening model
        JobOpening = apps.get_model("recruiters", "JobOpening")

        if options["job_id"]:
            job_id = options["job_id"]
            try:
                # Verify the job exists
                job = JobOpening.objects.get(pk=job_id)
            except JobOpening.DoesNotExist as e:
                raise CommandError(f"JobOpening with ID {job_id} does not exist") from e

            self.stdout.write(f"Deleting embeddings for job opening {job_id}")
            remove_job_opening_embeddings(job_id)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully deleted embeddings for job opening {job_id}"
                )
            )

        elif options["all"]:
            # Get all job openings
            jobs = JobOpening.objects.all()
            count = jobs.count()

            if count == 0:
                self.stdout.write(self.style.WARNING("No job openings found"))
                return

            self.stdout.write(f"Deleting embeddings for {count} job openings")

            # Track success and failures
            success_count = 0
            failure_count = 0

            for job in jobs:
                try:
                    remove_job_opening_embeddings(job.pk)
                    success_count += 1
                    self.stdout.write(
                        f"Deleted embeddings for job {job.pk}: {job.title}"
                    )
                except Exception as e:
                    failure_count += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f"Error deleting embeddings for job {job.pk}: {str(e)}"
                        )
                    )

            # Report the results
            self.stdout.write(
                self.style.SUCCESS(
                    f"Completed with {success_count} successes and {failure_count} failures"
                )
            )

        else:
            self.stdout.write(
                self.style.WARNING("Please provide either --job_id or --all")
            )
            self.stdout.write("Examples:")
            self.stdout.write("  python manage.py delete_job_embeddings --job_id=123")
            self.stdout.write("  python manage.py delete_job_embeddings --all")
