"""Tests for TalentPoolManager business logic."""

from unittest.mock import patch

from django.test import TestCase

from apps.authentication.models import User
from apps.job_seekers.models import JobSeekerProfile, RoleRecommendation, TalentSheet
from apps.job_seekers.services.talent_pool_manager import TalentPoolManager


class TalentPoolToggleTests(TestCase):
    """Verify join/leave behaviour without executing background jobs."""

    def setUp(self):
        self.user = User.objects.create_user(  # type: ignore[attr-defined]
            email="toggle@example.com",
            password="pw",
            user_type="job_seeker",
            name="Toggle Tester",
        )

        # Fetch profile created by signal via user_owner foreign key
        self.profile: JobSeekerProfile = JobSeekerProfile.objects.get(
            user_owner=self.user
        )

    @patch("apps.job_seekers.services.talent_pool_manager.async_task")
    def test_join_talent_pool_creates_placeholder_sheet_and_schedules_task(
        self, mock_async_task
    ):
        status = TalentPoolManager.toggle_talent_pool(self.user, join=True)

        self.assertTrue(status["in_talent_pool"])
        # No sheet exists yet – task will create it
        self.assertFalse(status["has_talent_sheet"])

        mock_async_task.assert_called()  # Make sure scheduling attempted

    @patch("apps.job_seekers.services.talent_pool_manager.async_task")
    def test_leave_talent_pool_unpublishes_sheet(self, mock_async_task):
        # First, create a published sheet manually
        TalentSheet.objects.create(
            job_seeker=self.profile,
            promotional_blurb="Some blurb",
            experience_overview="Chief Researcher (2015-2017): Managed research team.",
            is_published=True,
        )

        # Leave the talent pool
        status = TalentPoolManager.toggle_talent_pool(self.user, join=False)
        self.assertFalse(status["in_talent_pool"])
        self.assertTrue(status["has_talent_sheet"])

        # The sheet should now be unpublished
        self.profile.refresh_from_db()
        sheet = self.profile.talent_sheet  # type: ignore[attr-defined]
        self.assertFalse(sheet.is_published)

        # Leaving the pool should not enqueue any tasks
        mock_async_task.assert_not_called()


class RoleInterestToggleTests(TestCase):
    """Test TalentPoolManager.toggle_role_interest convenience function."""

    def setUp(self):
        self.user = User.objects.create_user(  # type: ignore[attr-defined]
            email="role@example.com",
            password="pw",
            user_type="job_seeker",
            name="Role Interest",
        )

        # Fetch profile created by signal via user_owner foreign key
        self.profile = JobSeekerProfile.objects.get(user_owner=self.user)

        # Create two recommendations so we can check list update
        self.rec1 = RoleRecommendation.objects.create(
            job_seeker=self.profile,
            role_title="Backend Dev",
            description="Desc",
        )
        self.rec2 = RoleRecommendation.objects.create(
            job_seeker=self.profile,
            role_title="Data Engineer",
            description="Desc",
        )

        # Create a talent sheet (unpublished)
        self.sheet = TalentSheet.objects.create(
            job_seeker=self.profile,
            promotional_blurb="Blurb",
            experience_overview="Chief Researcher (2015-2017): Managed research team.",
            is_published=True,
        )

    def test_toggle_interest_updates_flags_and_sheet(self):
        # Initially not interested
        self.assertFalse(self.rec1.is_candidate_interested)
        self.assertFalse(self.rec2.is_candidate_interested)

        # Express interest in the first role
        TalentPoolManager.toggle_role_interest(self.rec1.id, interested=True)  # type: ignore[attr-defined]

        # Reload from DB
        self.rec1.refresh_from_db()
        self.sheet.refresh_from_db()

        self.assertTrue(self.rec1.is_candidate_interested)
        self.assertIn("Backend Dev", self.sheet.ideal_roles)

        # Express interest in second role as well – ideal_roles should contain both
        TalentPoolManager.toggle_role_interest(self.rec2.id, interested=True)  # type: ignore[attr-defined]
        self.sheet.refresh_from_db()

        self.assertIn("Backend Dev", self.sheet.ideal_roles)
        self.assertIn("Data Engineer", self.sheet.ideal_roles)

        # Unauthorized profile returns None when mismatched
        other_user = User.objects.create_user(  # type: ignore[attr-defined]
            email="other@example.com",
            password="pw",
            user_type="job_seeker",
        )

        other_profile = JobSeekerProfile.objects.get(user_owner=other_user)

        result = TalentPoolManager.toggle_role_interest(
            self.rec1.id, interested=True, profile=other_profile  # type: ignore[attr-defined]
        )

        self.assertIsNone(result)
