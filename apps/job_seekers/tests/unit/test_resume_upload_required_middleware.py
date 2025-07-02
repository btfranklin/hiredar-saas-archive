"""Tests for :pyclass:`ResumeUploadRequiredMiddleware`.

These tests assert that **job-seekers** cannot access normal application pages
until they have uploaded a resume, while exempt URLs remain accessible.
"""

from __future__ import annotations

import uuid

from django.test import Client, TestCase
from django.urls import reverse

from apps.authentication.models import User
from apps.job_seekers.models import JobSeekerProfile


class ResumeUploadRequiredMiddlewareTests(TestCase):
    """Verify the behaviour of the resume-upload enforcement middleware."""

    def setUp(self):
        super().setUp()
        self.client: Client = Client()

        # Create a *job-seeker* account (profile is created automatically by signal)
        self.seeker_password = "Testpass123!"
        # Using `create` instead of the helper avoids static-analysis false positives
        self.seeker: User = User.objects.create(
            email="seeker@example.com",
            user_type="job_seeker",
            name="Job Seeker",
        )
        self.seeker.set_password(self.seeker_password)
        self.seeker.save(update_fields=["password"])

        # Convenience URLs
        self.dashboard_url = reverse("job_seekers:dashboard")
        self.profile_create_url = reverse("job_seekers:profile_create")
        self.resume_upload_url = reverse("job_seekers:resume_upload")
        self.task_status_url = reverse(
            "job_seekers:task_status", kwargs={"task_id": str(uuid.uuid4())}
        )

    # ------------------------------------------------------------------
    # Helper utilities
    # ------------------------------------------------------------------

    def _login_seeker(self) -> None:
        """Authenticate the *job-seeker* test client."""

        logged_in = self.client.login(
            email=self.seeker.email, password=self.seeker_password
        )
        assert logged_in, "Failed to log in test user"

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_redirects_when_resume_missing(self):
        """Job-seekers without a resume should be redirected to the upload page."""

        self._login_seeker()

        response = self.client.get(self.dashboard_url)

        # Expect a redirect to the profile-creation / resume-upload page
        self.assertRedirects(
            response,
            self.profile_create_url,
            fetch_redirect_response=False,
        )

    def test_access_allowed_for_exempt_paths(self):
        """The upload flow remains accessible even without a resume."""

        self._login_seeker()

        # 1. The profile-creation page
        response_create = self.client.get(self.profile_create_url)
        self.assertEqual(response_create.status_code, 200)

        # 2. The POST endpoint for uploading resumes
        response_upload = self.client.options(
            self.resume_upload_url
        )  # pre-flight verb to avoid file upload complexity
        # OPTIONS should not be redirected either
        self.assertNotEqual(response_upload.status_code, 302)

        # 3. The task-status polling URL (dynamic segment)
        response_status = self.client.get(self.task_status_url)
        # Could be 404 (no such task) but **must not** be a redirect to upload page
        self.assertNotEqual(response_status.status_code, 302)

    def test_access_allowed_once_resume_present(self):
        """After a resume is attached, the middleware should allow access."""

        # Attach dummy resume XML to profile
        profile: JobSeekerProfile = JobSeekerProfile.objects.get(user_owner=self.seeker)
        profile.resume_xml = "<resume />"
        profile.save(update_fields=["resume_xml"])

        self._login_seeker()

        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
