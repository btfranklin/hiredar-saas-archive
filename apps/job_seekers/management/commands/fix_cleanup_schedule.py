"""
Management command to fix cleanup task scheduling issues.

This command inspects and repairs the resume processing cleanup task schedule.
"""

from django.core.management.base import BaseCommand
from django_q.models import Schedule
from django_q.tasks import schedule

from apps.resume_processing.tasks.cleanup_tasks import initialize_cleanup_once


class Command(BaseCommand):
    """Command to fix the resume processing cleanup task schedule."""

    help = "Diagnoses and fixes resume processing cleanup task scheduling issues"

    def handle(self, *args, **options):
        """Execute the command."""
        self.stdout.write("Checking resume processing cleanup task schedules...")

        # Find all schedules for the cleanup task
        cleanup_schedules = Schedule.objects.filter(
            func="apps.resume_processing.tasks.cleanup_tasks.cleanup_resume_processing_progress"
        )

        count = cleanup_schedules.count()
        self.stdout.write(f"Found {count} cleanup schedule(s)")

        if count == 0:
            self.stdout.write(
                self.style.WARNING(
                    "No schedules found. Disabling any stray schedule and running cleanup..."
                )
            )

            initialize_cleanup_once()
            self.stdout.write(
                self.style.SUCCESS(
                    "Successfully removed periodic schedule and ran cleanup once"
                )
            )
            return

        # Check if any schedule has incorrect settings
        wrong_minutes = [s for s in cleanup_schedules if s.minutes != 15]
        for wrong in wrong_minutes:
            self.stdout.write(
                self.style.WARNING(
                    f"Schedule {getattr(wrong, 'id', 'unknown')} has incorrect minutes: {wrong.minutes} (should be 15)"
                )
            )

        # If more than one schedule or any with wrong minutes, delete all and create a new one
        if count > 1 or wrong_minutes:
            self.stdout.write("Deleting all existing cleanup schedules...")
            cleanup_schedules.delete()

            self.stdout.write("Creating a new schedule with correct settings...")

            schedule(
                "apps.resume_processing.tasks.cleanup_tasks.cleanup_resume_processing_progress",
                name="cleanup_resume_processing_progress",
                schedule_type=Schedule.MINUTES,
                minutes=15,
            )

            self.stdout.write(
                self.style.SUCCESS(
                    "Successfully reset cleanup schedule to run every 15 minutes"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Cleanup schedule is correctly set up: {getattr(cleanup_schedules[0], 'id', 'unknown')}"
                )
            )

        # List all current schedules
        self.stdout.write("\nCurrent cleanup schedules:")
        for s in Schedule.objects.filter(
            func="apps.resume_processing.tasks.cleanup_tasks.cleanup_resume_processing_progress"
        ):
            self.stdout.write(
                f"ID: {getattr(s, 'id', 'unknown')}, Name: {s.name}, Minutes: {s.minutes}, Next: {s.next_run}"
            )
