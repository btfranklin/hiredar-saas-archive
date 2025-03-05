"""Custom account adapter for user registration and redirection."""

from typing import Any, cast

from allauth.account.adapter import DefaultAccountAdapter
from django.http import HttpRequest
from django.urls import reverse

from apps.authentication.types import AuthenticatedUser


class AccountAdapter(DefaultAccountAdapter):
    """Custom account adapter for user registration and redirection."""

    def get_login_redirect_url(self, request: HttpRequest) -> str:
        """Return the appropriate dashboard URL based on user type."""
        assert request.user.is_authenticated, "User must be authenticated"
        user = cast(AuthenticatedUser, request.user)

        # If the user is an admin or has staff privileges, redirect to admin interface
        if user.user_type == "admin" or user.is_staff:
            return reverse("admin:index")

        # Otherwise redirect based on user type
        if user.user_type == "recruiter":
            return reverse("recruiters:dashboard")
        return reverse("job_seekers:dashboard")

    def get_signup_redirect_url(self, request: HttpRequest) -> str:
        """Return the appropriate profile creation URL based on user type."""
        assert request.user.is_authenticated, "User must be authenticated"
        user = cast(AuthenticatedUser, request.user)

        # If the user is an admin, redirect to admin interface
        if user.user_type == "admin" or user.is_staff:
            return reverse("admin:index")

        if user.user_type == "recruiter":
            return reverse("recruiters:profile")
        return reverse("job_seekers:profile_create")

    def save_user(
        self, request: HttpRequest, user: Any, form: Any, commit: bool = True
    ) -> AuthenticatedUser:
        """Save the user with additional fields from the signup form."""
        user = cast(
            AuthenticatedUser, super().save_user(request, user, form, commit=False)
        )

        # Get user type from the form
        user_type = request.POST.get("user_type")
        if user_type == "recruiter":
            user.user_type = "recruiter"  # type: ignore
        elif user_type == "job_seeker":
            user.user_type = "job_seeker"  # type: ignore

        if commit:
            user.save()

        return user
