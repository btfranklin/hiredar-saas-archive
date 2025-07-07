"""
Service for safely managing candidate matches with proper locking.
"""

import logging
from decimal import Decimal
from typing import Any

from django.apps import apps
from django.db import IntegrityError, transaction

logger = logging.getLogger(__name__)


class CandidateMatchService:
    """Service for safely creating and updating candidate matches."""

    @staticmethod
    @transaction.atomic
    def safe_upsert_candidate_match(
        job_opening_id: int,
        talent_sheet_id: int,
        score_updates: dict[str, float],
        **additional_defaults: Any,
    ) -> tuple[Any, bool]:
        """
        Safely create or update a CandidateMatch with proper locking.

        This method prevents race conditions by using select_for_update()
        to lock the related records before performing the upsert.

        Args:
            job_opening_id: ID of the job opening
            talent_sheet_id: ID of the talent sheet
            score_updates: Dictionary of score field names to values
            **additional_defaults: Additional fields to update

        Returns:
            Tuple of (CandidateMatch instance, created_flag)

        Raises:
            ValueError: If required models don't exist
        """
        CandidateMatch = apps.get_model("matching", "CandidateMatch")
        JobOpening = apps.get_model("recruiters", "JobOpening")
        TalentSheet = apps.get_model("job_seekers", "TalentSheet")

        try:
            # Lock the related objects to prevent concurrent modifications
            job_opening = JobOpening.objects.select_for_update().get(id=job_opening_id)
            talent_sheet = TalentSheet.objects.select_for_update().get(
                id=talent_sheet_id
            )
        except (JobOpening.DoesNotExist, TalentSheet.DoesNotExist) as e:
            raise ValueError(f"Required model not found: {e}")

        # Prepare the defaults dictionary
        defaults = {
            "holistic_score": Decimal(str(score_updates.get("holistic", 0))),
            "skills_score": Decimal(str(score_updates.get("skills", 0))),
            "experience_score": Decimal(str(score_updates.get("experience", 0))),
            "wildcard_score": Decimal(str(score_updates.get("wildcard", 0))),
            "qualifications_score": Decimal(
                str(score_updates.get("qualifications", 0))
            ),
            **additional_defaults,
        }

        # Try to get existing match with lock, or create new one
        try:
            # First, try to get and lock existing match
            existing_match = CandidateMatch.objects.select_for_update().get(
                job_opening=job_opening, talent_sheet=talent_sheet
            )

            # ---------------------------------------------------------------------
            # Preserve analysis status if it has already been generated
            # ---------------------------------------------------------------------
            # When upstream matching tasks refresh scores they often pass
            # ``is_analyzed=False`` by default.  If the match has already been
            # analyzed we **do not** want to overwrite the existing
            # ``is_analyzed=True`` flag – doing so would trigger repeated calls
            # to the expensive LLM when the recruiter views the match detail
            # page.  Only allow the flag to change if the caller explicitly
            # sets it to ``True`` or if the match has never been analyzed.

            if (
                "is_analyzed" in defaults
                and defaults["is_analyzed"] is False
                and existing_match.is_analyzed
            ):
                # Remove the attempted reset so we preserve the current value
                defaults.pop("is_analyzed")

            # Update the existing match
            for field, value in defaults.items():
                setattr(existing_match, field, value)
            existing_match.save(update_fields=list(defaults.keys()))

            logger.debug(
                "Updated existing CandidateMatch for job %s, talent %s",
                job_opening_id,
                talent_sheet_id,
            )
            return existing_match, False

        except CandidateMatch.DoesNotExist:
            # No existing match, create new one
            try:
                new_match = CandidateMatch.objects.create(
                    job_opening=job_opening,
                    talent_sheet=talent_sheet,
                    **defaults,
                )
                logger.debug(
                    "Created new CandidateMatch for job %s, talent %s",
                    job_opening_id,
                    talent_sheet_id,
                )
                return new_match, True

            except IntegrityError:
                # Race condition: another process created the match
                # between our check and create. Try to get it again.
                logger.warning(
                    "IntegrityError during CandidateMatch creation, retrying get for job %s, talent %s",
                    job_opening_id,
                    talent_sheet_id,
                )
                existing_match = CandidateMatch.objects.select_for_update().get(
                    job_opening=job_opening, talent_sheet=talent_sheet
                )

                # Update with our values
                for field, value in defaults.items():
                    setattr(existing_match, field, value)
                existing_match.save(update_fields=list(defaults.keys()))

                return existing_match, False

    @staticmethod
    @transaction.atomic
    def safe_update_analysis(
        candidate_match_id: int,
        match_summary: str,
        match_analysis: str,
        is_analyzed: bool = True,
    ) -> Any | None:
        """
        Safely update the analysis fields of a candidate match.

        Args:
            candidate_match_id: ID of the candidate match
            match_summary: Summary of the match analysis
            match_analysis: Detailed analysis of the match
            is_analyzed: Whether the match has been analyzed

        Returns:
            Updated CandidateMatch instance, or None if not found
        """
        CandidateMatch = apps.get_model("matching", "CandidateMatch")

        try:
            # Get and lock the candidate match
            candidate_match = CandidateMatch.objects.select_for_update().get(
                id=candidate_match_id
            )

            # Update analysis fields
            candidate_match.match_summary = match_summary
            candidate_match.match_analysis = match_analysis
            candidate_match.is_analyzed = is_analyzed
            candidate_match.save(
                update_fields=["match_summary", "match_analysis", "is_analyzed"]
            )

            logger.debug(
                "Updated analysis for CandidateMatch %s",
                candidate_match_id,
            )
            return candidate_match

        except CandidateMatch.DoesNotExist:
            logger.warning(
                "CandidateMatch %s not found when updating analysis",
                candidate_match_id,
            )
            return None
