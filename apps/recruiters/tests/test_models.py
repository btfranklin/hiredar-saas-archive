"""Tests for recruiter models."""

from django.test import TestCase

from apps.authentication.models import User
from apps.recruiters.models import RecruiterProfile


class RecruiterProfileModelTests(TestCase):
    """Test cases for the RecruiterProfile model."""

    def setUp(self) -> None:
        """Set up test data."""
        # Create a test user with recruiter type - profile will be created automatically by signal
        self.test_user = User.objects.create_user(  # type: ignore
            email="recruiter@example.com",
            password="password123",
            user_type="recruiter",
            name="Test Recruiter",
        )

        # Get the automatically created recruiter profile
        self.recruiter_profile = RecruiterProfile.objects.get(user=self.test_user)

    def test_recruiter_profile_creation(self) -> None:
        """Test that a recruiter profile is created correctly."""
        self.assertEqual(self.recruiter_profile.user, self.test_user)
        self.assertFalse(self.recruiter_profile.is_subscribed)
        self.assertEqual(self.recruiter_profile.subscription_tier, "basic")
