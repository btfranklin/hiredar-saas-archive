"""Service layer for Job Seeker Workshop tools."""

import logging
import os
from typing import TYPE_CHECKING

from django.conf import settings
from promptdown import StructuredPrompt

from hiredar.llm import chat_complete

if TYPE_CHECKING:  # pragma: no cover
    from apps.job_seekers.models.profile import JobSeekerProfile

logger = logging.getLogger(__name__)

# Directory for markdown prompts
PROMPT_DIR = os.path.join(os.path.dirname(__file__), "prompts")

UPGRADE_PROMPT = os.path.join(PROMPT_DIR, "upgrade_resume.prompt.md")
TARGETED_PROMPT = os.path.join(PROMPT_DIR, "targeted_resume.prompt.md")
COVER_LETTER_PROMPT = os.path.join(PROMPT_DIR, "cover_letter.prompt.md")


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
    """Generate an upgraded version of the job seeker's resume."""

    resume_text = _compose_resume_text(profile)
    if not resume_text:
        raise ValueError("Profile lacks sufficient information to generate a resume.")

    if not os.path.exists(UPGRADE_PROMPT):
        logger.error("Prompt file not found: %s", UPGRADE_PROMPT)
        raise ValueError("Prompt file not found: upgrade resume prompt")

    structured_prompt = StructuredPrompt.from_promptdown_file(UPGRADE_PROMPT)
    structured_prompt.apply_template_values({"resume_text": resume_text})
    messages = structured_prompt.to_chat_completion_messages()

    logger.info(
        "Generating upgraded resume for profile_id=%s",
        getattr(profile, "id", "unknown"),
    )
    return chat_complete(
        messages=messages,
        model=settings.JOBSEEKERS_WORKSHOP_UPGRADE_MODEL,
        temperature=settings.JOBSEEKERS_WORKSHOP_UPGRADE_TEMPERATURE,
    )


def generate_targeted_documents(
    profile: "JobSeekerProfile", job_description: str
) -> dict[str, str]:
    """Generate a targeted resume and cover letter."""

    resume_text = _compose_resume_text(profile)
    if not resume_text:
        raise ValueError("Profile missing resume information.")

    # Targeted Resume
    if not os.path.exists(TARGETED_PROMPT):
        logger.error("Prompt file not found: %s", TARGETED_PROMPT)
        raise ValueError("Prompt file not found: targeted resume prompt")

    structured_prompt = StructuredPrompt.from_promptdown_file(TARGETED_PROMPT)
    structured_prompt.apply_template_values(
        {"resume_text": resume_text, "job_description": job_description}
    )
    messages = structured_prompt.to_chat_completion_messages()

    logger.info(
        "Generating targeted resume for profile_id=%s",
        getattr(profile, "id", "unknown"),
    )
    targeted_resume = chat_complete(
        messages=messages,
        model=settings.JOBSEEKERS_WORKSHOP_TARGETED_MODEL,
        temperature=settings.JOBSEEKERS_WORKSHOP_TARGETED_TEMPERATURE,
    )

    # Cover Letter
    if not os.path.exists(COVER_LETTER_PROMPT):
        logger.error("Prompt file not found: %s", COVER_LETTER_PROMPT)
        raise ValueError("Prompt file not found: cover letter prompt")

    structured_prompt = StructuredPrompt.from_promptdown_file(COVER_LETTER_PROMPT)
    structured_prompt.apply_template_values(
        {"resume_text": resume_text, "job_description": job_description}
    )
    messages = structured_prompt.to_chat_completion_messages()

    logger.info(
        "Generating cover letter for profile_id=%s",
        getattr(profile, "id", "unknown"),
    )
    cover_letter = chat_complete(
        messages=messages,
        model=settings.JOBSEEKERS_WORKSHOP_TARGETED_MODEL,
        temperature=settings.JOBSEEKERS_WORKSHOP_TARGETED_TEMPERATURE,
    )

    return {
        "targeted_resume": targeted_resume,
        "cover_letter": cover_letter,
    }
