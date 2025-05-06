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
            response = requests.post(
                "https://api.smtp2go.com/v3/email/send",
                json=payload,
                timeout=10,
            )
            response.raise_for_status()
            sent_count += 1
        return sent_count
