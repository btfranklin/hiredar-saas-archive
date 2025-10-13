"""Views for real-time e-mail verification feedback."""

import logging
from typing import Any

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views import View

from apps.authentication.services.email_verifier import verify_email

logger = logging.getLogger(__name__)


class QuickEmailVerificationView(View):
    """
    HTMX endpoint that verifies an email in real time via QuickEmailVerification API.
    Renders the _email_verification.html snippet with success or error context.
    """

    def get(
        self, request: HttpRequest, *_args: Any, **_kwargs: Any
    ) -> HttpResponse:
        """Render verification result snippet for the provided e-mail."""
        email = request.GET.get("email", "").strip()
        if not email:
            return render(
                request,
                "authentication/_email_verification.html",
                {"error": "Please enter an email address"},
            )
        try:
            result = verify_email(email)
        except Exception:
            logger.exception("QuickEmailVerification API error")
            return render(
                request,
                "authentication/_email_verification.html",
                {"error": "Verification service error, please try again later."},
            )
        status = result.get("result", "").lower()
        safe_to_send = result.get("safe_to_send")
        success = (
            status in ("valid", "deliverable") or str(safe_to_send).lower() == "true"
        )
        return render(
            request,
            "authentication/_email_verification.html",
            {
                "success": success,
                "reason": result.get("reason", "").replace("_", " "),
            },
        )
