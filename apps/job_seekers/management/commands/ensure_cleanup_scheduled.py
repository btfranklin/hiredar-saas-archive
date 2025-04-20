"""
Management command to ensure the resume processing cleanup task is scheduled.

This command can be run manually if needed to ensure the cleanup task is properly scheduled.
"""

import logging

from django.core.management.base import BaseCommand

from apps.resume_processing.tasks.cleanup_tasks import ensure_cleanup_scheduled


class Command(BaseCommand):
    """Command to ensure the resume processing cleanup task is scheduled."""

    help = "Ensures the resume processing cleanup task is scheduled in Django Q"

    def handle(self, *args, **options):
        """Execute the command."""
        self.stdout.write("Ensuring resume processing cleanup task is scheduled...")

        try:
            ensure_cleanup_scheduled()
            self.stdout.write(
                self.style.SUCCESS("Successfully verified/scheduled cleanup task")
            )
        except Exception as e:
            logging.getLogger(__name__).error(
                "Error ensuring cleanup task is scheduled: %s", e, exc_info=True
            )
            self.stdout.write(
                self.style.ERROR(f"Error ensuring cleanup task is scheduled: {e}")
            )
            return 1

        return 0
