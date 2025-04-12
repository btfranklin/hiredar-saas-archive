"""
Service for managing job seeker profiles.
"""

from django.db import transaction

from apps.job_seekers.models import JobSeekerProfile


class ProfileManager:
    """Service for managing job seeker profiles."""

    @staticmethod
    def get_profile(user):
        """
        Get a job seeker profile for a user.

        Args:
            user: The user to get the profile for

        Returns:
            The job seeker profile, or None if it doesn't exist
        """
        try:
            return JobSeekerProfile.objects.get(user=user)
        except JobSeekerProfile.DoesNotExist:
            return None

    @staticmethod
    @transaction.atomic
    def create_or_update_profile(user, profile_data):
        """
        Create or update a job seeker profile.

        Args:
            user: The user to create/update the profile for
            profile_data: Dictionary of profile data

        Returns:
            The created or updated job seeker profile
        """
        profile, created = JobSeekerProfile.objects.get_or_create(user=user)

        # Update the profile with the provided data
        for field, value in profile_data.items():
            if hasattr(profile, field):
                setattr(profile, field, value)

        profile.save()
        return profile

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
