"""
Management command to process or remove talent sheet embeddings.

This command can be used to manually process embeddings for talent sheets or remove them.
"""

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    """Process or remove embeddings for talent sheets."""

    help = "Process or remove embeddings for talent sheets"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--talent_id",
            type=int,
            help="Process a specific talent sheet ID",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Process all published talent sheets",
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
            process_talent_sheet,
            remove_talent_sheet_embeddings,
        )

        # Get the TalentSheet model
        TalentSheet = apps.get_model("job_seekers", "TalentSheet")

        if options["talent_id"]:
            talent_id = options["talent_id"]
            try:
                # Verify the talent sheet exists
                talent_sheet = TalentSheet.objects.get(id=talent_id)
            except TalentSheet.DoesNotExist:
                raise CommandError(f"TalentSheet with ID {talent_id} does not exist")

            if options["remove"]:
                self.stdout.write(f"Removing embeddings for talent sheet {talent_id}")
                remove_talent_sheet_embeddings(talent_id)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully removed embeddings for talent sheet {talent_id}"
                    )
                )
            else:
                self.stdout.write(f"Processing embeddings for talent sheet {talent_id}")
                process_talent_sheet(talent_id)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully processed embeddings for talent sheet {talent_id}"
                    )
                )

        elif options["all"]:
            # Query only published talent sheets
            talent_sheets = TalentSheet.objects.filter(status="PUBLISHED")
            count = talent_sheets.count()

            if count == 0:
                self.stdout.write(
                    self.style.WARNING("No published talent sheets found")
                )
                return

            self.stdout.write(f"Processing {count} published talent sheets")

            # Track success and failures
            success_count = 0
            failure_count = 0

            for talent_sheet in talent_sheets:
                try:
                    if options["remove"]:
                        remove_talent_sheet_embeddings(talent_sheet.id)
                    else:
                        process_talent_sheet(talent_sheet.id)
                    success_count += 1
                    self.stdout.write(f"Processed talent sheet {talent_sheet.id}")
                except Exception as e:
                    failure_count += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f"Error processing talent sheet {talent_sheet.id}: {str(e)}"
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
                "  python manage.py process_talent_embeddings --talent_id=123"
            )
            self.stdout.write("  python manage.py process_talent_embeddings --all")
            self.stdout.write(
                "  python manage.py process_talent_embeddings --all --remove"
            )
