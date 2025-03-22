"""
Management command to process or remove job embeddings.

This command can be used to manually process embeddings for job openings or remove them.
"""

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    """Process or remove embeddings for job openings."""

    help = "Process or remove embeddings for job openings"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--job_id",
            type=int,
            help="Process a specific job opening ID",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Process all active job openings",
        )
        parser.add_argument(
            "--remove",
            action="store_true",
            help="Remove embeddings instead of creating them",
        )

    def handle(self, *args, **options):
        """Execute the command."""
        # Import tasks here to avoid loading issues during Django startup
        from apps.matching.tasks import (
            process_job_opening,
            remove_job_opening_embeddings,
        )

        # Get the JobOpening model
        JobOpening = apps.get_model("recruiters", "JobOpening")

        if options["job_id"]:
            job_id = options["job_id"]
            try:
                # Verify the job exists
                job = JobOpening.objects.get(id=job_id)
            except JobOpening.DoesNotExist:
                raise CommandError(f"JobOpening with ID {job_id} does not exist")

            if options["remove"]:
                self.stdout.write(f"Removing embeddings for job opening {job_id}")
                remove_job_opening_embeddings(job_id)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully removed embeddings for job opening {job_id}"
                    )
                )
            else:
                self.stdout.write(f"Processing embeddings for job opening {job_id}")
                process_job_opening(job_id)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully processed embeddings for job opening {job_id}"
                    )
                )

        elif options["all"]:
            # Query only active job openings
            jobs = JobOpening.objects.filter(is_active=True)
            count = jobs.count()

            if count == 0:
                self.stdout.write(self.style.WARNING("No active job openings found"))
                return

            self.stdout.write(f"Processing {count} active job openings")

            # Track success and failures
            success_count = 0
            failure_count = 0

            for job in jobs:
                try:
                    if options["remove"]:
                        remove_job_opening_embeddings(job.id)
                    else:
                        process_job_opening(job.id)
                    success_count += 1
                    self.stdout.write(f"Processed job opening {job.id}: {job.title}")
                except Exception as e:
                    failure_count += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f"Error processing job opening {job.id}: {str(e)}"
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
            self.stdout.write("  python manage.py process_job_embeddings --job_id=123")
            self.stdout.write("  python manage.py process_job_embeddings --all")
            self.stdout.write(
                "  python manage.py process_job_embeddings --all --remove"
            )
