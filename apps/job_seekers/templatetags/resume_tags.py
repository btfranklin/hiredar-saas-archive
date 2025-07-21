import re

from django import template
from django.utils.safestring import mark_safe

register = template.Library()

# Labels to bold when they appear at the start of a line
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

# Compile a regex to match these labels at the start of lines
pattern = re.compile(
    r"^(?P<label>(?:" + "|".join(re.escape(label) for label in LABELS) + r"))",
    re.MULTILINE,
)


def bold_resume_labels(value):
    def replacer(match):
        return "<strong>{}</strong>".format(match.group("label"))

    result = pattern.sub(replacer, value)
    return mark_safe(result)


register.filter("bold_resume_labels", bold_resume_labels)
