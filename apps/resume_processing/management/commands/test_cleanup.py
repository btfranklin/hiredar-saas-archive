"""
Management command to test the cleanup task.

This command can be used to manually run the cleanup task for testing purposes.
"""

from django.core.management.base import BaseCommand

from apps.resume_processing.tasks.cleanup_tasks import (
    cleanup_resume_processing_progress,
)


class Command(BaseCommand):
    """Test the cleanup task manually."""

    help = "Run the resume processing cleanup task manually for testing"

    def handle(self, *args, **options):
        """Execute the cleanup task and report results."""
        self.stdout.write("Running cleanup task...")

        try:
            result = cleanup_resume_processing_progress()

            if result["status"] == "success":
                self.stdout.write(self.style.SUCCESS(f"✅ {result['message']}"))
                self.stdout.write(
                    f"   - Completed records cleaned: {result['completed_records']}"
                )
                self.stdout.write(f"   - Old records cleaned: {result['old_records']}")
            else:
                self.stdout.write(
                    self.style.ERROR(f"❌ Cleanup failed: {result['message']}")
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error running cleanup: {str(e)}"))
