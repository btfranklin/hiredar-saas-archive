"""Tests for the authentication app models."""

from typing import cast

from django.test import TestCase

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
