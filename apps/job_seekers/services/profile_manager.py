"""
Service for managing job seeker profiles.
"""

from django.db import transaction

from apps.authentication.models import User
from apps.candidates.models import CandidatePool
from apps.job_seekers.models import JobSeekerProfile


class ProfileManager:
    """Service for managing job seeker profiles."""

    @staticmethod
    def get_profile(owner):
        """Get a job seeker profile for an owner (User or CandidatePool)."""
        if isinstance(owner, User):
            return JobSeekerProfile.objects.filter(user_owner=owner).first()
        if isinstance(owner, CandidatePool):
            return JobSeekerProfile.objects.filter(candidate_pool=owner).first()
        return None

    @staticmethod
    @transaction.atomic
    def create_or_update_profile(owner, profile_data):
        """
        Create or update a job seeker profile.

        Args:
            owner: The owner (User or CandidatePool) to create/update the profile for
            profile_data: Dictionary of profile data

        Returns:
            The created or updated job seeker profile
        """
        profile = ProfileManager.get_profile(owner)
        if not profile:
            # Create new profile with correct foreign key
            if isinstance(owner, User):
                profile = JobSeekerProfile(user_owner=owner)
            elif isinstance(owner, CandidatePool):
                profile = JobSeekerProfile(candidate_pool=owner)
            else:
                raise ValueError(f"Unsupported owner type: {type(owner)}")

        # Update the profile with the provided data
        for field, value in profile_data.items():
            # Only update fields that exist on the model
            if hasattr(profile, field):
                setattr(profile, field, value)
            # Handle candidate_name specifically for pool-owned profiles
            elif field == "candidate_name" and isinstance(owner, CandidatePool):
                setattr(profile, "candidate_name", value)

        profile.save()
        return profile

    @staticmethod
    def create_or_update_profile_for_candidate_pool(candidate_pool, profile_data):
        """
        Create or update a job seeker profile for a candidate pool.

        Args:
            candidate_pool: CandidatePool instance
            profile_data: Dictionary of profile data

        Returns:
            The created or updated job seeker profile
        """
        return ProfileManager.create_or_update_profile(candidate_pool, profile_data)

    @staticmethod
    def format_skills(skills_list):
        """
        Format a list of skills for storage in the database.

        Args:
            skills_list: List of skill names

        Returns:
            Line-separated string of skills
        """
        if not skills_list:
            return ""
        return "\n".join(skill.strip() for skill in skills_list if skill.strip())

    @staticmethod
    def parse_skills(skills_string):
        """
        Parse a line-separated string of skills into a list.

        Args:
            skills_string: Line-separated string of skills

        Returns:
            List of skill names
        """
        if not skills_string:
            return []
        return [skill.strip() for skill in skills_string.splitlines() if skill.strip()]

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

    @staticmethod
    def get_profile_by_user_id(user_id):
        """
        Get a job seeker profile for a user by user ID.

        This is a convenience method for views that have the user ID.

        Args:
            user_id: The ID of the user to get the profile for

        Returns:
            The job seeker profile, or None if it doesn't exist
        """
        # Look up the profile by the user_owner foreign key
        return JobSeekerProfile.objects.get(user_owner__id=user_id)

    @staticmethod
    def get_profile_for_user(user):
        """
        Get a job seeker profile for a user object.

        This is a convenience method for views that already have the user object.

        Args:
            user: The user object to get the profile for

        Returns:
            The job seeker profile, or None if it doesn't exist
        """
        return ProfileManager.get_profile(user)
