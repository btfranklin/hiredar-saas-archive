"""Unit tests for models in the job_seekers app.

These tests focus on the light‑weight helper properties and __str__ methods so
they can run without any heavy external dependencies.
"""

from django.test import TestCase

from apps.authentication.models import User
from apps.candidates.models import CandidatePool
from apps.job_seekers.models import JobSeekerProfile, RoleRecommendation, TalentSheet


class JobSeekerProfileModelTests(TestCase):
    """Test helper properties on JobSeekerProfile."""

    def setUp(self):
        # Resume ingestion now owns candidate profiles via recruiter pools.
        self.recruiter = User.objects.create_user(  # type: ignore[attr-defined]
            email="recruiter@example.com",
            password="password123",
            name="Recruiter Owner",
            user_type="recruiter",
        )
        self.candidate_pool = CandidatePool.objects.create(
            recruiter=self.recruiter, name="Imported Résumés"
        )

        # Create a pool-owned profile with parsed resume details.
        self.profile = JobSeekerProfile.objects.create(
            candidate_pool=self.candidate_pool,
            candidate_name="John Smith",
            most_recent_title="Senior Platform Engineer",
            professional_summary="Seasoned engineer with focus on infrastructure.",
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

    def test_str_for_pool_owned_profile(self):
        """__str__ should reflect the owning candidate pool."""

        self.assertEqual(
            str(self.profile), f"Job Seeker (Pool: {self.candidate_pool.name})"
        )

    def test_display_name_and_initials_for_pool_owned_profile(self):
        """Pool-owned profiles should use candidate_name when present."""

        self.assertEqual(self.profile.display_name, "John Smith")
        self.assertEqual(self.profile.avatar_initials, "JS")

        # If candidate_name is missing we should fall back to title initials.
        self.profile.candidate_name = ""
        self.profile.save(update_fields=["candidate_name"])
        self.assertEqual(self.profile.display_name, "Senior Platform Engineer")
        self.assertEqual(self.profile.avatar_initials, "SE")


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
        """Pool-owned profiles should fall back to the profile identifier."""
        recruiter = User.objects.create_user(  # type: ignore[attr-defined]
            email="recs@example.com",
            password="pw",
            user_type="recruiter",
            name="Rec",
        )
        candidate_pool = CandidatePool.objects.create(
            recruiter=recruiter,
            name="Summer Uploads",
        )
        profile = JobSeekerProfile.objects.create(candidate_pool=candidate_pool)

        rec = RoleRecommendation.objects.create(
            job_seeker=profile,
            role_title="Data Analyst",
            description="Analyze stuff",
        )

        stringified = str(rec)
        self.assertIn("Data Analyst", stringified)
        self.assertIn(f"Profile {profile.pk}", stringified)


class TalentSheetModelTests(TestCase):
    """Tests for TalentSheet helper properties."""

    def setUp(self):
        recruiter = User.objects.create_user(  # type: ignore[attr-defined]
            email="talentrecruiter@example.com",
            password="pw",
            user_type="recruiter",
            name="Talent Recruiter",
        )

        self.candidate_pool = CandidatePool.objects.create(
            recruiter=recruiter,
            name="Talent Batch",
        )

        # Pool-owned profile used for talent sheet generation
        self.profile = JobSeekerProfile.objects.create(
            candidate_pool=self.candidate_pool,
            candidate_name="Tal En T",
        )

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

    def test_candidate_pool_property_for_pool_owned_sheet(self):
        """Pool-owned profiles should yield their candidate pool."""

        self.assertEqual(self.talent_sheet.candidate_pool, self.candidate_pool)
