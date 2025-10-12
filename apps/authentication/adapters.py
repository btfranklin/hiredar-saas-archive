"""Custom account adapters for user registration and redirection."""

import logging
import uuid
from typing import Any, cast

from allauth.account import app_settings as account_settings
from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.internal import flows
from allauth.account.models import EmailAddress
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.http import HttpRequest
from django.shortcuts import redirect
from django.urls import reverse

from apps.authentication.services.email_verifier import verify_email
from apps.authentication.types import AuthenticatedUser

logger = logging.getLogger(__name__)


class AccountAdapter(DefaultAccountAdapter):
    """Custom account adapter for user registration and redirection."""

    def get_login_redirect_url(self, request: HttpRequest) -> str:
        """Return the appropriate dashboard URL based on user type."""
        assert request.user.is_authenticated, "User must be authenticated"
        user = cast(AuthenticatedUser, request.user)

        # If the user is an admin or has staff privileges, redirect to admin interface
        if user.user_type == "admin" or user.is_staff:
            return reverse("admin:index")

        # Otherwise redirect recruiters to their dashboard
        return reverse("recruiters:dashboard")

    def get_signup_redirect_url(self, request: HttpRequest) -> str:
        """Return the appropriate profile creation URL based on user type."""
        assert request.user.is_authenticated, "User must be authenticated"
        user = cast(AuthenticatedUser, request.user)

        # If the user is an admin, redirect to admin interface
        if user.user_type == "admin" or user.is_staff:
            return reverse("admin:index")

        # Redirect recruiters to their dashboard (no standalone profile page exists)
        return reverse("recruiters:dashboard")

    # --------------------------------------------------
    # E-mail Confirmation Flow
    # --------------------------------------------------
    def get_email_verification_redirect_url(  # type: ignore[override]
        self,
        email_address,  # allauth.account.models.EmailAddress
    ) -> str:
        """Return the URL to redirect to after an e-mail verification."""
        user = getattr(email_address, "user", None)
        if user is not None:
            if getattr(user, "user_type", None) == "admin" or getattr(
                user, "is_staff", False
            ):
                return reverse("admin:index")
            if getattr(user, "user_type", None) == "recruiter":
                return reverse("recruiters:dashboard")
        # Default: recruiter dashboard
        return reverse("recruiters:dashboard")

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

        # All self-service accounts are recruiters
        user.user_type = "recruiter"  # type: ignore

        if commit:
            user.save()

        return user

    def clean_email(self, email: str) -> str:
        """
        Validate email via QuickEmailVerification before Allauth confirmation.
        Raises ValidationError if the API reports the address invalid.
        """
        try:
            result = verify_email(email)
        except Exception as e:
            raise ValidationError(
                "Could not verify email address. Please try again later."
            ) from e
        status = result.get("result", "").lower()
        safe_to_send = result.get("safe_to_send")
        ok = status in ("valid", "deliverable") or str(safe_to_send).lower() == "true"
        if not ok:
            reason = result.get("reason", "unknown error").replace("_", " ")
            raise ValidationError(f"Email address appears invalid: {reason}.")
        try:
            return super().clean_email(email)
        except ValidationError as exc:
            # Duplicate email error: user should log in instead of signing up
            raise ValidationError(
                "An account with this email already exists. Please log in instead."
            ) from exc

    def send_confirmation_mail(
        self, request: HttpRequest, emailconfirmation, signup: bool
    ) -> None:
        """
        Send the confirmation mail unless in DEBUG mode or
        an override address is set, in which case log instead of sending.
        """
        # Build context for rendering the email
        ctx: dict[str, Any] = {
            "request": request,
            "email": emailconfirmation.email_address.email,
            "current_site": get_current_site(request),
            "user": emailconfirmation.email_address.user,
        }
        if account_settings.EMAIL_VERIFICATION_BY_CODE_ENABLED:
            ctx["code"] = emailconfirmation.key
        else:
            ctx["key"] = emailconfirmation.key
            ctx["activate_url"] = flows.email_verification.get_email_verification_url(
                request, emailconfirmation
            )
        template = (
            "account/email/email_confirmation_signup"
            if signup
            else "account/email/email_confirmation"
        )
        message = self.render_mail(template, emailconfirmation.email_address.email, ctx)

        # If in debug or override set, log and skip sending
        if settings.DEBUG or getattr(
            settings, "EMAIL_VERIFICATION_OVERRIDE_ADDRESS", None
        ):
            logger.info(
                "Confirmation email for %s NOT sent. Subject: %s; Body: %s",
                emailconfirmation.email_address.email,
                getattr(message, "subject", ""),
                getattr(message, "body", ""),
            )
            return

        # Otherwise, optionally override recipient and send
        override = getattr(settings, "EMAIL_VERIFICATION_OVERRIDE_ADDRESS", None)
        if override:
            original = emailconfirmation.email_address.email
            emailconfirmation.email_address.email = override

        # --------------------------------------------------
        # Use django-post-office immediate priority so the
        # verification e-mail goes out synchronously.
        # --------------------------------------------------
        setattr(message, "priority", "now")  # mark for immediate send
        message.send(fail_silently=False)

        if override:
            emailconfirmation.email_address.email = original

        logger.info(
            "Sent immediate confirmation e-mail to %s (signup=%s)",
            emailconfirmation.email_address.email,
            signup,
        )
        return  # skip parent implementation

    # ------------------------------------------------------------------
    #  Immediate-send priority for *all* system e-mails
    # ------------------------------------------------------------------
    def render_mail(
        self,
        template_prefix: str,
        email: str,
        context: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> EmailMessage | EmailMultiAlternatives:
        """Wrap parent implementation, tagging the message for instant send.

        We delegate all heavy lifting (context augmentation, subject formatting,
        multi-part rendering, etc.) to the base class, then simply mark the
        resulting ``EmailMessage`` with ``priority='now'``.  The subsequent
        call to ``message.send()`` performed by ``DefaultAccountAdapter`` will
        therefore bypass the Post-Office queue.
        """

        message = super().render_mail(template_prefix, email, context, headers=headers)
        setattr(message, "priority", "now")
        return message


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

        # ------------------------------------------------------------------
        # Simplified flow based solely on whether that e-mail is already
        # present in our database.  If the social account is *not* already
        # linked (`sociallogin.is_existing` is False) and we see that the
        # e-mail address is registered, we assume the user should log in
        # and *not* create a duplicate account.
        # ------------------------------------------------------------------

        user_email = getattr(sociallogin.user, "email", None)
        email_address_exists = (
            bool(user_email) and EmailAddress.objects.filter(email=user_email).exists()
        )

        if not sociallogin.is_existing and email_address_exists:
            messages.error(
                request,
                "An account with this email already exists. Please log in instead.",
                fail_silently=True,
            )
            raise ImmediateHttpResponse(redirect("authentication:login"))

        # If this is a new user (about to be created), set default fields
        if not sociallogin.is_existing:
            sociallogin.user.user_type = "recruiter"

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
                        extra_data = sociallogin.account.extra_data or {}
                        first_name = extra_data.get(
                            "localizedFirstName"
                        ) or extra_data.get("firstName", "")
                        last_name = extra_data.get(
                            "localizedLastName"
                        ) or extra_data.get("lastName", "")
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
            user.user_type = "recruiter"
            user.save(update_fields=["user_type"])

        # Auto-verify LinkedIn-sourced email, both legacy and OIDC providers
        if sociallogin.account.provider in ("linkedin_oauth2", "linkedin"):
            # Verify primary email
            EmailAddress.objects.filter(user=user, email=user.email).update(
                verified=True,
                primary=True,
            )
            # Extract name from LinkedIn extra_data
            extra_data = sociallogin.account.extra_data or {}
            # Try legacy and OIDC fields
            first_name = (
                extra_data.get("localizedFirstName")
                or extra_data.get("firstName")
                or extra_data.get("given_name")
                or ""
            )
            last_name = (
                extra_data.get("localizedLastName")
                or extra_data.get("lastName")
                or extra_data.get("family_name")
                or ""
            )
            if first_name or last_name:
                full_name = f"{first_name} {last_name}".strip()
            else:
                full_name = extra_data.get("name", "") or extra_data.get(
                    "full_name", ""
                )
            if full_name:
                user.name = full_name
            # Mark user as US certified for social signup
            user.is_us_certified = True
            user.save(update_fields=["name", "is_us_certified"])

        return cast(AuthenticatedUser, user)

    def get_connect_redirect_url(self, request: HttpRequest, socialaccount: Any) -> str:
        """Handle redirect after connecting a social account to an existing user."""
        return reverse("authentication:settings")
