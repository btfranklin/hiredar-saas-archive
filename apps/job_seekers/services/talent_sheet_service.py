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

    @staticmethod
    @transaction.atomic
    def safe_update_publication_status(
        job_seeker_id: int,
        is_published: bool,
    ) -> TalentSheet | None:
        """
        Safely update the publication status of a talent sheet.

        Args:
            job_seeker_id: ID of the job seeker profile
            is_published: New publication status

        Returns:
            Updated TalentSheet instance, or None if not found

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
            talent_sheet = TalentSheet.objects.select_for_update().get(
                job_seeker=job_seeker
            )

            # Update publication status
            talent_sheet.is_published = is_published
            talent_sheet.save(update_fields=["is_published"])

            logger.debug(
                "Updated publication status for TalentSheet (job seeker %s) to %s",
                job_seeker_id,
                is_published,
            )
            return talent_sheet

        except TalentSheet.DoesNotExist:
            logger.warning(
                "TalentSheet not found for job seeker %s when updating publication status",
                job_seeker_id,
            )
            return None

    @staticmethod
    @transaction.atomic
    def safe_update_ideal_roles(
        job_seeker_id: int,
        ideal_roles: str,
    ) -> TalentSheet | None:
        """
        Safely update the ideal roles of a talent sheet.

        Args:
            job_seeker_id: ID of the job seeker profile
            ideal_roles: New ideal roles string

        Returns:
            Updated TalentSheet instance, or None if not found

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
            talent_sheet = TalentSheet.objects.select_for_update().get(
                job_seeker=job_seeker
            )

            # Update ideal roles
            talent_sheet.ideal_roles = ideal_roles
            talent_sheet.save(update_fields=["ideal_roles"])

            logger.debug(
                "Updated ideal roles for TalentSheet (job seeker %s)",
                job_seeker_id,
            )
            return talent_sheet

        except TalentSheet.DoesNotExist:
            logger.warning(
                "TalentSheet not found for job seeker %s when updating ideal roles",
                job_seeker_id,
            )
            return None
