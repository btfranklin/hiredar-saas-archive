from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.job_seekers.models.profile import JobSeekerProfile

SAMPLE_MD = """# Professional Summary\nLorem ipsum\n# Skills\nPython, Django"""


@override_settings(JOBSEEKERS_WORKSHOP_DAILY_LIMIT=2)
class UpgradeResumeRateLimitTests(TestCase):
    """Verify rate-limiting for the résumé upgrade workshop tool."""

    def setUp(self) -> None:
        # Ensure module-level constant reflects test override
        from apps.job_seekers.views import workshop_views as wv

        wv.DAILY_LIMIT = 2
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
        self.url = reverse("job_seekers:workshop_upgrade_resume")

    def _post_upgrade(self):
        """Helper to hit the POST endpoint with necessary patches."""
        with (
            patch(
                "apps.job_seekers.views.workshop_views.upgrade_resume_content",
                return_value=SAMPLE_MD,
            ),
            patch(
                "apps.job_seekers.views.workshop_views.parse_resume_markdown",
                return_value=self.profile,
            ),
            patch(
                "apps.job_seekers.middleware.resume_upload_required.ResumeUploadRequiredMiddleware.process_request",
                return_value=None,
            ),
        ):
            return self.client.post(self.url, HTTP_HX_REQUEST="true")

    def test_limit_enforced_after_two_requests(self):
        resp1 = self._post_upgrade()
        self.assertEqual(resp1.status_code, 200)

        resp2 = self._post_upgrade()
        self.assertEqual(resp2.status_code, 200)

        resp3 = self._post_upgrade()
        self.assertEqual(resp3.status_code, 429)
        self.assertIn(b"daily limit", resp3.content.lower())

    def test_button_disabled_when_limit_reached(self):
        cache_key = f"resume_upgrade:{self.user.id}"
        cache.set(cache_key, 2, timeout=60 * 60)

        with patch(
            "apps.job_seekers.middleware.resume_upload_required.ResumeUploadRequiredMiddleware.process_request",
            return_value=None,
        ):
            resp = self.client.get(self.url)
        self.assertContains(resp, "Upgrade Resume (limit reached)")
        self.assertContains(resp, "btn-disabled")
