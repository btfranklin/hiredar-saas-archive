"""Views for the authentication app."""

from .account_views import ChangePasswordView, UpdateAccountView
from .auth_views import CustomLoginView, CustomLogoutView, RecruiterSignupView

__all__ = [
    "CustomLoginView",
    "CustomLogoutView",
    "RecruiterSignupView",
    "UpdateAccountView",
    "ChangePasswordView",
]
