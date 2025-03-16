"""
Command to clean up old TaskProgress records.

This management command deletes old TaskProgress records to prevent
database bloat from accumulating completed or failed tasks.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.job_seekers.models import TaskProgress


class Command(BaseCommand):
    """Command to clean up old TaskProgress records."""

    help = "Clean up old TaskProgress records that are no longer needed"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--days",
            type=int,
            default=7,
            help="Delete records older than this many days (default: 7)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting",
        )

    def handle(self, *args, **options):
        """Execute the command."""
        days = options["days"]
        dry_run = options["dry_run"]

        # Get cutoff date for records to delete
        cutoff_date = timezone.now() - timedelta(days=days)

        # Query records that would be deleted
        records_to_delete = TaskProgress.objects.filter(created_at__lt=cutoff_date)
        count = records_to_delete.count()

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"Would delete {count} TaskProgress records older than {days} days"
                )
            )

            # Show summary by status
            status_counts = {}
            for record in records_to_delete:
                status_counts[record.status] = status_counts.get(record.status, 0) + 1

            for status, status_count in status_counts.items():
                self.stdout.write(f"  {status}: {status_count}")

            self.stdout.write(
                self.style.SUCCESS("Dry run completed. No records deleted.")
            )
        else:
            # Actually delete the records
            deleted_count = TaskProgress.clean_up_old_records(days)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully deleted {deleted_count} TaskProgress records older than {days} days"
                )
            )
