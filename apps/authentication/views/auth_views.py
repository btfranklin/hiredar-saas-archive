"""Authentication views for user signup, login, and logout."""

import uuid
from typing import cast

from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.messages.views import SuccessMessageMixin
from django.forms import BaseModelForm
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import CreateView

from apps.authentication.forms import CustomAuthenticationForm
from apps.authentication.models import User
from apps.authentication.types import AuthenticatedUser


class JobSeekerSignupView(CreateView):
    """
    View for job seeker signup process.

    This view handles the registration of new job seeker users, creating both a User
    and JobSeekerProfile instance. It uses email as username and sets the user_type to
    'job_seeker'.
    """

    template_name = "job_seekers/signup.html"
    model = User
    fields = ["email", "password"]  # Simplified to only require email and password

    def get_success_url(self) -> str:
        """Return the profile creation URL."""
        return reverse("job_seekers:profile_create")

    def form_valid(self, form: BaseModelForm) -> HttpResponseRedirect:
        """Process the form if it is valid."""
        # Check if user with this email already exists
        email = form.cleaned_data["email"]
        if User.objects.filter(email=email).exists():
            form.add_error("email", "A user with this email already exists")
            return cast(HttpResponseRedirect, self.form_invalid(form))

        user = form.save(commit=False)
        # Generate a unique username based on email to avoid collisions
        username_base = email.split("@")[0]
        # Add a random suffix to ensure uniqueness
        random_suffix = uuid.uuid4().hex[:8]
        user.username = f"{username_base}_{random_suffix}"
        user.set_password(form.cleaned_data["password"])
        user.user_type = "job_seeker"
        # Default name until resume is parsed
        user.name = "New User"
        user.save()

        # Log in the user with allauth's backend
        login(
            self.request,
            user,
            backend="allauth.account.auth_backends.AuthenticationBackend",
        )

        return HttpResponseRedirect(self.get_success_url())


class RecruiterSignupView(CreateView):
    """
    View for recruiter signup process.

    This view handles the registration of new recruiter users, creating both a User
    and RecruiterProfile instance.
    """

    template_name = "recruiters/signup.html"
    model = User
    fields = ["email", "name", "password"]  # Include name field for recruiters

    def get_success_url(self) -> str:
        """Return the recruiter dashboard URL."""
        return reverse("recruiters:dashboard")

    def form_valid(self, form: BaseModelForm) -> HttpResponseRedirect:
        """Process the form if it is valid."""
        # Check if user with this email already exists
        email = form.cleaned_data["email"]
        if User.objects.filter(email=email).exists():
            form.add_error("email", "A user with this email already exists")
            return cast(HttpResponseRedirect, self.form_invalid(form))

        # Validate that name is provided for recruiters
        name = form.cleaned_data.get("name", "").strip()
        if not name or name == "New User":
            form.add_error("name", "Please provide your name")
            return cast(HttpResponseRedirect, self.form_invalid(form))

        user = form.save(commit=False)
        # Generate a unique username based on email to avoid collisions
        username_base = email.split("@")[0]
        # Add a random suffix to ensure uniqueness
        random_suffix = uuid.uuid4().hex[:8]
        user.username = f"{username_base}_{random_suffix}"
        user.set_password(form.cleaned_data["password"])
        user.user_type = "recruiter"
        user.name = name  # Use the validated name
        user.save()

        # Log in the user with allauth's backend
        login(
            self.request,
            user,
            backend="allauth.account.auth_backends.AuthenticationBackend",
        )

        return HttpResponseRedirect(self.get_success_url())


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
        """Process the form if it is valid."""
        # Let the parent class handle the login
        result = super().form_valid(form)

        # Customize the success message if needed
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
