"""Tests for the authentication app views."""

from typing import cast

from django.test import Client, TestCase
from django.urls import reverse

from apps.authentication.models import User, UserManager


class AuthenticationViewTests(TestCase):
    """Test cases for authentication views."""

    def setUp(self) -> None:
        """Set up test data."""
        self.client = Client()
        self.job_seeker_data = {
            "email": "jobseeker@example.com",
            "password1": "testpass123",
            "password2": "testpass123",
            "name": "Job Seeker",
            "user_type": "job_seeker",
        }
        self.recruiter_data = {
            "email": "recruiter@example.com",
            "password1": "testpass123",
            "password2": "testpass123",
            "name": "Recruiter User",
            "user_type": "recruiter",
            "company_name": "Test Company",
        }

    def test_job_seeker_signup(self) -> None:
        """Test job seeker signup process."""
        response = self.client.post(
            reverse("authentication:job_seeker_signup"),
            self.job_seeker_data,
            follow=True,  # Follow redirects
        )
        # Initial response should be a redirect
        self.assertEqual(response.redirect_chain[0][1], 302)  # Redirect after success

        # Verify user was created with correct attributes
        user = User.objects.get(email=self.job_seeker_data["email"])
        self.assertEqual(user.user_type, "job_seeker")

        # Job seeker profiles are created as part of the signup process
        # We aren't testing that here, as it's handled by another app

    def test_recruiter_signup(self) -> None:
        """Test recruiter signup process."""
        response = self.client.post(
            reverse("authentication:recruiter_signup"),
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

    def test_login(self) -> None:
        """Test user login process."""
        # Create a user first
        user_manager = cast(UserManager, User.objects)
        user_manager.create_user(
            email=self.job_seeker_data["email"],
            password=self.job_seeker_data["password1"],
            name=self.job_seeker_data["name"],
            user_type=self.job_seeker_data["user_type"],
        )

        # Try logging in
        response = self.client.post(
            reverse("authentication:login"),
            {
                "username": self.job_seeker_data["email"],
                "password": self.job_seeker_data["password1"],
            },
        )
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertTrue(response.wsgi_request.user.is_authenticated)
