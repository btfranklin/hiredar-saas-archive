"""Custom account adapters for user registration and redirection."""

import uuid
from typing import Any, cast

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
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

    def populate_username(self, request, user):
        """
        Override username generation to use email as base.

        This completely overrides allauth's default username generation.
        """
        # If email is available, use it to generate a username
        if user.email:
            base = user.email.split("@")[0]
            random_suffix = uuid.uuid4().hex[:8]
            user.username = f"{base}_{random_suffix}"
        else:
            # Fallback to a random username
            user.username = f"user_{uuid.uuid4().hex[:10]}"

        return user.username

    def save_user(
        self, request: HttpRequest, user: Any, form: Any, commit: bool = True
    ) -> AuthenticatedUser:
        """Save the user with additional fields from the signup form."""
        # Then continue with parent implementation
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


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom social account adapter for social login processing.

    This adapter handles social login integration with the HireDAR user model,
    ensuring user type is properly set and users are redirected appropriately.
    """

    def pre_social_login(self, request: HttpRequest, sociallogin: Any) -> None:
        """
        Process the social login before it's saved.

        This is called before the user is logged in. We can use this to:
        1. Set default user type
        2. Pre-populate fields based on social account data
        """
        # Call the parent implementation first
        super().pre_social_login(request, sociallogin)

        # If this is a new user (about to be created), set default fields
        if not sociallogin.is_existing:
            # Get any user_type from session or POST data
            user_type = self._get_user_type(request)

            # Set default user type if specified
            if user_type in ["recruiter", "job_seeker"]:
                sociallogin.user.user_type = user_type
            else:
                # Always default to job_seeker if not specified
                sociallogin.user.user_type = "job_seeker"

            # Set name from social account if available
            if not sociallogin.user.name or sociallogin.user.name == "New User":
                if hasattr(sociallogin, "account") and hasattr(
                    sociallogin.account, "extra_data"
                ):
                    if sociallogin.account.provider == "google":
                        sociallogin.user.name = sociallogin.account.extra_data.get(
                            "name", "New User"
                        )
                    elif sociallogin.account.provider == "linkedin_oauth2":
                        first_name = sociallogin.account.extra_data.get("firstName", "")
                        last_name = sociallogin.account.extra_data.get("lastName", "")
                        if first_name or last_name:
                            sociallogin.user.name = f"{first_name} {last_name}".strip()

    def populate_username(self, request, user):
        """
        Override username generation to use email as base for social login.

        This completely overrides allauth's default username generation.
        """
        # If email is available, use it to generate a username
        if user.email:
            base = user.email.split("@")[0]
            random_suffix = uuid.uuid4().hex[:8]
            user.username = f"{base}_{random_suffix}"
        else:
            # Fallback to a random username
            user.username = f"user_{uuid.uuid4().hex[:10]}"

        return user.username

    def save_user(
        self, request: HttpRequest, sociallogin: Any, form: Any | None = None
    ) -> AuthenticatedUser:
        """
        Save the user created from social login.

        This customizes how the user is saved from a social account.
        """
        # Call the parent implementation first
        user = super().save_user(request, sociallogin, form)

        # Set anything else needed after saving
        if hasattr(user, "user_type") and not user.user_type:
            # Fallback if user_type wasn't set in pre_social_login
            user.user_type = "job_seeker"
            user.save(update_fields=["user_type"])

        return cast(AuthenticatedUser, user)

    def get_connect_redirect_url(self, request: HttpRequest, socialaccount: Any) -> str:
        """Handle redirect after connecting a social account to an existing user."""
        return reverse("authentication:settings")

    def _get_user_type(self, request: HttpRequest) -> str | None:
        """
        Get the user type from various sources.

        Order of precedence:
        1. POST data
        2. Session
        3. URL parameters
        4. Default to None (will be handled elsewhere)
        """
        # Try to get from POST data
        user_type = request.POST.get("user_type")
        if user_type in ["recruiter", "job_seeker"]:
            return user_type

        # Try to get from session
        user_type = request.session.get("user_type")
        if user_type in ["recruiter", "job_seeker"]:
            return user_type

        # Try to get from URL parameters
        user_type = request.GET.get("user_type")
        if user_type in ["recruiter", "job_seeker"]:
            return user_type

        return None
