"""Template tags for handling skills in templates."""

from django import template

register = template.Library()


@register.filter
def skill_match_percentage(job_skills: str, user_skills: str) -> int:
    """
    Calculate the percentage of job skills that match user skills.

    Args:
        job_skills: Comma-separated string of job skills.
        user_skills: Comma-separated string of user skills.

    Returns:
        int: Percentage of matching skills (0-100).
    """
    if not job_skills or not user_skills:
        return 0

    job_skill_list = [s.strip().lower() for s in job_skills.split(",")]
    user_skill_list = [s.strip().lower() for s in user_skills.split(",")]

    if not job_skill_list:
        return 0

    matches = sum(1 for skill in job_skill_list if skill in user_skill_list)
    return int((matches / len(job_skill_list)) * 100)


@register.filter
def split(value: str | None, delimiter: str = ",") -> list[str]:
    """
    Split a string by a delimiter.

    Args:
        value: The string to split.
        delimiter: The delimiter to split by.

    Returns:
        list[str]: The split string.
    """
    if not value:
        return []
    return value.split(delimiter)


@register.filter
def strip(value: str | None) -> str:
    """
    Strip whitespace from a string.

    Args:
        value: The string to strip.

    Returns:
        str: The stripped string.
    """
    if not value:
        return ""
    return value.strip()
