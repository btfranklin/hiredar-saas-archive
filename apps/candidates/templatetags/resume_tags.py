"""Template filters for formatting resume content in candidate views."""

import re

from django import template
from django.utils.safestring import mark_safe

register = template.Library()

LABELS = [
    "Position:",
    "Company:",
    "Dates:",
    "Description:",
    "Impact:",
    "Institution:",
    "Degree:",
    "End Date:",
    "Certification:",
    "Issuer:",
]

pattern = re.compile(
    r"^(?P<label>(?:" + "|".join(re.escape(label) for label in LABELS) + r"))",
    re.MULTILINE,
)


@register.filter(name="bold_resume_labels")
def bold_resume_labels(value: str) -> str:
    """Wrap leading labels in <strong> tags to aid readability."""

    def replacer(match: re.Match[str]) -> str:
        return f"<strong>{match.group('label')}</strong>"

    result = pattern.sub(replacer, value)
    return mark_safe(result)

