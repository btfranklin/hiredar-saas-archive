"""
Management command to create candidate matches for job openings.

This command processes all active job openings and identifies matching talent sheets,
creating or updating CandidateMatch objects based on the match scores.
"""

import logging
from decimal import Decimal

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.matching.core.matching import match_job_to_talents
from apps.matching.models import CandidateMatch

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Create candidate matches for job openings."""

    help = "Generate candidate matches for active job openings."

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
            "--min_score",
            type=float,
            default=50.0,
            help="Minimum match score to create a match (default: 50.0)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit the number of job openings to process",
        )

    def handle(self, *args, **options):
        """Execute the command."""
        # Get the JobOpening model
        JobOpening = apps.get_model("recruiters", "JobOpening")
        JobSeekerProfile = apps.get_model("job_seekers", "JobSeekerProfile")

        min_score = options["min_score"]
        if min_score < 0 or min_score > 100:
            self.stderr.write(
                self.style.ERROR("Minimum score must be between 0 and 100")
            )
            return

        if options["job_id"]:
            job_id = options["job_id"]
            try:
                job = JobOpening.objects.get(id=job_id)
                if job.status != "active":
                    self.stderr.write(
                        self.style.WARNING(f"Job opening {job_id} is not active.")
                    )
                    return
                self.process_job_opening(job, min_score)
            except JobOpening.DoesNotExist:
                self.stderr.write(
                    self.style.ERROR(f"Job opening with ID {job_id} does not exist")
                )
                return
        elif options["all"]:
            # Query active job openings
            jobs = JobOpening.objects.filter(status="active")

            if options["limit"]:
                jobs = jobs[: options["limit"]]

            job_count = jobs.count()

            if job_count == 0:
                self.stdout.write(self.style.WARNING("No active job openings found"))
                return

            self.stdout.write(f"Processing {job_count} active job openings")

            # Track success and failures
            success_count = 0
            failure_count = 0

            for job in jobs:
                try:
                    num_matches = self.process_job_opening(job, min_score)
                    success_count += 1
                    self.stdout.write(
                        f"Processed job opening {job.id}: {job.title} - Created/updated {num_matches} matches"
                    )
                except Exception as e:
                    failure_count += 1
                    self.stderr.write(
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
            self.stdout.write(
                "  python manage.py create_candidate_matches --job_id=123"
            )
            self.stdout.write("  python manage.py create_candidate_matches --all")
            self.stdout.write(
                "  python manage.py create_candidate_matches --all --min_score=60"
            )

    def process_job_opening(self, job, min_score):
        """
        Process a single job opening, find matching talents and create CandidateMatch objects.

        Args:
            job: JobOpening instance
            min_score: Minimum match score to create a match

        Returns:
            Number of matches created or updated
        """
        self.stdout.write(f"Finding matches for job opening {job.id}: {job.title}")

        # Get talents that match this job across all matching perspectives
        match_results = match_job_to_talents(job.id, top_k=20)

        # Count matches created
        match_count = 0

        # Process all match types
        with transaction.atomic():
            # Map of result keys to match types in the database
            match_type_mapping = {
                "top_matches": "holistic",
                "best_skills_fit": "skills",
                "experience_matches": "experience",
                "wildcard_matches": "wildcard",
            }

            # Process each type of match
            for result_key, match_type in match_type_mapping.items():
                # Skip if no matches of this type
                if not match_results.get(result_key):
                    continue

                for match in match_results[result_key]:
                    # Convert score from 0-1 to 0-100 and round to 2 decimal places
                    score = Decimal(str(round(match["score"] * 100, 2)))

                    # Skip if below minimum score
                    if score < min_score:
                        continue

                    talent_sheet_id = match["metadata"]["talent_sheet_id"]

                    try:
                        # Get the job seeker profile associated with this talent sheet
                        job_seeker = (
                            apps.get_model("job_seekers", "TalentSheet")
                            .objects.get(id=talent_sheet_id)
                            .job_seeker
                        )

                        # For non-holistic match types, only create them if a holistic match doesn't already exist
                        # for this job seeker and job opening
                        if (
                            match_type != "holistic"
                            and CandidateMatch.objects.filter(
                                job_opening=job,
                                job_seeker=job_seeker,
                                match_type="holistic",
                            ).exists()
                        ):
                            continue

                        # Create or update the match
                        candidate_match, created = (
                            CandidateMatch.objects.update_or_create(
                                job_opening=job,
                                job_seeker=job_seeker,
                                match_type=match_type,
                                defaults={
                                    "match_score": score,
                                },
                            )
                        )

                        match_count += 1

                    except Exception as e:
                        self.stderr.write(
                            self.style.ERROR(
                                f"Error creating {match_type} match for talent sheet {talent_sheet_id}: {str(e)}"
                            )
                        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Created/updated {match_count} matches for job opening {job.id}"
            )
        )

        return match_count
