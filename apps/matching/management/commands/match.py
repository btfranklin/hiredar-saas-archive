"""
Management command to run matching between talent sheets and job openings.

This command provides a CLI interface to test or manually invoke matching.
"""

import json
from typing import Any

from django.core.management.base import BaseCommand

from apps.matching.core.matching import match_job_to_talents, match_talent_to_jobs


class Command(BaseCommand):
    """Run matching for a TalentSheet or a JobOpening."""

    help = "Run matching for a TalentSheet or a JobOpening."

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--talent", type=int, help="TalentSheet id to match against JobOpenings"
        )
        parser.add_argument(
            "--job", type=int, help="JobOpening id to match against TalentSheets"
        )
        parser.add_argument(
            "--top_k",
            type=int,
            default=10,
            help="Number of matches to return per perspective",
        )
        parser.add_argument(
            "--format",
            choices=["json", "pretty"],
            default="pretty",
            help="Output format (json for machine readability, pretty for human readability)",
        )

    def handle(self, *args, **options):
        """Execute the command."""
        top_k = options.get("top_k", 10)
        output_format = options.get("format", "pretty")

        try:
            if options.get("talent"):
                talent_id = options["talent"]
                self.stdout.write(f"Running matching for TalentSheet {talent_id}...")
                results = match_talent_to_jobs(talent_id, top_k=top_k)

                if output_format == "json":
                    self.stdout.write(json.dumps(results))
                else:
                    self._print_pretty_results(results, "Job")

            elif options.get("job"):
                job_id = options["job"]
                self.stdout.write(f"Running matching for JobOpening {job_id}...")
                results = match_job_to_talents(job_id, top_k=top_k)

                if output_format == "json":
                    self.stdout.write(json.dumps(results))
                else:
                    self._print_pretty_results(results, "Talent")
            else:
                self.stdout.write(
                    self.style.WARNING(
                        "Please provide either --talent <id> or --job <id>."
                    )
                )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error during matching: {str(e)}"))

    def _print_pretty_results(self, results: dict[str, Any], entity_type: str):
        """
        Print results in a more human-readable format.

        Args:
            results: Dictionary of results by match type
            entity_type: "Job" or "Talent" to indicate what kind of entity was matched
        """
        for perspective, matches in results.items():
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n===== {perspective.replace('_', ' ').title()} ====="
                )
            )

            if not matches:
                self.stdout.write(self.style.WARNING(f"No {perspective} found."))
                continue

            for i, match in enumerate(matches, 1):
                vector_id = match.id
                score = match.score
                metadata = match.metadata or {}

                if entity_type == "Job":
                    title = metadata.get("title", "Unknown Job")
                    company = metadata.get("company", "Unknown Company")
                    location = metadata.get("location", "Remote/Unspecified")
                    self.stdout.write(
                        f"{i}. {title} at {company} ({location}) - Score: {score:.4f}"
                    )
                else:
                    name = metadata.get("job_seeker_name", "Unknown Candidate")
                    section = metadata.get("section", "Unknown Section")
                    self.stdout.write(f"{i}. {name} - {section} - Score: {score:.4f}")

                # Display a preview of the content if available
                if "content_preview" in metadata:
                    self.stdout.write(
                        f"   Preview: {metadata['content_preview'][:100]}..."
                    )

                self.stdout.write("")  # Empty line for spacing
