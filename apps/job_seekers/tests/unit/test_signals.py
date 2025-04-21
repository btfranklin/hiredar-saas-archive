"""Signal tests for job_seekers app."""

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from apps.authentication.models import User
from apps.job_seekers.models import JobSeekerProfile


class JobSeekerProfileSignalTests(TestCase):
    """Ensure a profile is automatically created for job seeker users."""

    def test_profile_created_on_user_creation(self):
        user = User.objects.create_user(
            email="signal@example.com",
            password="pw",
            user_type="job_seeker",
        )

        user_ct = ContentType.objects.get_for_model(User)

        self.assertTrue(
            JobSeekerProfile.objects.filter(
                owner_content_type=user_ct, owner_object_id=user.id
            ).exists()
        )
