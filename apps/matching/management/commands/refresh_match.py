"""
Management command to refresh and analyze the match between a job seeker and job opening.

This command forcibly refreshes the match score between a job seeker and job opening by
clearing existing matches and triggering a fresh match computation.
"""

import json
from typing import Any

from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.authentication.models import User
from apps.job_seekers.models import JobSeekerProfile, TalentSheet
from apps.matching.core.matching import match_job_to_talents
from apps.matching.models import CandidateMatch
from apps.recruiters.models import JobOpening


class Command(BaseCommand):
    """Refresh and analyze a match between a job seeker and job opening."""

    help = "Refresh and analyze the match between a job seeker and job opening."

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "job_seeker_name",
            type=str,
            help="Name of the job seeker to analyze (partial match is supported)",
        )
        parser.add_argument(
            "job_title",
            type=str,
            help="Title of the job opening to analyze (partial match is supported)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Execute the command."""
        job_seeker_name = options["job_seeker_name"]
        job_title = options["job_title"]

        self.stdout.write(
            f"Refreshing match for job seeker '{job_seeker_name}' and job opening '{job_title}'"
        )

        # Find the job seeker by name
        users = User.objects.filter(
            Q(name__icontains=job_seeker_name) & Q(user_type="job_seeker")
        ).order_by("name")

        if not users.exists():
            self.stdout.write(
                self.style.ERROR(
                    f"No job seekers found with name containing '{job_seeker_name}'"
                )
            )
            return

        # If multiple users match, list them and exit
        if users.count() > 1:
            self.stdout.write(
                self.style.WARNING(
                    f"Found {users.count()} job seekers with name containing '{job_seeker_name}'"
                )
            )
            self.stdout.write("Please refine your search or select from the list:")
            for i, user in enumerate(users):
                self.stdout.write(f"{i+1}. {user.name} ({user.email})")
            return

        # Get the user
        user = users.first()
        self.stdout.write(
            self.style.SUCCESS(f"Found job seeker: {user.name} ({user.email})")
        )

        # Find the job opening by title
        job_openings = JobOpening.objects.filter(title__icontains=job_title).order_by(
            "title"
        )

        if not job_openings.exists():
            self.stdout.write(
                self.style.ERROR(
                    f"No job openings found with title containing '{job_title}'"
                )
            )
            return

        # If multiple job openings match, list them and exit
        if job_openings.count() > 1:
            self.stdout.write(
                self.style.WARNING(
                    f"Found {job_openings.count()} job openings with title containing '{job_title}'"
                )
            )
            self.stdout.write("Please refine your search or select from the list:")
            for i, job in enumerate(job_openings):
                self.stdout.write(f"{i+1}. {job.title} - {job.company}")
            return

        # Get the job opening
        job_opening = job_openings.first()
        self.stdout.write(
            self.style.SUCCESS(
                f"Found job opening: {job_opening.title} at {job_opening.company}"
            )
        )

        # Check if user has a job seeker profile
        try:
            profile = user.job_seeker_profile
        except JobSeekerProfile.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"Job seeker {user.name} does not have a profile")
            )
            return

        # Check if job seeker has a talent sheet
        try:
            talent_sheet = profile.talent_sheet
            self.stdout.write(
                f"Found talent sheet (Published: {'Yes' if talent_sheet.is_published else 'No'})"
            )

            if not talent_sheet.is_published:
                self.stdout.write(
                    self.style.WARNING(
                        "Talent sheet is not published - this is required for matching"
                    )
                )
                return

        except TalentSheet.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    f"Job seeker {user.name} does not have a talent sheet, which is required for matching"
                )
            )
            return

        # Delete existing matches
        existing_matches = CandidateMatch.objects.filter(
            job_opening=job_opening, talent_sheet=talent_sheet
        )

        if existing_matches.exists():
            count = existing_matches.count()
            existing_matches.delete()
            self.stdout.write(
                f"Deleted {count} existing matches between job seeker and job opening"
            )
        else:
            self.stdout.write("No existing matches found to delete")

        # Force job opening to active status for matching
        original_status = job_opening.status
        if job_opening.status != "active":
            self.stdout.write(
                f"Temporarily setting job opening status from '{job_opening.status}' to 'active' for matching"
            )
            job_opening.status = "active"
            job_opening.save(update_fields=["status"])

        try:
            # Run the match algorithm
            self.stdout.write("Running matching algorithm...")
            match_results = match_job_to_talents(job_opening.id, top_k=1)

            # Create a match if one was found
            if match_results["holistic_matches"]:
                # Get the match
                match_data = match_results["holistic_matches"][0]

                # Check if this matches our talent sheet
                match_talent_id = match_data["metadata"].get("talent_sheet_id")
                if str(match_talent_id) == str(talent_sheet.id):
                    # Create the match record
                    match_score = round(match_data["score"] * 100, 2)
                    match = CandidateMatch.objects.create(
                        job_opening=job_opening,
                        talent_sheet=talent_sheet,
                        match_type="holistic",
                        match_score=match_score,
                        status="identified",
                        is_analyzed=False,
                    )
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Created new match with score: {match_score}"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            f"The match algorithm did not return our talent sheet (expected {talent_sheet.id}, got {match_talent_id})"
                        )
                    )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        "The matching algorithm did not find any matches"
                    )
                )

            # Check all match types
            self.stdout.write("\nMatch results by type:")
            for match_type, matches in match_results.items():
                if matches:
                    self.stdout.write(f"  {match_type}: {len(matches)} matches found")
                    top_match = matches[0]
                    top_score = round(top_match["score"] * 100, 2)
                    top_talent_id = top_match["metadata"].get("talent_sheet_id")
                    self.stdout.write(
                        f"    Top match: Talent sheet {top_talent_id} with score {top_score}"
                    )
                else:
                    self.stdout.write(f"  {match_type}: No matches found")

        finally:
            # Restore original job status if it was changed
            if job_opening.status != original_status:
                self.stdout.write(
                    f"Restoring job opening status to '{original_status}'"
                )
                job_opening.status = original_status
                job_opening.save(update_fields=["status"])
