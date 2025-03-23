"""URL patterns for the authentication app."""

from django.urls import path
from django.urls.resolvers import URLPattern

from apps.authentication.views.account_views import (
    ChangePasswordView,
    UpdateAccountView,
)
from apps.authentication.views.auth_views import (
    CustomLoginView,
    CustomLogoutView,
    JobSeekerSignupView,
    RecruiterSignupView,
)

app_name = "authentication"

urlpatterns: list[URLPattern] = [
    # Authentication URLs
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", CustomLogoutView.as_view(), name="logout"),
    path("signup/job-seeker/", JobSeekerSignupView.as_view(), name="job_seeker_signup"),
    path("signup/recruiter/", RecruiterSignupView.as_view(), name="recruiter_signup"),
    # Settings URLs
    path("settings/", UpdateAccountView.as_view(), name="settings"),
    path("settings/password/", ChangePasswordView.as_view(), name="change_password"),
]
