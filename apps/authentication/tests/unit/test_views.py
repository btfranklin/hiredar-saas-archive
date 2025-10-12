"""Tests for the authentication app views."""

from typing import cast

from allauth.account.models import EmailAddress
from django.test import Client, TestCase
from django.urls import reverse

from apps.authentication.models import User, UserManager


class AuthenticationViewTests(TestCase):
    """Test cases for authentication views."""

    def setUp(self) -> None:
        """Set up test data."""
        self.client = Client()
        self.recruiter_data = {
            "email": "recruiter@example.com",
            "password1": "testpass123",
            "password2": "testpass123",
            "name": "Recruiter User",
            "user_type": "recruiter",
            "company_name": "Test Company",
            "us_only_certification": True,
        }

    def test_recruiter_signup(self) -> None:
        """Test recruiter signup process."""
        response = self.client.post(
            reverse("authentication:signup"),
            self.recruiter_data,
            follow=True,  # Follow redirects
        )
        # Initial response should be a redirect
        self.assertEqual(response.redirect_chain[0][1], 302)  # Redirect after success

        # Verify user was created with correct attributes
        user = User.objects.get(email=self.recruiter_data["email"])
        self.assertEqual(user.user_type, "recruiter")
        self.assertEqual(user.name, self.recruiter_data["name"])

        # Recruiter profiles are created as part of the signup process
        # We aren't testing that here, as it's handled by another app

    def test_login_allows_recruiter(self) -> None:
        """Recruiter users can log in successfully."""
        # Create a user first
        user_manager = cast(UserManager, User.objects)
        user = user_manager.create_user(
            email=self.recruiter_data["email"],
            password=self.recruiter_data["password1"],
            name=self.recruiter_data["name"],
            user_type="recruiter",
        )
        # Mark the user's email as verified to satisfy mandatory email checks
        EmailAddress.objects.create(
            user=user, email=user.email, primary=True, verified=True
        )

        # Try logging in
        response = self.client.post(
            reverse("authentication:login"),
            {
                "username": self.recruiter_data["email"],
                "password": self.recruiter_data["password1"],
            },
        )
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_login_blocks_job_seeker_accounts(self) -> None:
        """Legacy job seeker accounts are denied access."""
        user_manager = cast(UserManager, User.objects)
        user = user_manager.create_user(
            email="jobseeker@example.com",
            password="testpass123",
            name="Job Seeker",
            user_type="job_seeker",
        )
        EmailAddress.objects.create(
            user=user, email=user.email, primary=True, verified=True
        )

        response = self.client.post(
            reverse("authentication:login"),
            {
                "username": "jobseeker@example.com",
                "password": "testpass123",
            },
        )
        self.assertEqual(response.status_code, 200)  # Form re-rendered with errors
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        self.assertContains(response, "This account type is no longer supported")
