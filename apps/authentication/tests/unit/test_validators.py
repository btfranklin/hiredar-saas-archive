"""Tests for authentication validators."""

import pytest
from django.core.exceptions import ValidationError

from apps.authentication.validators import validate_recruiter_name


@pytest.mark.parametrize(
    "name",
    [
        "Jane Doe",
        "Mary-Anne O'Neil",
        "Carlos M. Lopez",
        "A B",
    ],
)
def test_validate_recruiter_name_accepts_human_like_names(name: str) -> None:
    """Validator should allow typical human names."""
    validate_recruiter_name(name)


@pytest.mark.parametrize(
    "name",
    [
        "http://spam.example.com",
        "Best Offer visit www.spam.com now",
        "This is an amazing offer!!! $$$$",
        "1234567890 $$$$ 1234567890",
        "A" * 81,
        (
            "CLAIM A PREMIUM GIFT WORTH UP TO $100,000.77 "
            "https://telegra.ph/Get-a-gift-worth-up-to-10000077-10-24-59194?12531998"
        ),
        (
            "GET READY—YOUR GIFT UP TO $100,000.77 IS HERE "
            "https://telegra.ph/Get-a-gift-worth-up-to-10000077-10-24-73244?33323764"
        ),
    ],
)
def test_validate_recruiter_name_rejects_spammy_inputs(name: str) -> None:
    """Validator should reject spam-like names."""
    with pytest.raises(ValidationError):
        validate_recruiter_name(name)
