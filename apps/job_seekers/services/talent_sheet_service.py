"""
Service for safely managing talent sheets with proper locking.
"""

import logging
from typing import Any

from django.db import IntegrityError, transaction

from apps.job_seekers.models import JobSeekerProfile, TalentSheet

logger = logging.getLogger(__name__)


class TalentSheetService:
    """Service for safely creating and updating talent sheets."""

    @staticmethod
    @transaction.atomic
    def safe_upsert_talent_sheet(
        job_seeker_id: int,
        talent_sheet_data: dict[str, Any],
    ) -> tuple[TalentSheet, bool]:
        """
        Safely create or update a TalentSheet with proper locking.

        Args:
            job_seeker_id: ID of the job seeker profile
            talent_sheet_data: Dictionary of talent sheet data

        Returns:
            Tuple of (TalentSheet instance, created_flag)

        Raises:
            ValueError: If JobSeekerProfile doesn't exist
        """
        try:
            # Lock the job seeker profile
            job_seeker = JobSeekerProfile.objects.select_for_update().get(
                id=job_seeker_id
            )
        except JobSeekerProfile.DoesNotExist:
            raise ValueError(f"JobSeekerProfile {job_seeker_id} not found")

        try:
            # Try to get and lock existing talent sheet
            existing_sheet = TalentSheet.objects.select_for_update().get(
                job_seeker=job_seeker
            )

            # Update the existing sheet
            for field, value in talent_sheet_data.items():
                if hasattr(existing_sheet, field):
                    setattr(existing_sheet, field, value)
            existing_sheet.save(update_fields=list(talent_sheet_data.keys()))

            logger.debug(
                "Updated existing TalentSheet for job seeker %s",
                job_seeker_id,
            )
            return existing_sheet, False

        except TalentSheet.DoesNotExist:
            # No existing sheet, create new one
            try:
                new_sheet = TalentSheet.objects.create(
                    job_seeker=job_seeker,
                    **talent_sheet_data,
                )
                logger.debug(
                    "Created new TalentSheet for job seeker %s",
                    job_seeker_id,
                )
                return new_sheet, True

            except IntegrityError:
                # Race condition: another process created the sheet
                logger.warning(
                    "IntegrityError during TalentSheet creation, retrying get for job seeker %s",
                    job_seeker_id,
                )
                existing_sheet = TalentSheet.objects.select_for_update().get(
                    job_seeker=job_seeker
                )

                # Update with our values
                for field, value in talent_sheet_data.items():
                    if hasattr(existing_sheet, field):
                        setattr(existing_sheet, field, value)
                existing_sheet.save(update_fields=list(talent_sheet_data.keys()))

                return existing_sheet, False
