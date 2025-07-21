"""
Custom template filters for the matching app.
"""

import re

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def mul(value, arg):
    """
    Multiplies the value by the argument.

    Usage:
        {{ value|mul:10 }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


ANALYSIS_LABELS = [
    "✅ Proven Results & Achievements:",
    "✅ Skills & Qualifications Alignment:",
    "✅ Experience Relevance:",
    "🚀 Future Performance Potential:",
    "⚠️ Gaps & Challenges:",
]

pattern_analysis = re.compile(
    r"^(?P<label>(?:" + "|".join(re.escape(label) for label in ANALYSIS_LABELS) + r"))",
    re.MULTILINE,
)


def bold_analysis_headings(value):
    """
    Bold predefined analysis headings and add spacing.
    """

    def replacer(match):
        return '<strong class="block mt-4">{}</strong>'.format(match.group("label"))

    result = pattern_analysis.sub(replacer, value or "")
    return mark_safe(result)


register.filter("bold_analysis_headings", bold_analysis_headings)
register.filter("bold_analysis_headings", bold_analysis_headings)
