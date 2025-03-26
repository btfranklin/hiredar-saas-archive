"""
Management command to delete talent embeddings.

This command can be used to manually delete embeddings for talent sheets.
"""

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    """Delete embeddings for talent sheets."""

    help = "Delete embeddings for talent sheets"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--talent_id",
            type=int,
            help="Delete embeddings for a specific talent sheet ID",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Delete embeddings for all talent sheets",
        )

    def handle(self, *args, **options):
        """Execute the command."""
        # Import task here to avoid loading issues during Django startup
        from apps.matching.tasks import remove_talent_sheet_embeddings

        # Get the TalentSheet model
        TalentSheet = apps.get_model("job_seekers", "TalentSheet")

        if options["talent_id"]:
            talent_id = options["talent_id"]
            try:
                # Verify the talent sheet exists
                talent_sheet = TalentSheet.objects.get(id=talent_id)
            except TalentSheet.DoesNotExist as e:
                raise CommandError(
                    f"TalentSheet with ID {talent_id} does not exist"
                ) from e

            self.stdout.write(f"Deleting embeddings for talent sheet {talent_id}")
            remove_talent_sheet_embeddings(talent_id)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully deleted embeddings for talent sheet {talent_id}"
                )
            )

        elif options["all"]:
            # Get all talent sheets
            talent_sheets = TalentSheet.objects.all()
            count = talent_sheets.count()

            if count == 0:
                self.stdout.write(self.style.WARNING("No talent sheets found"))
                return

            self.stdout.write(f"Deleting embeddings for {count} talent sheets")

            # Track success and failures
            success_count = 0
            failure_count = 0

            for talent_sheet in talent_sheets:
                try:
                    remove_talent_sheet_embeddings(talent_sheet.id)
                    success_count += 1
                    self.stdout.write(
                        f"Deleted embeddings for talent sheet {talent_sheet.id}"
                    )
                except Exception as e:
                    failure_count += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f"Error deleting embeddings for talent sheet {talent_sheet.id}: {str(e)}"
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
                self.style.WARNING("Please provide either --talent_id or --all")
            )
            self.stdout.write("Examples:")
            self.stdout.write(
                "  python manage.py delete_talent_embeddings --talent_id=123"
            )
            self.stdout.write("  python manage.py delete_talent_embeddings --all")
