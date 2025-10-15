"""
LLM integration helpers for candidate profile enrichment workflows.
"""

from __future__ import annotations

import logging
import os

import requests
from django.conf import settings
from dotenv import load_dotenv
from promptdown import StructuredPrompt

from apps.candidates.models import CandidateProfile, CandidateRoleRecommendation
from apps.candidates.services.recommendation.xml_parser import (
    CandidateProfileEnrichment,
    parse_profile_enrichment_xml,
    parse_role_recommendations_xml,
)
from hiredar.llm import get_llm_response

load_dotenv()

logger = logging.getLogger(__name__)


def _require_api_key() -> str:
    api_key = settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
    if not api_key:
        error_msg = "No API key found. Set OPENAI_API_KEY for candidate workflows."
        logger.error(error_msg)
        raise ValueError(error_msg)
    return api_key


def generate_role_recommendations(resume_xml: str) -> list[CandidateRoleRecommendation]:
    """Return unsaved CandidateRoleRecommendation objects from resume XML."""
    _require_api_key()
    if not resume_xml:
        error_msg = "Unable to generate role recommendations: resume_xml is empty"
        logger.error(error_msg)
        raise ValueError(error_msg)

    prompt_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "prompts",
        "generate_role_recommendations_from_xml.prompt.md",
    )
    if not os.path.exists(prompt_path):
        raise ValueError(f"Prompt file not found at {prompt_path}")

    structured_prompt = StructuredPrompt.from_promptdown_file(prompt_path)
    wrapped_xml = f"```xml\n{resume_xml}\n```"
    structured_prompt.apply_template_values({"resume_xml": wrapped_xml})
    response_input = structured_prompt.to_responses_input()

    response_content = get_llm_response(
        response_input=response_input,
        model=settings.JOBSEEKERS_ROLE_RECOMMENDATION_MODEL,
        reasoning_effort=settings.JOBSEEKERS_ROLE_RECOMMENDATION_REASONING_EFFORT,
    )

    if not response_content or not isinstance(response_content, str):
        raise ValueError("LLM response content missing or invalid for recommendations")

    return parse_role_recommendations_xml(response_content)


def generate_personal_tagline(resume_xml: str) -> str:
    """Return a short personal tagline for recruiter-facing contexts."""
    _require_api_key()
    if not resume_xml:
        logger.error("Resume XML is empty or None")
        return "Unable to generate tagline: No resume data provided"

    prompt_path = os.path.join(
        settings.BASE_DIR,
        "apps",
        "resume_processing",
        "prompts",
        "generate_personal_tagline_from_xml.prompt.md",
    )
    if not os.path.exists(prompt_path):
        error_msg = f"Prompt file not found at path: {prompt_path}"
        logger.error(error_msg)
        return "Unable to generate tagline: Prompt file not found"

    structured_prompt = StructuredPrompt.from_promptdown_file(prompt_path)
    wrapped_xml = f"```xml\n{resume_xml}\n```"
    structured_prompt.apply_template_values({"resume_xml": wrapped_xml})
    response_input = structured_prompt.to_responses_input()

    tagline = get_llm_response(
        response_input=response_input,
        model=settings.JOBSEEKERS_TAGLINE_GENERATION_MODEL,
        max_tokens=settings.JOBSEEKERS_TAGLINE_MAX_TOKENS,
        reasoning_effort=getattr(
            settings,
            "JOBSEEKERS_TAGLINE_GENERATION_REASONING_EFFORT",
            "medium",
        ),
    )

    if not tagline or not isinstance(tagline, str):
        raise ValueError("LLM response content missing or invalid for tagline")

    return tagline.strip().strip('"').strip("'")


def generate_profile_enrichment(
    candidate_profile: CandidateProfile,
    interested_roles: list[str] | None = None,
) -> CandidateProfileEnrichment:
    """
    Produce recruiter-facing narrative content for a CandidateProfile.
    """
    _require_api_key()
    resume_xml = candidate_profile.resume_xml or ""
    if not resume_xml:
        raise ValueError("Cannot generate profile enrichment without resume_xml")

    prompt_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "prompts",
        "generate_talent_sheet_from_xml.prompt.md",
    )

    structured_prompt = StructuredPrompt.from_promptdown_file(prompt_path)
    interested_roles_str = ", ".join(interested_roles or [])
    wrapped_xml = f"```xml\n{resume_xml}\n```"

    structured_prompt.apply_template_values(
        {
            "resume_xml": wrapped_xml,
            "interested_roles": interested_roles_str,
        }
    )
    response_input = structured_prompt.to_responses_input()

    xml_response = get_llm_response(
        response_input=response_input,
        model=settings.JOBSEEKERS_TALENT_SHEET_MODEL,
        timeout=60,
        reasoning_effort=getattr(
            settings,
            "JOBSEEKERS_TALENT_SHEET_REASONING_EFFORT",
            "medium",
        ),
    )

    if not xml_response:
        raise ValueError("Empty response from LLM when generating talent sheet")

    try:
        enrichment = parse_profile_enrichment_xml(
            xml_response,
            candidate_profile=candidate_profile,
        )
    except requests.exceptions.RequestException:
        # Propagate network errors to callers
        raise
    except ValueError:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Unhandled error parsing profile enrichment XML: %s", exc)
        raise

    logger.info("Generated profile enrichment for CandidateProfile %s", candidate_profile.pk)
    return enrichment

