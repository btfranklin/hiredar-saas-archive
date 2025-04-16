"""
Service for managing job seeker profiles.
"""

from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from apps.job_seekers.models import JobSeekerProfile


class ProfileManager:
    """Service for managing job seeker profiles."""

    @staticmethod
    def get_profile(owner):
        """
        Get a job seeker profile for an owner (User or UploadedResumePool).

        Args:
            owner: The owner (User or UploadedResumePool) to get the profile for

        Returns:
            The job seeker profile, or None if it doesn't exist
        """
        try:
            # Get the content type for the owner class
            owner_content_type = ContentType.objects.get_for_model(owner.__class__)
            # Look up the profile by owner content type and ID
            return JobSeekerProfile.objects.get(
                owner_content_type=owner_content_type, owner_object_id=owner.pk
            )
        except JobSeekerProfile.DoesNotExist:
            return None

    @staticmethod
    @transaction.atomic
    def create_or_update_profile(owner, profile_data):
        """
        Create or update a job seeker profile.

        Args:
            owner: The owner (User or UploadedResumePool) to create/update the profile for
            profile_data: Dictionary of profile data

        Returns:
            The created or updated job seeker profile
        """
        # Check if profile exists
        profile = ProfileManager.get_profile(owner)

        if not profile:
            # Create new profile with polymorphic owner
            owner_content_type = ContentType.objects.get_for_model(owner.__class__)
            profile = JobSeekerProfile(
                owner_content_type=owner_content_type, owner_object_id=owner.pk
            )

        # Update the profile with the provided data
        for field, value in profile_data.items():
            if hasattr(profile, field):
                setattr(profile, field, value)

        profile.save()
        return profile

    @staticmethod
    def create_or_update_profile_for_resume_pool(resume_pool, profile_data):
        """
        Create or update a job seeker profile for a resume pool.

        Args:
            resume_pool: UploadedResumePool instance
            profile_data: Dictionary of profile data

        Returns:
            The created or updated job seeker profile
        """
        return ProfileManager.create_or_update_profile(resume_pool, profile_data)

    @staticmethod
    def format_skills(skills_list):
        """
        Format a list of skills for storage in the database.

        Args:
            skills_list: List of skill names

        Returns:
            Pipe-separated string of skills
        """
        if not skills_list:
            return ""
        return " | ".join(skill.strip() for skill in skills_list if skill.strip())

    @staticmethod
    def parse_skills(skills_string):
        """
        Parse a pipe-separated string of skills into a list.

        Args:
            skills_string: Pipe-separated string of skills

        Returns:
            List of skill names
        """
        if not skills_string:
            return []
        return [skill.strip() for skill in skills_string.split(" | ") if skill.strip()]

    @staticmethod
    def is_profile_complete(profile):
        """
        Check if a job seeker profile is complete.

        A profile is considered complete if it has the minimal required fields
        populated.

        Args:
            profile: The profile to check

        Returns:
            True if the profile is complete, False otherwise
        """
        # Define the minimum required fields for a complete profile
        required_fields = [
            "skills",
            "experience",
            "professional_summary",
            "desired_role",
            "years_of_experience",
        ]

        # Check if all required fields have a value
        for field in required_fields:
            value = getattr(profile, field, None)
            if not value:
                return False

        return True
