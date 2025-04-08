"""
Custom template filters for the matching app.
"""

from django import template

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
