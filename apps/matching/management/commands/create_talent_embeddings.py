"""
Management command to create talent embeddings.

This command can be used to manually create embeddings for talent sheets.
"""

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    """Create embeddings for talent sheets."""

    help = "Create embeddings for talent sheets"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--talent_id",
            type=int,
            help="Create embeddings for a specific talent sheet ID",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Create embeddings for all published talent sheets",
        )

    def handle(self, *args, **options):
        """Execute the command."""
        # Import task here to avoid loading issues during Django startup
        from apps.matching.tasks import create_talent_sheet_embeddings

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

            self.stdout.write(f"Creating embeddings for talent sheet {talent_id}")
            create_talent_sheet_embeddings(talent_id)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully created embeddings for talent sheet {talent_id}"
                )
            )

        elif options["all"]:
            # Query only published talent sheets
            talent_sheets = TalentSheet.objects.filter(is_published=True)
            count = talent_sheets.count()

            if count == 0:
                self.stdout.write(
                    self.style.WARNING("No published talent sheets found")
                )
                return

            self.stdout.write(
                f"Creating embeddings for {count} published talent sheets"
            )

            # Track success and failures
            success_count = 0
            failure_count = 0

            for talent_sheet in talent_sheets:
                try:
                    create_talent_sheet_embeddings(talent_sheet.id)
                    success_count += 1
                    self.stdout.write(
                        f"Created embeddings for talent sheet {talent_sheet.id}"
                    )
                except Exception as e:
                    failure_count += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f"Error creating embeddings for talent sheet {talent_sheet.id}: {str(e)}"
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
                "  python manage.py create_talent_embeddings --talent_id=123"
            )
            self.stdout.write("  python manage.py create_talent_embeddings --all")
