"""Custom validators for authentication-related fields."""

from __future__ import annotations

import re
from typing import Final

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

_DISALLOWED_KEYWORDS: Final[tuple[str, ...]] = (
    "http://",
    "https://",
    "www.",
    ".com",
    ".net",
    ".org",
    ".io",
    ".co",
)
_URLISH_PATTERN: Final[re.Pattern[str]] = re.compile(r"(https?://|www\.)", re.IGNORECASE)
_LONG_PUNCTUATION_PATTERN: Final[re.Pattern[str]] = re.compile(r"[!#$%^&*_=+]{4,}")
_ALLOWED_SPECIAL_CHARACTERS: Final[set[str]] = {"-", "'", ".", ","}
_MAX_LENGTH: Final[int] = 80


def validate_recruiter_name(value: str) -> None:
    """Ensure recruiter-provided names look like human names."""
    if value is None:
        raise ValidationError(_("Please provide your name."))

    candidate = value.strip()
    if not candidate:
        raise ValidationError(_("Please provide your name."))

    if len(candidate) > _MAX_LENGTH:
        raise ValidationError(
            _("Name must be %(max_length)s characters or fewer."),
            params={"max_length": _MAX_LENGTH},
        )

    lower_candidate = candidate.lower()
    if any(keyword in lower_candidate for keyword in _DISALLOWED_KEYWORDS):
        raise ValidationError(
            _("Name cannot contain URLs or promotional text. Please use your real name.")
        )

    if _URLISH_PATTERN.search(candidate):
        raise ValidationError(
            _("Name cannot contain URLs or promotional text. Please use your real name.")
        )

    if _LONG_PUNCTUATION_PATTERN.search(candidate):
        raise ValidationError(
            _("Name cannot contain long runs of punctuation or special characters.")
        )

    humanish_count = sum(
        1
        for char in candidate
        if char.isalpha() or char.isspace() or char in _ALLOWED_SPECIAL_CHARACTERS
    )

    if humanish_count < len(candidate) / 2:
        raise ValidationError(
            _("Name appears to be spam. Please enter the name you use professionally.")
        )
