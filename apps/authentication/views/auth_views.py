"""Authentication views for user signup, login, and logout."""

from typing import cast

from allauth.account.views import SignupView
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponseRedirect
from django.urls import reverse

from apps.authentication.forms import (
    CustomAuthenticationForm,
    JobSeekerSignupForm,
    RecruiterSignupForm,
)
from apps.authentication.models import User
from apps.authentication.types import AuthenticatedUser


class JobSeekerSignupView(SignupView):
    """
    View for job seeker signup process.

    This view extends allauth's SignupView to handle job seeker registrations.
    It uses the JobSeekerSignupForm to properly set the user_type and name.
    """

    template_name = "job_seekers/signup.html"
    form_class = JobSeekerSignupForm

    def get_success_url(self) -> str:
        """Return the profile creation URL after successful signup."""
        return reverse("job_seekers:profile_create")


class RecruiterSignupView(SignupView):
    """
    View for recruiter signup process.

    This view extends allauth's SignupView to handle recruiter registrations.
    It uses the RecruiterSignupForm to properly collect name and set user_type.
    """

    template_name = "recruiters/signup.html"
    form_class = RecruiterSignupForm

    def get_success_url(self) -> str:
        """Return the recruiter dashboard URL after successful signup."""
        return reverse("recruiters:dashboard")


class CustomLoginView(SuccessMessageMixin, LoginView):
    """Custom login view that uses email authentication."""

    template_name = "authentication/login.html"
    success_message = "Welcome back!"
    form_class = CustomAuthenticationForm

    def get_success_url(self) -> str:
        """Return the appropriate dashboard based on user type."""
        if not self.request.user.is_authenticated:
            # Default to home page if not authenticated
            return reverse("core:home")

        # User is authenticated, redirect based on user type
        user = cast(AuthenticatedUser, self.request.user)

        # If the user is an admin or has staff privileges, redirect to admin interface
        if user.user_type == "admin" or user.is_staff:
            return reverse("admin:index")

        if user.user_type == "recruiter":
            return reverse("recruiters:dashboard")
        return reverse("job_seekers:dashboard")

    def form_valid(self, form: CustomAuthenticationForm) -> HttpResponseRedirect:
        """Process the form if it is valid, enforcing email verification."""
        # Check if email verification is mandatory and user is unverified
        user = getattr(form, "user_cache", None) or self.request.user
        from allauth.account.utils import has_verified_email, send_email_confirmation
        from django.conf import settings
        from django.http import HttpResponseRedirect
        from django.urls import reverse

        if getattr(settings, "ACCOUNT_EMAIL_VERIFICATION", "").lower() == "mandatory":
            # If the user has not verified their primary email, resend confirmation and redirect
            if not has_verified_email(user):
                send_email_confirmation(self.request, user)
                return HttpResponseRedirect(reverse("account_email_verification_sent"))

        # Proceed with normal login
        result = super().form_valid(form)
        # Customize the success message
        if self.request.user.is_authenticated:
            user = cast(User, self.request.user)
            full_name = user.get_full_name() or user.email
            self.success_message = f"Welcome back, {full_name}!"
        return cast(HttpResponseRedirect, result)


class CustomLogoutView(LogoutView):
    """Custom logout view."""

    template_name = "authentication/logout.html"
    next_page = "/"
    http_method_names = ["get", "post", "options"]
