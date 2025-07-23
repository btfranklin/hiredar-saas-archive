from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.job_seekers.models.profile import JobSeekerProfile

SAMPLE_MD = """# LinkedIn Headline\nSenior Python Developer\n# About\nPassionate software engineer..."""


@override_settings(JOBSEEKERS_WORKSHOP_LINKEDIN_DAILY_LIMIT=2)
class OptimizeLinkedInRateLimitTests(TestCase):
    """Verify daily usage limits for the LinkedIn optimization tool."""

    def setUp(self) -> None:
        from apps.job_seekers.views import workshop_views as wv

        wv.LINKEDIN_DAILY_LIMIT = 2
        cache.clear()
        User = get_user_model()
        self.user = User.objects.create_user(  # type: ignore[attr-defined]
            email="js@example.com", password="test123", user_type="job_seeker"
        )
        self.profile = JobSeekerProfile.objects.create(
            user_owner=self.user, resume_xml="<resume></resume>"
        )
        self.client = Client()
        self.client.force_login(self.user)
        self.url = reverse("job_seekers:workshop_optimize_linkedin")

    def _post_optimize(self):
        """Helper to hit the POST endpoint with required patches."""
        with (
            patch(
                "apps.job_seekers.views.workshop_views.optimize_linkedin_content",
                return_value=SAMPLE_MD,
            ),
            patch(
                "apps.job_seekers.views.workshop_views.parse_linkedin_markdown",
                return_value={"headline": "X", "about": "Y"},
            ),
            patch(
                "apps.job_seekers.middleware.resume_upload_required.ResumeUploadRequiredMiddleware.process_request",
                return_value=None,
            ),
        ):
            return self.client.post(self.url, HTTP_HX_REQUEST="true")

    def test_limit_enforced_after_two_requests(self):
        # First and second requests succeed
        resp1 = self._post_optimize()
        self.assertEqual(resp1.status_code, 200)

        resp2 = self._post_optimize()
        self.assertEqual(resp2.status_code, 200)

        # Third exceeds limit -> 429
        resp3 = self._post_optimize()
        self.assertEqual(resp3.status_code, 429)
        self.assertIn(b"daily limit", resp3.content.lower())

    def test_button_disabled_when_limit_reached(self):
        # Pre-fill cache to simulate exhausted quota
        cache_key = f"linkedin_optimize:{self.user.id}"
        cache.set(cache_key, 2, timeout=60 * 60)

        with patch(
            "apps.job_seekers.middleware.resume_upload_required.ResumeUploadRequiredMiddleware.process_request",
            return_value=None,
        ):
            resp = self.client.get(self.url)
        self.assertContains(resp, "Generate (limit reached)")
        self.assertContains(resp, "btn-disabled")
