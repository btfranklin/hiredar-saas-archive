"""Views for the authentication app."""

from .account_views import ChangePasswordView, UpdateAccountView
from .auth_views import (
    CustomLoginView,
    CustomLogoutView,
    JobSeekerSignupView,
    RecruiterSignupView,
)

__all__ = [
    "CustomLoginView",
    "CustomLogoutView",
    "JobSeekerSignupView",
    "RecruiterSignupView",
    "UpdateAccountView",
    "ChangePasswordView",
]
