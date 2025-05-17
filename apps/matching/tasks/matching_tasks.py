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
                "qualifications_matches": "qualifications",
            }

            # Store all matches by talent sheet ID for quick lookup later
            all_matches_by_talent = {}

            # First pass: collect all matches by talent sheet ID
            for result_key, match_type in match_type_mapping.items():
                matches = match_results.get(result_key, [])

                for match in matches:
                    talent_sheet_id = match["metadata"]["talent_sheet_id"]
                    # Store raw score (0-1 range) directly from Pinecone
                    score = match["score"]

                    if talent_sheet_id not in all_matches_by_talent:
                        all_matches_by_talent[talent_sheet_id] = {}

                    all_matches_by_talent[talent_sheet_id][match_type] = score

            # Process each type of match
            for result_key, match_type in match_type_mapping.items():
                if not match_results.get(result_key):
                    continue

                for match in match_results[result_key]:
                    # Use raw score (0-1 range) directly from Pinecone
                    score = match["score"]

                    # Skip if below minimum score (0.5)
                    if score < 0.5:
                        continue

                    talent_sheet_id = match["metadata"]["talent_sheet_id"]

                    # Get all match scores for this talent
                    talent_scores = all_matches_by_talent.get(talent_sheet_id, {})

                    # Get the scores for different match types, default to 0
                    holistic_score = talent_scores.get("holistic", 0)
                    skills_score = talent_scores.get("skills", 0)
                    experience_score = talent_scores.get("experience", 0)
                    wildcard_score = talent_scores.get("wildcard", 0)
                    qualifications_score = talent_scores.get("qualifications", 0)

                    try:
                        # Get the talent sheet
                        TalentSheet = apps.get_model("job_seekers", "TalentSheet")
                        talent_sheet = TalentSheet.objects.get(id=talent_sheet_id)

                        # Create or update the match
                        candidate_match, created = (
                            CandidateMatch.objects.update_or_create(
                                job_opening=job,
                                talent_sheet=talent_sheet,
                                match_type=match_type,
                                defaults={
                                    "holistic_score": holistic_score,
                                    "skills_score": skills_score,
                                    "experience_score": experience_score,
                                    "wildcard_score": wildcard_score,
                                    "qualifications_score": qualifications_score,
                                    "is_analyzed": False,  # Reset analysis flag on update
                                },
                            )
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

        # Gracefully handle missing talent sheets – they may have been deleted
        try:
            talent = TalentSheet.objects.get(id=talent_id)
        except TalentSheet.DoesNotExist:
            logger.warning(
                "Talent sheet %s not found, skipping matching to active jobs",
                talent_id,
            )
            return

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
                        "qualifications_matches": "qualifications",
                    }

                    # Store all matches for this talent by match type
                    talent_scores = {}

                    # First pass: collect all match scores for this talent
                    for result_key, match_type in match_type_mapping.items():
                        matches = match_results.get(result_key, [])

                        for match in matches:
                            # Skip if not matching our talent sheet
                            if str(match["metadata"]["talent_sheet_id"]) != str(
                                talent_id
                            ):
                                continue

                            # Store raw score (0-1 range) directly from Pinecone
                            score = match["score"]
                            talent_scores[match_type] = score

                    # Process each type of match
                    for result_key, match_type in match_type_mapping.items():
                        if not match_results.get(result_key):
                            continue

                        for match in match_results[result_key]:
                            # Skip if not matching our talent sheet
                            if str(match["metadata"]["talent_sheet_id"]) != str(
                                talent_id
                            ):
                                continue

                            # Use raw score (0-1 range) directly from Pinecone
                            score = match["score"]

                            # Skip if below minimum score (0.5)
                            if score < 0.5:
                                continue

                            # Get the scores for all match types, default to 0
                            holistic_score = talent_scores.get("holistic", 0)
                            skills_score = talent_scores.get("skills", 0)
                            experience_score = talent_scores.get("experience", 0)
                            wildcard_score = talent_scores.get("wildcard", 0)
                            qualifications_score = talent_scores.get(
                                "qualifications", 0
                            )

                            try:
                                # Create or update the match
                                candidate_match, created = (
                                    CandidateMatch.objects.update_or_create(
                                        job_opening=job,
                                        talent_sheet=talent,
                                        match_type=match_type,
                                        defaults={
                                            "holistic_score": holistic_score,
                                            "skills_score": skills_score,
                                            "experience_score": experience_score,
                                            "wildcard_score": wildcard_score,
                                            "qualifications_score": qualifications_score,
                                            "is_analyzed": False,  # Reset analysis flag on update
                                        },
                                    )
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
