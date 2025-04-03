"""
Matching task functions.

This module contains task functions for creating and removing matches between
job openings and talent sheets.
"""

# Use get_model to handle importing from another app without circular imports
from django.apps import apps
from django.db import transaction

# Import matching core
from apps.matching.core.matching import match_job_to_talents
from apps.matching.models import CandidateMatch

# Import shared utilities
from apps.matching.tasks.common import logger


def create_candidate_matches(job_id: int, **kwargs) -> None:
    """
    Create candidate matches for a job opening.

    Args:
        job_id: ID of the job opening to process
        **kwargs: Additional arguments (ignored)
    """
    try:
        JobOpening = apps.get_model("recruiters", "JobOpening")
        job = JobOpening.objects.get(id=job_id)

        if job.status != "active":
            logger.warning("Job opening %s is not active, skipping matching", job_id)
            return

        # Get matches from the matching system
        match_results = match_job_to_talents(job_id, top_k=20)

        # Process matches in a transaction
        with transaction.atomic():
            # Map of result keys to match types in the database
            match_type_mapping = {
                "holistic_matches": "holistic",
                "skills_matches": "skills",
                "experience_matches": "experience",
                "wildcard_matches": "wildcard",
            }

            # Process each type of match
            for result_key, match_type in match_type_mapping.items():
                if not match_results.get(result_key):
                    continue

                for match in match_results[result_key]:
                    # Convert score from 0-1 to 0-100 and round to 2 decimal places
                    score = round(match["score"] * 100, 2)

                    # Skip if below minimum score (50)
                    if score < 50:
                        continue

                    talent_sheet_id = match["metadata"]["talent_sheet_id"]

                    try:
                        # Get the talent sheet
                        TalentSheet = apps.get_model("job_seekers", "TalentSheet")
                        talent_sheet = TalentSheet.objects.get(id=talent_sheet_id)

                        # For non-holistic match types, only create them if a holistic match doesn't already exist
                        if (
                            match_type != "holistic"
                            and CandidateMatch.objects.filter(
                                job_opening=job,
                                talent_sheet=talent_sheet,
                                match_type="holistic",
                            ).exists()
                        ):
                            continue

                        # Create or update the match
                        CandidateMatch.objects.update_or_create(
                            job_opening=job,
                            talent_sheet=talent_sheet,
                            match_type=match_type,
                            defaults={
                                "match_score": score,
                                "is_analyzed": False,  # Reset analysis flag on update
                            },
                        )

                    except Exception as e:
                        logger.error(
                            "Error creating %s match for talent sheet %s: %s",
                            match_type,
                            talent_sheet_id,
                            e,
                        )

        logger.info("Created/updated matches for job opening %s", job_id)
    except Exception as e:
        logger.error("Error creating matches for job opening %s: %s", job_id, e)
        raise


def remove_job_opening_matches(job_id: int, **kwargs) -> None:
    """
    Remove all matches for a job opening.

    Args:
        job_id: ID of the job opening to process
        **kwargs: Additional arguments (ignored)
    """
    try:
        with transaction.atomic():
            CandidateMatch.objects.filter(job_opening_id=job_id).delete()
        logger.info("Removed matches for job opening %s", job_id)
    except Exception as e:
        logger.error("Error removing matches for job opening %s: %s", job_id, e)
        raise


def match_talent_to_active_jobs(talent_id: int, **kwargs) -> None:
    """
    Match a talent sheet against all active job openings.

    Args:
        talent_id: ID of the talent sheet to process
        **kwargs: Additional arguments (ignored)
    """
    try:
        JobOpening = apps.get_model("recruiters", "JobOpening")
        TalentSheet = apps.get_model("job_seekers", "TalentSheet")

        talent = TalentSheet.objects.get(id=talent_id)
        if not talent.is_published:
            logger.warning(
                "Talent sheet %s is not published, skipping matching", talent_id
            )
            return

        # Get all active jobs
        active_jobs = JobOpening.objects.filter(status="active")

        for job in active_jobs:
            try:
                # Get matches from the matching system
                match_results = match_job_to_talents(job.id, top_k=20)

                # Process matches in a transaction
                with transaction.atomic():
                    # Map of result keys to match types in the database
                    match_type_mapping = {
                        "holistic_matches": "holistic",
                        "skills_matches": "skills",
                        "experience_matches": "experience",
                        "wildcard_matches": "wildcard",
                    }

                    # Process each type of match
                    for result_key, match_type in match_type_mapping.items():
                        if not match_results.get(result_key):
                            continue

                        for match in match_results[result_key]:
                            # Convert score from 0-1 to 0-100 and round to 2 decimal places
                            score = round(match["score"] * 100, 2)

                            # Skip if below minimum score (50)
                            if score < 50:
                                continue

                            # Skip if not matching our talent sheet
                            if match["metadata"]["talent_sheet_id"] != talent_id:
                                continue

                            try:
                                # For non-holistic match types, only create them if a holistic match doesn't already exist
                                if (
                                    match_type != "holistic"
                                    and CandidateMatch.objects.filter(
                                        job_opening=job,
                                        talent_sheet=talent,
                                        match_type="holistic",
                                    ).exists()
                                ):
                                    continue

                                # Create or update the match
                                CandidateMatch.objects.update_or_create(
                                    job_opening=job,
                                    talent_sheet=talent,
                                    match_type=match_type,
                                    defaults={
                                        "match_score": score,
                                        "is_analyzed": False,  # Reset analysis flag on update
                                    },
                                )

                            except Exception as e:
                                logger.error(
                                    "Error creating %s match for job opening %s: %s",
                                    match_type,
                                    job.id,
                                    e,
                                )

            except Exception as e:
                logger.error("Error processing job opening %s: %s", job.id, e)

        logger.info("Created/updated matches for talent sheet %s", talent_id)
    except Exception as e:
        logger.error("Error creating matches for talent sheet %s: %s", talent_id, e)
        raise


def remove_talent_sheet_matches(talent_id: int, **kwargs) -> None:
    """
    Remove all matches for a talent sheet.

    Args:
        talent_id: ID of the talent sheet to process
        **kwargs: Additional arguments (ignored)
    """
    try:
        with transaction.atomic():
            CandidateMatch.objects.filter(talent_sheet_id=talent_id).delete()
        logger.info("Removed matches for talent sheet %s", talent_id)
    except Exception as e:
        logger.error("Error removing matches for talent sheet %s: %s", talent_id, e)
        raise
