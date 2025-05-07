from typing import Any

import requests
from django.conf import settings
from django.core.cache import cache


def verify_email(email: str) -> dict[str, Any]:
    """
    Verify the given email address using QuickEmailVerification API.
    Returns the JSON response as a dict.

    Uses sandbox endpoint if USE_QUICKEMAILVERIFICATION_SANDBOX is True.
    """
    api_key = settings.QUICKEMAILVERIFICATION_API_KEY
    if not api_key:
        raise RuntimeError(
            "QUICKEMAILVERIFICATION_API_KEY is not configured in settings."
        )

    # Check cache first
    cache_key = f"qev:{email}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # Choose endpoint
    if getattr(settings, "USE_QUICKEMAILVERIFICATION_SANDBOX", False):
        url = "https://api.quickemailverification.com/v1/verify/sandbox"
    else:
        url = "https://api.quickemailverification.com/v1/verify"

    params = {"email": email, "apikey": api_key}
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    result = response.json()
    # Cache the result for 5 minutes to reuse for server-side validation
    cache.set(cache_key, result, timeout=300)
    return result
