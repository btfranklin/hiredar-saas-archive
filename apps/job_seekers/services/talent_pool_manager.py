"""
Service for managing talent pool operations.
"""

from django.db import transaction
from django.shortcuts import get_object_or_404
from django_q.tasks import async_task

from apps.job_seekers.models import JobSeekerProfile, RoleRecommendation, TalentSheet
from apps.job_seekers.tasks.talent_sheet_tasks import generate_talent_sheet_task


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
            profile = JobSeekerProfile.objects.get(user=user)
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
        except JobSeekerProfile.DoesNotExist:
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
            profile = JobSeekerProfile.objects.get(user=user)
            profile_id = getattr(profile, "id", None)

            if profile_id is None:
                return {
                    "in_talent_pool": False,
                    "has_talent_sheet": False,
                    "is_published": False,
                    "error": "Profile ID not found",
                }

            # If the job seeker is entering the talent pool, schedule a task to generate their talent sheet
            if join:
                try:
                    # Schedule the talent sheet generation task
                    task_id = async_task(
                        generate_talent_sheet_task,
                        profile_id,
                        hook=None,  # No callback needed
                        task_name=f"generate_talent_sheet_{profile_id}",
                    )
                except Exception as e:
                    # Log the error but don't fail the request
                    pass  # In the original code, it logged but continued

            # Get or create talent sheet
            talent_sheet, created = TalentSheet.objects.get_or_create(
                job_seeker=profile,
                defaults={
                    "promotional_blurb": "",
                    "skill_overview": "",
                    "is_published": join,
                },
            )

            # If the job seeker is leaving the talent pool, unpublish their talent sheet
            if not join:
                talent_sheet.is_published = False
                talent_sheet.save(update_fields=["is_published"])
            else:
                talent_sheet.is_published = True
                talent_sheet.save(update_fields=["is_published"])

            return {
                "in_talent_pool": join,
                "has_talent_sheet": True,
                "is_published": join,
            }
        except JobSeekerProfile.DoesNotExist:
            return {
                "in_talent_pool": False,
                "has_talent_sheet": False,
                "is_published": False,
                "error": "Profile not found",
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
            talent_sheet_data: Dictionary of data for the talent sheet

        Returns:
            The created or updated TalentSheet
        """
        talent_sheet, created = TalentSheet.objects.update_or_create(
            job_seeker=profile, defaults=talent_sheet_data
        )

        return talent_sheet
