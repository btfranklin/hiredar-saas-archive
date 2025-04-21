"""
Service for managing talent pool operations.
"""

import logging

from django.db import transaction
from django.shortcuts import get_object_or_404
# Use centralised helper to decouple from task queue implementation
from apps.core.tasks import safe_async_task

from apps.job_seekers.models import RoleRecommendation, TalentSheet
from apps.job_seekers.services.profile_manager import ProfileManager

# Set up logging
logger = logging.getLogger(__name__)


class TalentPoolManager:
    """Service for managing talent pool operations."""

    @staticmethod
    def get_talent_pool_status(user):
        """
        Get the talent pool status for a user.

        Args:
            user: The user to check

        Returns:
            Dictionary with talent pool status information
        """
        try:
            profile = ProfileManager.get_profile(user)
            if not profile:
                return {
                    "in_talent_pool": False,
                    "has_talent_sheet": False,
                    "is_published": False,
                }

            in_talent_pool = profile.in_talent_pool

            # Get talent sheet if it exists
            talent_sheet = None
            try:
                talent_sheet = TalentSheet.objects.get(job_seeker=profile)
            except TalentSheet.DoesNotExist:
                pass

            return {
                "in_talent_pool": in_talent_pool,
                "has_talent_sheet": talent_sheet is not None,
                "is_published": talent_sheet.is_published if talent_sheet else False,
            }
        except Exception as e:
            logger.error(
                "Error getting talent pool status for user %s: %s", user.id, str(e)
            )
            return {
                "in_talent_pool": False,
                "has_talent_sheet": False,
                "is_published": False,
            }

    @staticmethod
    @transaction.atomic
    def toggle_talent_pool(user, join=True):
        """
        Toggle a user's participation in the talent pool.

        Args:
            user: The user to toggle
            join: True to join the talent pool, False to leave

        Returns:
            Dictionary with updated talent pool status
        """
        try:
            profile = ProfileManager.get_profile(user)
            if not profile:
                return {
                    "in_talent_pool": False,
                    "has_talent_sheet": False,
                    "is_published": False,
                    "error": "Profile not found",
                }

            profile_id = getattr(profile, "id", None)

            if profile_id is None:
                return {
                    "in_talent_pool": False,
                    "has_talent_sheet": False,
                    "is_published": False,
                    "error": "Profile ID not found",
                }

            # Handle talent pool status change
            if join:
                # The job seeker is joining the talent pool
                # Schedule the talent sheet generation task
                try:
                    # Use a string reference to the task to avoid circular imports
                    task_id = safe_async_task(
                        "apps.job_seekers.tasks.talent_sheet_tasks.generate_talent_sheet_task",
                        profile_id,
                        task_name=f"generate_talent_sheet_{profile_id}",
                    )
                    logger.info("Scheduled talent sheet generation task: %s", task_id)
                except Exception as e:
                    logger.error(
                        "Failed to schedule talent sheet generation task for profile %s: %s",
                        profile_id,
                        str(e),
                    )

                # Check if a talent sheet already exists (e.g., from a previous pool participation)
                has_talent_sheet = False
                is_published = False
                try:
                    talent_sheet = TalentSheet.objects.get(job_seeker=profile)
                    has_talent_sheet = True

                    # If leaving and rejoining, we might need to unpublish an existing sheet
                    # until the new LLM-generated content is ready
                    if not talent_sheet.is_published:
                        # Don't change it if already unpublished
                        pass
                    elif (
                        not talent_sheet.promotional_blurb
                        or talent_sheet.promotional_blurb.startswith(
                            "Your talent profile is being generated"
                        )
                    ):
                        # If it's just a placeholder, keep it unpublished until real content is ready
                        talent_sheet.is_published = False
                        talent_sheet.save(update_fields=["is_published"])
                except TalentSheet.DoesNotExist:
                    # That's expected - the task will create one
                    pass
            else:
                # The job seeker is leaving the talent pool
                # If a talent sheet exists, unpublish it
                has_talent_sheet = False
                try:
                    talent_sheet = TalentSheet.objects.get(job_seeker=profile)
                    has_talent_sheet = True
                    talent_sheet.is_published = False
                    talent_sheet.save(update_fields=["is_published"])
                except TalentSheet.DoesNotExist:
                    # No talent sheet to unpublish
                    pass

            return {
                "in_talent_pool": join,
                "has_talent_sheet": has_talent_sheet,
                "is_published": (
                    join and has_talent_sheet and talent_sheet.is_published
                    if "talent_sheet" in locals()
                    else False
                ),
            }
        except Exception as e:
            logger.error("Error toggling talent pool for user %s: %s", user.id, str(e))
            return {
                "in_talent_pool": False,
                "has_talent_sheet": False,
                "is_published": False,
                "error": "An error occurred",
            }

    @staticmethod
    def get_role_recommendations(profile):
        """
        Get role recommendations for a job seeker.

        Args:
            profile: The job seeker profile

        Returns:
            QuerySet of role recommendations
        """
        return RoleRecommendation.objects.filter(job_seeker=profile)

    @staticmethod
    @transaction.atomic
    def toggle_role_interest(role_id, interested=True, profile=None):
        """
        Toggle a job seeker's interest in a recommended role.

        Args:
            role_id: ID of the role recommendation
            interested: True if interested, False if not
            profile: Optional profile to check authorization

        Returns:
            The updated role recommendation, or None if not found or unauthorized
        """
        # Get the role recommendation
        role = get_object_or_404(RoleRecommendation, id=role_id)

        # If profile was provided, check if the role belongs to this profile
        if profile is not None and role.job_seeker != profile:
            return None

        # Toggle the interest flag
        role.is_candidate_interested = interested
        role.save(update_fields=["is_candidate_interested"])

        # If showing interest, update the ideal roles on the talent sheet
        if interested:
            profile = role.job_seeker
            try:
                talent_sheet = TalentSheet.objects.get(job_seeker=profile)

                # Get all roles the candidate is interested in
                interested_roles = RoleRecommendation.objects.filter(
                    job_seeker=profile, is_candidate_interested=True
                ).values_list("role_title", flat=True)

                # Update talent sheet ideal roles
                talent_sheet.ideal_roles = ", ".join(interested_roles)
                talent_sheet.save(update_fields=["ideal_roles"])
            except TalentSheet.DoesNotExist:
                pass

        return role

    @staticmethod
    @transaction.atomic
    def create_or_update_talent_sheet(profile, talent_sheet_data):
        """
        Create or update a talent sheet for a job seeker profile.

        Args:
            profile: JobSeekerProfile to create/update talent sheet for
            talent_sheet_data: Dictionary of data for the talent sheet.
                               Should not include salary_min as this is only set manually by users.

        Returns:
            The created or updated TalentSheet
        """
        talent_sheet, created = TalentSheet.objects.update_or_create(
            job_seeker=profile, defaults=talent_sheet_data
        )

        return talent_sheet
