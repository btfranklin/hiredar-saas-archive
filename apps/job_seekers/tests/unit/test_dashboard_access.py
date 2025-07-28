from __future__ import annotations

import pytest
from django.conf import settings
from django.test import Client
from django.urls import reverse

from apps.authentication.models import User
from apps.job_seekers.models import JobSeekerProfile


@pytest.mark.django_db
class TestDashboardAccess:
    """Verify the access-control logic provided by ``JobSeekerRequiredMixin``."""

    def _create_user(
        self, *, user_type: str = "job_seeker", with_profile: bool = True
    ) -> User:
        """Helper: create a user (and optionally remove the auto-created profile)."""

        user = User.objects.create_user(  # type: ignore[arg-type]
            email=f"{user_type}@example.com",
            password="password123",
            user_type=user_type,
            name="Test User",
        )

        # The post-save signal auto-creates a profile for job-seekers – remove it
        # when the caller requests *with_profile=False* so we can test that path.
        if user_type == "job_seeker" and not with_profile:
            JobSeekerProfile.objects.filter(user_owner=user).delete()

        return user

    # --------------------------------------------------------------
    # Test cases
    # --------------------------------------------------------------

    def test_unauthenticated_user_redirects_to_login(self):
        client = Client()
        url = reverse("job_seekers:dashboard")

        response = client.get(url)

        assert response.status_code == 302
        # Django prepends the original URL as "?next=…"; we only check prefix.
        assert response["Location"].startswith(settings.LOGIN_URL)

    def test_non_job_seeker_redirects_home(self):
        user = self._create_user(user_type="recruiter")
        client = Client()
        client.force_login(user)

        url = reverse("job_seekers:dashboard")
        response = client.get(url)

        assert response.status_code == 302
        assert response["Location"] == reverse("core:home")

    def test_job_seeker_without_profile_redirects_to_profile_create(self):
        user = self._create_user(user_type="job_seeker", with_profile=False)
        client = Client()
        client.force_login(user)

        url = reverse("job_seekers:dashboard")
        response = client.get(url)

        assert response.status_code == 302
        assert response["Location"] == reverse("job_seekers:profile_create")

    def test_job_seeker_with_profile_gets_dashboard(self):
        user = self._create_user(user_type="job_seeker", with_profile=True)

        # The resume-upload middleware requires a non-empty ``resume_xml`` field.
        profile = JobSeekerProfile.objects.get(user_owner=user)
        profile.resume_xml = "<resume />"
        profile.save(update_fields=["resume_xml"])

        client = Client()
        client.force_login(user)

        url = reverse("job_seekers:dashboard")
        response = client.get(url)

        assert response.status_code == 200
        # A very light sanity check that we rendered the dashboard template.
        assert b"dashboard" in response.content.lower()
