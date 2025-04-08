"""
Management command to re-run matching for all active job openings.

This is a one-time fix for the section filter issue, where previous matches
may have been missed due to incorrect filter formatting.
"""

import logging
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.matching.tasks import create_candidate_matches
from apps.recruiters.models import JobOpening

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Re-run matching for all active job openings to fix section filter issue"

    def add_arguments(self, parser):
        parser.add_argument(
            "--delete-existing",
            action="store_true",
            help="Delete existing matches before creating new ones",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        delete_existing = options["delete_existing"]

        # Get all active job openings
        active_jobs = JobOpening.objects.filter(status="active")
        job_count = active_jobs.count()

        if job_count == 0:
            self.stdout.write(self.style.WARNING("No active job openings found"))
            return

        self.stdout.write(f"Found {job_count} active job openings")

        # Re-run matching for each job
        success_count = 0
        error_count = 0

        for job in active_jobs:
            try:
                self.stdout.write(f"Re-matching job {job.id}: {job.title}")

                # Delete existing matches if requested
                if delete_existing:
                    from apps.matching.models import CandidateMatch

                    with transaction.atomic():
                        deleted, _ = CandidateMatch.objects.filter(
                            job_opening=job
                        ).delete()
                        self.stdout.write(f"  Deleted {deleted} existing matches")

                # Use the same function that's used for regular matching
                create_candidate_matches(job.id)

                success_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"  ✓ Successfully re-matched job {job.id}")
                )

            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f"  ✗ Error re-matching job {job.id}: {str(e)}")
                )
                logger.exception("Error re-matching job %s", job.id)

        # Print summary
        self.stdout.write("\n=== Summary ===")
        self.stdout.write(f"Total jobs processed: {job_count}")
        self.stdout.write(self.style.SUCCESS(f"Successful re-matches: {success_count}"))

        if error_count > 0:
            self.stdout.write(self.style.ERROR(f"Failed re-matches: {error_count}"))
        else:
            self.stdout.write("Failed re-matches: 0")
