"""Service layer for Job Seeker Workshop tools."""

import logging
import os
import re
from typing import TYPE_CHECKING

from django.conf import settings
from promptdown import StructuredPrompt

from hiredar.llm import get_llm_response

if TYPE_CHECKING:  # pragma: no cover
    from apps.job_seekers.models.profile import JobSeekerProfile

logger = logging.getLogger(__name__)

# Directory for markdown prompts
PROMPT_DIR = os.path.join(os.path.dirname(__file__), "prompts")

UPGRADE_PROMPT = os.path.join(PROMPT_DIR, "upgrade_resume.prompt.md")
OPTIMIZE_LINKEDIN_PROMPT = os.path.join(PROMPT_DIR, "optimize_linkedin.prompt.md")


def _compose_resume_text(profile: "JobSeekerProfile") -> str:
    """Return a simple plain-text resume built from stored profile fields."""

    sections: list[str] = []
    if profile.professional_summary:
        sections.append("Professional Summary\n" + profile.professional_summary)
    if profile.most_recent_title or profile.years_of_experience:
        title_line = []
        if profile.most_recent_title:
            title_line.append(profile.most_recent_title)
        if profile.years_of_experience:
            title_line.append(f"{profile.years_of_experience} years experience")
        sections.append("Overview\n" + " | ".join(title_line))
    if profile.experience:
        sections.append("Experience\n" + profile.experience)
    if profile.education:
        sections.append("Education\n" + profile.education)
    if profile.certifications:
        sections.append("Certifications\n" + profile.certifications)
    if profile.skills:
        sections.append("Skills\n" + profile.skills)

    return "\n\n".join(sections)


def upgrade_resume_content(profile: "JobSeekerProfile") -> str:
    """Generate an upgraded version of the job seeker's resume.

    If the candidate has marked specific role recommendations as "interested", we
    pass those target roles into the prompt so the language model can tailor the
    rewrite accordingly.  When no such roles exist we fall back to the original
    behavior (the placeholder will be an empty string, which the prompt treats
    as "no target roles provided").
    """

    resume_text = _compose_resume_text(profile)
    if not resume_text:
        raise ValueError("Profile lacks sufficient information to generate a resume.")

    # ------------------------------------------------------------------
    # Collect any roles the user is actively interested in – these will be
    # injected into the prompt so the LLM can subtly bias achievements and
    # phrasing towards those positions.
    # ------------------------------------------------------------------
    try:
        # Local import to avoid circular dependencies during Django app setup
        from apps.job_seekers.models import RoleRecommendation  # type: ignore
    except ModuleNotFoundError:  # pragma: no cover – defensive in case of migrations
        interested_roles: list[str] = []
    else:
        interested_roles = list(
            RoleRecommendation.objects.filter(
                job_seeker=profile, is_candidate_interested=True
            ).values_list("role_title", flat=True)
        )

    # Join into a simple comma-separated string that the prompt can inject as a
    # single variable. An empty string signals "no target roles".
    target_roles = ", ".join(interested_roles)

    if not os.path.exists(UPGRADE_PROMPT):
        logger.error("Prompt file not found: %s", UPGRADE_PROMPT)
        raise ValueError("Prompt file not found: upgrade resume prompt")

    structured_prompt = StructuredPrompt.from_promptdown_file(UPGRADE_PROMPT)
    structured_prompt.apply_template_values(
        {"resume_text": resume_text, "target_roles": target_roles}
    )
    response_input = structured_prompt.to_responses_input()

    logger.info(
        "Generating upgraded resume for profile_id=%s (target_roles_count=%s)",
        getattr(profile, "id", "unknown"),
        len(interested_roles),
    )
    return get_llm_response(
        response_input=response_input,
        model=settings.JOBSEEKERS_WORKSHOP_RESUME_UPGRADE_MODEL,
        reasoning_effort=getattr(
            settings,
            "JOBSEEKERS_WORKSHOP_RESUME_UPGRADE_REASONING_EFFORT",
            "medium",
        ),
    )


# ---------------------------------------------------------------------------
# LinkedIn Optimization
# ---------------------------------------------------------------------------


def optimize_linkedin_content(profile: "JobSeekerProfile") -> str:
    """Generate an optimized LinkedIn headline and About section.

    The model receives the same core resume text plus any target roles the
    candidate expressed interest in. It returns markdown containing exactly two
    sections: *LinkedIn Headline* and *About*.
    """

    resume_text = _compose_resume_text(profile)
    if not resume_text:
        raise ValueError(
            "Profile lacks sufficient information to generate LinkedIn content."
        )

    try:
        from apps.job_seekers.models import RoleRecommendation  # type: ignore
    except ModuleNotFoundError:  # pragma: no cover
        interested_roles: list[str] = []
    else:
        interested_roles = list(
            RoleRecommendation.objects.filter(
                job_seeker=profile, is_candidate_interested=True
            ).values_list("role_title", flat=True)
        )

    target_roles = ", ".join(interested_roles)

    if not os.path.exists(OPTIMIZE_LINKEDIN_PROMPT):
        logger.error("Prompt file not found: %s", OPTIMIZE_LINKEDIN_PROMPT)
        raise ValueError("Prompt file not found: optimize LinkedIn prompt")

    structured_prompt = StructuredPrompt.from_promptdown_file(OPTIMIZE_LINKEDIN_PROMPT)
    structured_prompt.apply_template_values(
        {"resume_text": resume_text, "target_roles": target_roles}
    )
    response_input = structured_prompt.to_responses_input()

    logger.info(
        "Generating LinkedIn optimization for profile_id=%s (target_roles_count=%s)",
        getattr(profile, "id", "unknown"),
        len(interested_roles),
    )

    return get_llm_response(
        response_input=response_input,
        model=settings.JOBSEEKERS_WORKSHOP_LINKEDIN_MODEL,
        reasoning_effort=getattr(
            settings,
            "JOBSEEKERS_WORKSHOP_LINKEDIN_REASONING_EFFORT",
            "medium",
        ),
    )


class _ParsedResumeProfile:
    """Lightweight stand-in for :class:`JobSeekerProfile` created from markdown.

    This lets us reuse existing resume detail templates that expect a model
    instance with various text attributes and a ``skills_list`` helper.
    """

    def __init__(self, **sections: str):
        # Store all provided sections verbatim on the instance so template code
        # can reference ``.professional_summary`` / ``.experience`` / …
        for key, value in sections.items():
            setattr(self, key, value.strip())

    # ------------------------------------------------------------------
    # Template helpers expected by existing resume components
    # ------------------------------------------------------------------

    @property
    def skills_list(self) -> list[str]:  # noqa: D401 – simple list helper
        """Return the skills section as a list (splits on comma & newlines)."""

        skills = getattr(self, "skills", "")
        if not skills:
            return []

        # Handle either comma-separated inline lists or newline/bullet lists
        raw_items = re.split(r"[\n,]", skills)
        return [item.strip(" -*\t") for item in raw_items if item.strip()]


# ---------------------------------------------------------------------------
# Markdown parsing helpers
# ---------------------------------------------------------------------------


def _parse_resume_markdown(markdown_text: str) -> _ParsedResumeProfile:
    """Very small heuristic parser that extracts common resume sections.

    The upgraded resume comes back as Markdown. We slice it into sections
    based on leading heading markers ("#", "##", etc.) and map those headings
    onto :class:`JobSeekerProfile` field names. This is *good enough* for
    display purposes – we are **not** trying to perform full semantic parsing
    here.
    """

    # Build a mapping from lower-cased heading label → profile attribute
    # These must stay in sync with the mandated headings in our LLM prompts.
    heading_to_attr = {
        "professional summary": "professional_summary",
        "skills": "skills",
        "experience": "experience",
        "education": "education",
        "certifications": "certifications",
    }

    # Split the markdown into (heading, block) pairs
    pattern = re.compile(r"^\s*#+\s*(.+?)\s*$", re.MULTILINE)
    sections: dict[str, str] = {}

    headings = list(pattern.finditer(markdown_text))
    for idx, match in enumerate(headings):
        heading = match.group(1).strip().lower()
        start = match.end()
        end = (
            headings[idx + 1].start() if idx + 1 < len(headings) else len(markdown_text)
        )
        body = markdown_text[start:end].strip()
        if heading in heading_to_attr:
            sections[heading_to_attr[heading]] = body

    # Fallback: if we didn't detect headings we assume the *entire* markdown is a summary
    if not sections and markdown_text.strip():
        sections["professional_summary"] = markdown_text.strip()

    return _ParsedResumeProfile(**sections)


# Expose parser for external use
parse_resume_markdown = _parse_resume_markdown


# ---------------------------------------------------------------------------
# Markdown parsing helpers for LinkedIn content
# ---------------------------------------------------------------------------


def _parse_linkedin_markdown(markdown_text: str) -> dict[str, str]:
    """Parse the markdown returned by the LLM into headline / about parts."""

    pattern = re.compile(r"^\s*#+\s*(.+?)\s*$", re.MULTILINE)
    sections: dict[str, str] = {}

    headings = list(pattern.finditer(markdown_text))
    for idx, match in enumerate(headings):
        heading = match.group(1).strip().lower()
        start = match.end()
        end = (
            headings[idx + 1].start() if idx + 1 < len(headings) else len(markdown_text)
        )
        body = markdown_text[start:end].strip()

        if heading in {"linkedin headline", "headline"}:
            sections["headline"] = body
        elif heading in {"about", "about section"}:
            sections["about"] = body

    # Fallback: entire markdown as about if parsing failed
    if not sections and markdown_text.strip():
        sections["about"] = markdown_text.strip()

    return sections


# Expose parser for external use
parse_linkedin_markdown = _parse_linkedin_markdown
