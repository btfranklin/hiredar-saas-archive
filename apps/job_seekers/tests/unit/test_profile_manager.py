"""Unit tests for the ProfileManager service class."""

from django.test import TestCase

from apps.authentication.models import User
from apps.job_seekers.models import CandidatePool, JobSeekerProfile
from apps.job_seekers.services.profile_manager import ProfileManager


class ProfileManagerUtilityTests(TestCase):
    """Tests for helper utility functions (format/parse skills, completeness)."""

    def test_format_and_parse_skills_are_inverse_operations(self) -> None:
        """Ensure formatting then parsing returns the original skills list."""
        skills_input = ["Python", "  Django  ", "React"]

        formatted = ProfileManager.format_skills(skills_input)
        # Expected joined with newlines and trimmed values
        self.assertEqual(formatted, "Python\nDjango\nReact")

        parsed = ProfileManager.parse_skills(formatted)
        self.assertEqual(parsed, ["Python", "Django", "React"])

    def test_parse_skills_handles_empty_string(self) -> None:
        """Return an empty list when parse_skills receives a blank string."""
        self.assertEqual(ProfileManager.parse_skills(""), [])

    def test_format_skills_handles_empty_list(self) -> None:
        """Return an empty string when formatting an empty skill list."""
        self.assertEqual(ProfileManager.format_skills([]), "")

    def test_is_profile_complete(self) -> None:
        """Detect when a profile has all required fields populated."""
        # Create a dummy profile with no data
        profile = JobSeekerProfile()
        self.assertFalse(ProfileManager.is_profile_complete(profile))

        # Populate required fields
        for field in [
            "skills",
            "experience",
            "professional_summary",
            "desired_role",
            "years_of_experience",
        ]:
            setattr(profile, field, "dummy" if field != "years_of_experience" else 5)

        self.assertTrue(ProfileManager.is_profile_complete(profile))


class ProfileManagerDatabaseTests(TestCase):
    """Tests hitting the DB to ensure create_or_update_profile works."""

    def setUp(self) -> None:
        """Create a job seeker user used throughout database tests."""
        self.user = User.objects.create_user(  # type: ignore[attr-defined]
            email="pmgr@example.com",
            password="pw",
            user_type="job_seeker",
        )

    def test_create_profile_for_user(self) -> None:
        """Create a profile from scratch when one does not already exist."""
        # Delete the existing profile created by signal to test creation path
        JobSeekerProfile.objects.filter(user_owner=self.user).delete()

        data = {
            "skills": "Python",
            "experience": "Some experience",
        }

        profile = ProfileManager.create_or_update_profile(self.user, data)

        self.assertIsNotNone(profile.pk)
        self.assertEqual(profile.skills, "Python")
        self.assertEqual(profile.user_owner, self.user)

    def test_update_existing_profile(self) -> None:
        """Update an existing profile with new field values."""
        # Fetch the existing profile created by signal
        profile = ProfileManager.get_profile(self.user)
        self.assertIsNotNone(profile)

        new_data = {"professional_summary": "Updated summary"}
        updated = ProfileManager.create_or_update_profile(self.user, new_data)

        self.assertEqual(updated.professional_summary, "Updated summary")

    def test_create_profile_for_candidate_pool(self) -> None:
        """Create a profile anchored to a candidate pool instead of a user."""
        recruiter = User.objects.create_user(  # type: ignore[attr-defined]
            email="recruit@example.com",
            password="rpw",
            user_type="recruiter",
        )

        pool = CandidatePool.objects.create(recruiter=recruiter, name="May Uploads")

        data = {"skills": "C++, Embedded"}

        profile = ProfileManager.create_or_update_profile(pool, data)
        self.assertEqual(profile.candidate_pool, pool)
        self.assertEqual(profile.skills, "C++, Embedded")
