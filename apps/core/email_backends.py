from typing import Any

import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend


class SMTP2GOAPIEmailBackend(BaseEmailBackend):
    """
    An EmailBackend that uses the SMTP2GO HTTP API to send messages.
    """

    def send_messages(self, email_messages) -> int:
        sent_count = 0
        for message in email_messages:
            payload: dict[str, Any] = {
                "api_key": settings.SMTP2GO_API_KEY,
                "sender": message.from_email,
                "to": message.to,
                "subject": message.subject,
                "text_body": message.body,
            }
            # If there's an HTML alternative, add it
            for body, mimetype in getattr(message, "alternatives", []):
                if mimetype == "text/html":
                    payload["html_body"] = body
                    break
            try:
                # Use a slightly more lenient timeout – many transactional
                # email providers can take a little longer to respond under
                # heavy load.  A (connect_timeout, read_timeout) tuple is
                # supported by ``requests``; using it allows us to keep a
                # short connection timeout while giving the remote service
                # extra time to produce a response.
                response = requests.post(
                    "https://api.smtp2go.com/v3/email/send",
                    json=payload,
                    timeout=(3, 20),  # (connect, read) seconds
                )
                response.raise_for_status()
                sent_count += 1
            except requests.exceptions.ReadTimeout as exc:
                # A read timeout is usually transient.  Log the error and
                # continue without raising so the calling view does not
                # crash.  The user will have been created already – they can
                # request a new confirmation e-mail from their profile page.
                import logging

                logging.getLogger(__name__).warning(
                    "SMTP2GO read timeout while sending email: %s", exc
                )
                # Do not increment ``sent_count``; treat as unsent.
                continue
            except requests.exceptions.RequestException as exc:
                # For all other network-level errors we honour Django's
                # ``fail_silently`` semantics: raise only if the backend
                # was instantiated with ``fail_silently=False``.  Allauth
                # calls ``EmailMessage.send`` with ``fail_silently=False``,
                # so *by default* we re-raise.  Run-time environments can
                # switch to silent failures by calling ``EmailMessage.send(
                # fail_silently=True)`` or by instantiating the backend
                # directly with the flag set.
                import logging

                if getattr(self, "fail_silently", False):
                    logging.getLogger(__name__).error(
                        "SMTP2GO request exception suppressed due to fail_silently=True: %s",
                        exc,
                    )
                    continue
                raise
        return sent_count
