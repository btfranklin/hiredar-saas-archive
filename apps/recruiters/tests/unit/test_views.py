"""Tests for recruiter-facing views."""

from allauth.account.models import EmailAddress
from django.test import Client, TestCase
from django.urls import reverse

from apps.authentication.models import User


class RecruiterSettingsViewTests(TestCase):
    """Test behaviour of the recruiter settings view."""

    def setUp(self) -> None:
        self.client = Client()
        user_manager = User.objects  # type: ignore[assignment]
        self.user = user_manager.create_user(
            email="verified@example.com",
            password="testpass123",
            name="Recruiter User",
            user_type="recruiter",
        )
        EmailAddress.objects.create(
            user=self.user,
            email="verified@example.com",
            verified=True,
            primary=True,
        )

    def test_settings_view_marks_email_verified(self) -> None:
        """Recruiter settings view surfaces the email verification state."""
        self.client.force_login(self.user)

        response = self.client.get(reverse("recruiters:settings"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("email_verified", response.context)
        self.assertTrue(response.context["email_verified"])
        self.assertNotContains(
            response,
            "Your email address has not been verified.",
        )
