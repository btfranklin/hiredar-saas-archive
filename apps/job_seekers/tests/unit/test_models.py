"""Unit tests for models in the job_seekers app.

These tests focus on the light‑weight helper properties and __str__ methods so
they can run without any heavy external dependencies.
"""

from django.test import TestCase

from apps.authentication.models import User
from apps.job_seekers.models import (
    CandidatePool,
    JobSeekerProfile,
    RoleRecommendation,
    TalentSheet,
)


class JobSeekerProfileModelTests(TestCase):
    """Test helper properties on JobSeekerProfile."""

    def setUp(self):
        # Create a user who will own the profile
        self.user = User.objects.create_user(  # type: ignore[attr-defined]
            email="jsmith@example.com",
            password="password123",
            name="John Smith",
            user_type="job_seeker",
        )

        # Fetch the automatically created profile via user_owner foreign key
        self.profile: JobSeekerProfile = JobSeekerProfile.objects.get(
            user_owner=self.user
        )

        # Populate some skills so we can test skills_list
        self.profile.skills = (
            "Python\n  Django \nReact \n"  # note extra spaces & trailing newline
        )
        self.profile.save(update_fields=["skills"])

    def test_skills_list_property(self):
        """skills_list should return a clean list of skill names without blanks."""

        expected = ["Python", "Django", "React"]
        self.assertEqual(self.profile.skills_list, expected)

    def test_str_for_user_owned_profile(self):
        """__str__ should include user email when owned by a User instance."""

        self.assertIn(self.user.email, str(self.profile))

    def test_str_for_candidate_pool_owned_profile(self):
        """When the profile owner is a resume pool, __str__ should reflect that."""

        # Create a recruiter and a resume pool which will own a new profile.
        recruiter = User.objects.create_user(  # type: ignore[attr-defined]
            email="recruiter@example.com",
            password="recruiter_pw",
            name="Recruiter",
            user_type="recruiter",
        )

        candidate_pool = CandidatePool.objects.create(
            recruiter=recruiter,
            name="March Batch",
        )

        # Create a profile owned by the resume pool using candidate_pool field
        pool_profile = JobSeekerProfile.objects.create(candidate_pool=candidate_pool)

        self.assertIn("Candidate Pool: March Batch", str(candidate_pool))
        # The profile's __str__ should reference the pool label
        self.assertIn("March Batch", str(pool_profile))


class RoleRecommendationModelTests(TestCase):
    """Test helper methods on RoleRecommendation model."""

    def test_candidate_pool_property(self):
        """candidate_pool should bubble up from the related profile."""

        # Build minimal objects
        recruiter = User.objects.create_user(  # type: ignore[attr-defined]
            email="recruiter2@example.com",
            password="pw",
            user_type="recruiter",
            name="Rec",
        )
        candidate_pool = CandidatePool.objects.create(
            recruiter=recruiter,
            name="April Uploads",
        )

        # Create a profile owned by the resume pool
        profile = JobSeekerProfile.objects.create(candidate_pool=candidate_pool)

        rec = RoleRecommendation.objects.create(
            job_seeker=profile,
            role_title="Backend Engineer",
            description="Work on APIs",
        )

        # The property should return the candidate_pool instance
        self.assertEqual(rec.candidate_pool, candidate_pool)

    def test_str_contains_role_and_user(self):
        """__str__ should combine role title and job seeker identity."""

        user = User.objects.create_user(  # type: ignore[attr-defined]
            email="alice@example.com",
            password="pw",
            user_type="job_seeker",
            name="Alice Example",
        )

        # Fetch the profile created by signal via user_owner foreign key
        profile = JobSeekerProfile.objects.get(user_owner=user)

        rec = RoleRecommendation.objects.create(
            job_seeker=profile,
            role_title="Data Analyst",
            description="Analyse stuff",
        )

        stringified = str(rec)
        self.assertIn("Data Analyst", stringified)
        self.assertIn("Alice Example", stringified)


class TalentSheetModelTests(TestCase):
    """Tests for TalentSheet helper properties."""

    def setUp(self):
        # Create a job seeker
        self.user = User.objects.create_user(  # type: ignore[attr-defined]
            email="talent@example.com",
            password="pw",
            user_type="job_seeker",
            name="Tal En T",
        )

        # Fetch the profile created by signal
        self.profile = JobSeekerProfile.objects.get(user_owner=self.user)

        self.talent_sheet = TalentSheet.objects.create(
            job_seeker=self.profile,
            promotional_blurb="Great candidate",
            experience_overview="Chief Researcher (2015-2017): Led discovery of six biological compounds.",
            ideal_roles="Backend Dev, API Engineer",
            is_published=True,
        )

    def test_ideal_roles_list(self):
        """ideal_roles_list should split the CSV into trimmed values."""

        expected = ["Backend Dev", "API Engineer"]
        self.assertEqual(self.talent_sheet.ideal_roles_list, expected)

    def test_candidate_pool_none_for_user_owned(self):
        """User‑owned profiles should yield None for candidate_pool."""

        self.assertIsNone(self.talent_sheet.candidate_pool)
