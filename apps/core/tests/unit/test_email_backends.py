from __future__ import annotations

from unittest.mock import patch

import requests
from django.core.mail import EmailMessage
from django.test import TestCase

from apps.core.email_backends import SMTP2GOAPIEmailBackend


class SMTP2GOAPIEmailBackendTests(TestCase):
    """Verify robustness of the custom SMTP2GO HTTP email backend."""

    def _simple_email(self):  # type: ignore[no-self-use]
        """Return a minimal EmailMessage instance for use in tests."""
        return EmailMessage(
            subject="Test subject",
            body="Plain-text body",
            from_email="sender@example.com",
            to=["recipient@example.com"],
        )

    # ------------------------------------------------------------------
    # Timeout handling
    # ------------------------------------------------------------------

    def test_read_timeout_is_swallowed_and_returns_zero(self):
        """A ReadTimeout should not bubble up and should report as unsent."""
        backend = SMTP2GOAPIEmailBackend()
        email = self._simple_email()

        with patch(
            "apps.core.email_backends.requests.post",
            side_effect=requests.exceptions.ReadTimeout,
        ):
            sent = backend.send_messages([email])

        self.assertEqual(sent, 0)

    # ------------------------------------------------------------------
    # Generic RequestException behavior – fail_silently variations
    # ------------------------------------------------------------------

    def test_request_exception_suppressed_when_fail_silently(self):
        """With fail_silently=True generic errors should be swallowed."""
        backend = SMTP2GOAPIEmailBackend(fail_silently=True)
        email = self._simple_email()

        with patch(
            "apps.core.email_backends.requests.post",
            side_effect=requests.exceptions.RequestException,
        ):
            sent = backend.send_messages([email])

        self.assertEqual(sent, 0)

    def test_request_exception_propagates_when_not_silent(self):
        """With fail_silently=False generic errors should propagate."""
        backend = SMTP2GOAPIEmailBackend(fail_silently=False)
        email = self._simple_email()

        with patch(
            "apps.core.email_backends.requests.post",
            side_effect=requests.exceptions.RequestException,
        ):
            with self.assertRaises(requests.exceptions.RequestException):
                backend.send_messages([email])
