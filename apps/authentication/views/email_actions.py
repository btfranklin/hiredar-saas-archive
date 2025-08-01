"""Views related to email actions such as sending verification e-mails."""

from typing import Any, cast

from allauth.account.models import EmailAddress
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.views import View

from apps.authentication.types import AuthenticatedUser


class SendVerificationEmailView(LoginRequiredMixin, View):
    """Send a verification e-mail to the currently logged-in user."""

    http_method_names = ["post"]

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Trigger a verification e-mail if the user's primary e-mail is unverified."""
        user = cast(AuthenticatedUser, request.user)

        email_address, _ = EmailAddress.objects.get_or_create(
            user=user,
            email=user.email,
            defaults={"primary": False},
        )

        if email_address.verified:
            messages.info(request, "Your email address is already verified.")
        else:
            # Send (or resend) confirmation using allauth's built-in helper on the model.
            email_address.send_confirmation(request, signup=False)  # type: ignore[arg-type]
            messages.success(
                request,
                "Verification e-mail sent! Check your inbox (or spam folder).",
            )

        # Redirect back to the appropriate settings page.
        if user.user_type == "job_seeker":
            return redirect("job_seekers:settings")
        return redirect("recruiters:settings")
