"""Signal tests for job_seekers app."""

from django.test import TestCase

from apps.authentication.models import User
from apps.job_seekers.models import JobSeekerProfile


class JobSeekerProfileSignalTests(TestCase):
    """Ensure a profile is automatically created for job seeker users."""

    def test_profile_created_on_user_creation(self):
        user = User.objects.create_user(  # type: ignore[attr-defined]
            email="signal@example.com",
            password="pw",
            user_type="job_seeker",
        )

        # Verify profile created via user_owner foreign key
        self.assertTrue(JobSeekerProfile.objects.filter(user_owner=user).exists())
