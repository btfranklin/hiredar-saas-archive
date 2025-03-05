"""Tests for the authentication app."""

from typing import cast

from django.test import Client, TestCase
from django.urls import reverse

from apps.authentication.models import User, UserManager


class UserModelTests(TestCase):
    """Test cases for the User model."""

    def setUp(self) -> None:
        """Set up test data."""
        self.user_data = {
            "email": "test@example.com",
            "password": "testpass123",
            "first_name": "Test",
            "last_name": "User",
        }

    def test_create_user(self) -> None:
        """Test creating a new user."""
        user_manager = cast(UserManager, User.objects)
        user = user_manager.create_user(**self.user_data)
        self.assertEqual(user.email, self.user_data["email"])
        self.assertTrue(user.check_password(self.user_data["password"]))
        self.assertEqual(user.get_full_name(), "Test User")

    def test_create_superuser(self) -> None:
        """Test creating a new superuser."""
        user_manager = cast(UserManager, User.objects)
        admin_user = user_manager.create_superuser(**self.user_data)
        self.assertTrue(admin_user.is_superuser)
        self.assertTrue(admin_user.is_staff)


class AuthenticationViewTests(TestCase):
    """Test cases for authentication views."""

    def setUp(self) -> None:
        """Set up test data."""
        self.client = Client()
        self.job_seeker_data = {
            "email": "jobseeker@example.com",
            "password": "testpass123",
            "first_name": "Job",
            "last_name": "Seeker",
            "user_type": "job_seeker",
        }
        self.recruiter_data = {
            "email": "recruiter@example.com",
            "password": "testpass123",
            "first_name": "Recruiter",
            "last_name": "User",
            "user_type": "recruiter",
            "company_name": "Test Company",
        }

    def test_job_seeker_signup(self) -> None:
        """Test job seeker signup process."""
        response = self.client.post(
            reverse("authentication:job_seeker_signup"),
            self.job_seeker_data,
        )
        self.assertEqual(response.status_code, 302)  # Redirect after success
        user = User.objects.get(email=self.job_seeker_data["email"])
        self.assertEqual(user.user_type, "job_seeker")
        self.assertTrue(hasattr(user, "job_seeker_profile"))

    def test_recruiter_signup(self) -> None:
        """Test recruiter signup process."""
        response = self.client.post(
            reverse("authentication:recruiter_signup"),
            self.recruiter_data,
        )
        self.assertEqual(response.status_code, 302)  # Redirect after success
        user = User.objects.get(email=self.recruiter_data["email"])
        self.assertEqual(user.user_type, "recruiter")
        self.assertTrue(hasattr(user, "recruiter_profile"))

    def test_login(self) -> None:
        """Test user login process."""
        # Create a user first
        user_manager = cast(UserManager, User.objects)
        user_manager.create_user(**self.job_seeker_data)

        # Try logging in
        response = self.client.post(
            reverse("authentication:login"),
            {
                "username": self.job_seeker_data["email"],
                "password": self.job_seeker_data["password"],
            },
        )
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertTrue(response.wsgi_request.user.is_authenticated)
