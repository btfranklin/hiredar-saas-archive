"""
LLM integration for job seeker recommendations.

This module contains functions for sending resume data to LLM services
and processing the responses to generate recommendations.
"""

import logging
import os
from typing import Any, Iterable, cast

import requests
from django.conf import settings  # Import Django settings
from dotenv import load_dotenv
from openai import OpenAI
from promptdown import StructuredPrompt

from apps.job_seekers.models import JobSeekerProfile, RoleRecommendation, TalentSheet
from apps.job_seekers.services.recommendation.xml_parser import (
    parse_role_recommendations_xml,
    parse_talent_sheet_xml,
)

# Load environment variables
load_dotenv()

# Setup logging
logger = logging.getLogger(__name__)


def generate_role_recommendations(resume_xml: str) -> list[RoleRecommendation]:
    """
    Generate role recommendations based on the job seeker's resume XML.

    This function sends the job seeker's resume XML to an LLM to generate
    a list of recommended career roles with descriptions.

    Args:
        resume_xml: The XML representation of the job seeker's resume

    Returns:
        A list of RoleRecommendation objects (unsaved to database)

    Raises:
        ValueError: If the API key is missing or the LLM response is invalid
        requests.exceptions.RequestException: If the API request fails
        Exception: For any other processing errors
    """
    # Use settings for API key if available, fall back to env var (for compatibility)
    api_key = settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
    if not api_key:
        error_msg = "No API key found. Set OPENAI_API_KEY environment variable."
        logger.error(error_msg)
        raise ValueError(error_msg)

    # Check XML content
    if not resume_xml:
        logger.error("Resume XML is empty or None!")
        raise ValueError(
            "Unable to generate role recommendations: No resume data provided"
        )

    prompt_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "prompts",
        "generate_role_recommendations_from_xml.prompt.md",
    )

    # Check if prompt file exists
    if not os.path.exists(prompt_path):
        logger.error("Prompt file not found at path: %s", prompt_path)
        raise ValueError(
            "Unable to generate role recommendations: Prompt file not found"
        )

    try:
        structured_prompt = StructuredPrompt.from_promptdown_file(prompt_path)

        # Wrap the XML in markdown code block
        wrapped_xml = f"```xml\n{resume_xml}\n```"

        # Apply the template values
        structured_prompt.apply_template_values(
            {
                "resume_xml": wrapped_xml,
            }
        )

        # Get messages for the API call
        messages = structured_prompt.to_chat_completion_messages()

    except Exception as e:
        logger.error("Error preparing prompt: %s", str(e))
        raise ValueError(
            f"Unable to generate role recommendations: Error preparing prompt: {str(e)}"
        ) from e

    client = OpenAI(api_key=api_key)

    # Log the start of processing
    logger.info("Sending resume XML to LLM for role recommendations generation")
    logger.debug("XML length: %d characters", len(resume_xml))

    # Make the API call with proper error handling
    try:
        completion = client.chat.completions.create(
            model=settings.JOBSEEKERS_ROLE_RECOMMENDATION_MODEL,  # Renamed setting
            messages=cast(Iterable[Any], messages),
            temperature=settings.JOBSEEKERS_RECOMMENDATION_TEMPERATURE,  # Use settings
        )

        # Extract the content from the response
        response_content = completion.choices[0].message.content

        # Perform basic validation
        if not response_content or not isinstance(response_content, str):
            error_msg = "LLM response content is None or not a string"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Use the XML parser to parse the response content
        return parse_role_recommendations_xml(response_content)

    except requests.exceptions.RequestException as e:
        logger.error("API request failed: %s", str(e))
        # For RequestException, we carefully check for response attributes
        response = getattr(e, "response", None)
        if response is not None:
            if hasattr(response, "status_code"):
                logger.error("Response status: %s", response.status_code)
            if hasattr(response, "text"):
                logger.error("Response body: %s...", response.text[:500])
        raise

    except (KeyError, IndexError) as e:
        error_msg = f"Failed to extract content from API response: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg) from e

    except Exception as e:
        logger.error("Unexpected error in LLM processing: %s", str(e))
        raise


def generate_personal_tagline(resume_xml: str) -> str:
    """
    Generate a personal tagline based on the job seeker's resume XML.

    Args:
        resume_xml: The XML representation of the job seeker's resume

    Returns:
        A concise personal tagline as a string

    Raises:
        ValueError: If the API key is missing or the LLM response is invalid
        requests.exceptions.RequestException: If the API request fails
        Exception: For any other processing errors
    """
    # Use settings for API key if available, fall back to env var (for compatibility)
    api_key = settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
    if not api_key:
        error_msg = "No API key found. Set OPENAI_API_KEY environment variable."
        logger.error(error_msg)
        raise ValueError(error_msg)

    # Debug XML content
    if not resume_xml:
        logger.error("Resume XML is empty or None!")
        return "Unable to generate tagline: No resume data provided"

    prompt_path = os.path.join(
        settings.BASE_DIR,
        "apps",
        "resume_processing",
        "prompts",
        "generate_personal_tagline_from_xml.prompt.md",
    )

    # Debug: Check if prompt file exists
    if not os.path.exists(prompt_path):
        logger.error("Prompt file not found at path: %s", prompt_path)
        return "Unable to generate tagline: Prompt file not found"

    try:
        structured_prompt = StructuredPrompt.from_promptdown_file(prompt_path)

        # Wrap the XML in markdown code block
        wrapped_xml = f"```xml\n{resume_xml}\n```"

        # Apply the template values with the original XML
        structured_prompt.apply_template_values(
            {
                "resume_xml": wrapped_xml,
            }
        )

        # Get messages for the API call
        messages = structured_prompt.to_chat_completion_messages()

    except Exception as e:
        logger.error("Error preparing prompt: %s", str(e))
        return f"Unable to generate tagline: Error preparing prompt: {str(e)}"

    client = OpenAI(api_key=api_key)

    # Capture the start of processing for logging
    logger.info("Sending resume XML to LLM for tagline generation")
    logger.debug("XML length: %d characters", len(resume_xml))

    # Make the API call with proper error handling
    try:
        completion = client.chat.completions.create(
            model=settings.JOBSEEKERS_TAGLINE_GENERATION_MODEL,  # Renamed setting
            messages=cast(Iterable[Any], messages),
            temperature=settings.JOBSEEKERS_TAGLINE_TEMPERATURE,  # Use settings
            max_tokens=settings.JOBSEEKERS_TAGLINE_MAX_TOKENS,  # Use settings
        )

        # Extract the content from the response
        tagline = completion.choices[0].message.content

        # Perform basic validation
        if not tagline or not isinstance(tagline, str):
            error_msg = "LLM response content is None or not a string"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Clean up the tagline - strip whitespace and ensure no quotes
        tagline = tagline.strip().strip('"').strip("'")

        logger.info("Generated tagline: %s", tagline)
        return tagline

    except requests.exceptions.RequestException as e:
        logger.error("API request failed: %s", str(e))
        # For RequestException, we carefully check for response attributes
        response = getattr(e, "response", None)
        if response is not None:
            if hasattr(response, "status_code"):
                logger.error("Response status: %s", response.status_code)
            if hasattr(response, "text"):
                logger.error("Response body: %s...", response.text[:500])
        raise

    except (KeyError, IndexError) as e:
        error_msg = f"Failed to extract content from API response: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg) from e

    except Exception as e:
        logger.error("Unexpected error in LLM processing: %s", str(e))
        raise


def generate_talent_sheet(
    job_seeker_profile: JobSeekerProfile,
    interested_roles: list[str] | None = None,
) -> TalentSheet:
    """
    Generate a talent sheet based on the job seeker's resume XML and interested roles.

    This function sends the job seeker's resume XML and their interested role selections
    to an LLM to generate a comprehensive talent sheet for recruiters.

    Args:
        job_seeker_profile: The JobSeekerProfile instance to build the talent sheet for (provides resume_xml and skills)
        interested_roles: Optional list of roles the job seeker has expressed interest in

    Returns:
        A TalentSheet object (unsaved to database)

    Raises:
        ValueError: If the API key is missing or the LLM response is invalid
        requests.exceptions.RequestException: If the API request fails
        Exception: For any other processing errors
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        error_msg = "No API key found. Set OPENAI_API_KEY environment variable."
        logger.error(error_msg)
        raise ValueError(error_msg)

    client = OpenAI(api_key=api_key)

    # Extract resume XML from the profile (required for LLM prompt)
    resume_xml = job_seeker_profile.resume_xml or ""

    if not resume_xml:
        raise ValueError("Cannot generate talent sheet: profile.resume_xml is empty")

    try:
        # Load and fill the talent sheet generation prompt
        prompt_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "prompts",
            "generate_talent_sheet_from_xml.prompt.md",
        )

        # Load the prompt using the correct method
        structured_prompt = StructuredPrompt.from_promptdown_file(prompt_path)

        # Prepare interested roles as a comma-separated string for the prompt
        interested_roles_str = ""
        if interested_roles:
            interested_roles_str = ", ".join(interested_roles)

        # Wrap the XML in markdown code block
        wrapped_xml = f"```xml\n{resume_xml}\n```"

        # Apply the template values
        structured_prompt.apply_template_values(
            {
                "resume_xml": wrapped_xml,
                "interested_roles": interested_roles_str,
            }
        )

        # Get messages for the API call
        messages = structured_prompt.to_chat_completion_messages()

        # Call the OpenAI API
        response = client.chat.completions.create(
            model=settings.JOBSEEKERS_TALENT_SHEET_MODEL,
            messages=cast(Iterable[Any], messages),
            temperature=settings.JOBSEEKERS_TALENT_SHEET_TEMPERATURE,
            timeout=60,
        )

        # Extract talent sheet XML from response
        xml_response = cast(str, response.choices[0].message.content)
        if not xml_response:
            raise ValueError("Empty response from LLM")

        # Parse the XML response into a TalentSheet object
        talent_sheet = parse_talent_sheet_xml(xml_response)

        # Copy raw skills from the JobSeekerProfile directly
        talent_sheet.skills = job_seeker_profile.skills or ""

        logger.info("Generated talent sheet successfully")

        return talent_sheet

    except requests.exceptions.RequestException as e:
        logger.error("API request failed: %s", str(e), exc_info=True)
        raise
    except ValueError as e:
        logger.error("Failed to process LLM response: %s", str(e), exc_info=True)
        raise
    except Exception as e:
        logger.error("Error generating talent sheet: %s", str(e), exc_info=True)
        raise
