"""
Management command to reset and enforce the cleanup task schedule.

This command forcefully resets the resume processing cleanup task schedule.
"""

import datetime

from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.utils import timezone
from django_q.models import Schedule
from django_q.tasks import schedule


class Command(BaseCommand):
    """Command to reset the resume processing cleanup task schedule."""

    help = "Forcefully resets the resume processing cleanup task schedule"

    def handle(self, *args, **options):
        """Execute the command."""
        self.stdout.write("Forcefully resetting cleanup task schedule...")

        # Delete ALL existing schedules for the cleanup task
        cleanup_schedules = Schedule.objects.filter(
            name="cleanup_resume_processing_progress"
        )

        count = cleanup_schedules.count()
        if count > 0:
            self.stdout.write(f"Deleting {count} existing schedule(s)...")
            cleanup_schedules.delete()

        # Calculate next run to be exactly at the next 15-minute mark
        now = timezone.now()
        minutes_to_add = 15 - (now.minute % 15)
        if minutes_to_add == 0:
            minutes_to_add = 15

        next_run = now + datetime.timedelta(minutes=minutes_to_add)
        next_run = next_run.replace(second=0, microsecond=0)

        self.stdout.write(f"Setting next run time to: {next_run}")

        new_schedule = schedule(
            "apps.resume_processing.tasks.cleanup_tasks.cleanup_resume_processing_progress",
            name="cleanup_resume_processing_progress",
            schedule_type=Schedule.MINUTES,
            minutes=15,
            next_run=next_run,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created new cleanup schedule (ID: {getattr(new_schedule, 'id', 'unknown')}) to run every 15 minutes starting at {next_run}"
            )
        )

        # Set a flag to ensure the middleware doesn't try to reschedule
        cache.set("job_seekers_cleanup_task_scheduled", True, 60 * 60 * 24)  # 24 hours

        self.stdout.write(self.style.SUCCESS("Schedule reset complete"))
