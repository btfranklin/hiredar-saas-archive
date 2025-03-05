"""
Account-related views for managing user account settings.

This module contains views for updating account information and changing passwords.
"""

from typing import Any, cast

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.generic import View

from apps.authentication.types import AuthenticatedUser


class UpdateAccountView(LoginRequiredMixin, View):
    """
    View for managing user settings.

    Displays and handles updates to user account information.
    """

    def get_template_name(self, user: AuthenticatedUser) -> str:
        """Get the appropriate template based on user type."""
        if user.user_type == "job_seeker":
            return "job_seekers/settings.html"
        return "recruiters/settings.html"

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Handle GET requests to display the settings page."""
        user = cast(AuthenticatedUser, request.user)
        template_name = self.get_template_name(user)
        return render(request, template_name, {"user": user})

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Handle POST requests for updating account information."""
        try:
            # Update User model fields
            user = cast(AuthenticatedUser, request.user)
            user.first_name = request.POST.get("first_name", "")
            user.last_name = request.POST.get("last_name", "")
            user.email = request.POST.get("email", "")
            user.location = request.POST.get("location", "")
            user.save()

            messages.success(request, "Account information updated successfully.")
            if user.user_type == "job_seeker":
                return redirect("job_seekers:settings")
            return redirect("recruiters:settings")

        except Exception as e:
            messages.error(request, f"Error updating account: {str(e)}")
            user = cast(AuthenticatedUser, request.user)
            if user.user_type == "job_seeker":
                return redirect("job_seekers:settings")
            return redirect("recruiters:settings")


class ChangePasswordView(LoginRequiredMixin, View):
    """
    View for changing user password.

    Uses Django's built-in PasswordChangeForm to validate and change passwords.
    """

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Handle POST requests for changing passwords."""
        # Using Django's built-in password change form for validation
        user = cast(AuthenticatedUser, request.user)
        form = PasswordChangeForm(user=user, data=request.POST)

        if form.is_valid():
            # Save the new password
            form.save()
            # Update the session to prevent the user from being logged out
            update_session_auth_hash(request, form.user)
            messages.success(request, "Your password was changed successfully.")
        else:
            # Get all form errors as a list
            error_messages: list[str] = []
            for field, field_errors in form.errors.items():
                for error in field_errors:
                    error_messages.append(f"{field}: {error}")

            # Join all errors with a semicolon
            error_message = "; ".join(error_messages)
            messages.error(request, f"Error changing password: {error_message}")

        if user.user_type == "job_seeker":
            return redirect("job_seekers:settings")
        return redirect("recruiters:settings")
