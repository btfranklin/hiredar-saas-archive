"""
Management command to create job embeddings.

This command can be used to manually create embeddings for job openings.
"""

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    """Create embeddings for job openings."""

    help = "Create embeddings for job openings"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--job_id",
            type=int,
            help="Create embeddings for a specific job opening ID",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Create embeddings for all active job openings",
        )

    def handle(self, *args, **options):
        """Execute the command."""
        # Import task here to avoid loading issues during Django startup
        from apps.matching.tasks import create_job_opening_embeddings

        # Get the JobOpening model
        JobOpening = apps.get_model("recruiters", "JobOpening")

        if options["job_id"]:
            job_id = options["job_id"]
            try:
                # Verify the job exists
                job = JobOpening.objects.get(id=job_id)
            except JobOpening.DoesNotExist as e:
                raise CommandError(f"JobOpening with ID {job_id} does not exist") from e

            self.stdout.write(f"Creating embeddings for job opening {job_id}")
            create_job_opening_embeddings(job_id)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully created embeddings for job opening {job_id}"
                )
            )

        elif options["all"]:
            # Query only active job openings
            jobs = JobOpening.objects.filter(status="active")
            count = jobs.count()

            if count == 0:
                self.stdout.write(self.style.WARNING("No active job openings found"))
                return

            self.stdout.write(f"Creating embeddings for {count} active job openings")

            # Track success and failures
            success_count = 0
            failure_count = 0

            for job in jobs:
                try:
                    create_job_opening_embeddings(job.id)
                    success_count += 1
                    self.stdout.write(
                        f"Created embeddings for job {job.id}: {job.title}"
                    )
                except Exception as e:
                    failure_count += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f"Error creating embeddings for job {job.id}: {str(e)}"
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
            self.stdout.write("  python manage.py create_job_embeddings --job_id=123")
            self.stdout.write("  python manage.py create_job_embeddings --all")
