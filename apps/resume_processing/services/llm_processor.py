"""
LLM integration for resume processing.

This module contains functions for sending resume text to LLM services
and processing the responses.
"""

import logging
import os
import xml.etree.ElementTree as ET
from typing import Any

import requests
from django.conf import settings
from dotenv import load_dotenv
from promptdown import StructuredPrompt

from apps.resume_processing.services.xml_error_reporting import log_xml_error
from hiredar.llm import get_llm_response
from hiredar.llm.xml_utils import sanitize_xml_response

# Load environment variables
load_dotenv()

# Setup logging
logger = logging.getLogger(__name__)


def convert_text_to_xml(resume_text: str) -> str:
    """
    Convert plain resume text into a structured XML representation using an LLM.

    Args:
        resume_text: The plain text extracted from a resume PDF

    Returns:
        A structured XML representation of the resume, as a string

    Raises:
        ValueError: If the API key is missing or the LLM response is invalid
        ET.ParseError: If the generated XML is not well-formed
        requests.exceptions.RequestException: If the API request fails
        Exception: For any other processing errors
    """
    prompt_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "prompts",
        "convert_resume_to_xml.prompt.md",
    )
    structured_prompt = StructuredPrompt.from_promptdown_file(prompt_path)
    structured_prompt.apply_template_values(
        {
            "resume_text": resume_text,
        }
    )
    response_input = structured_prompt.to_responses_input()

    # Call OpenAI via shared wrapper
    logger.info("Sending resume text to LLM for XML conversion")
    logger.debug("Resume text length: %d characters", len(resume_text))

    try:
        xml_content = get_llm_response(
            response_input=response_input,
            model=settings.CANDIDATE_RESUME_PROCESSING_MODEL,
            reasoning_effort=settings.CANDIDATE_RESUME_PROCESSING_REASONING_EFFORT,
        )

        # Perform basic validation
        if not xml_content or not isinstance(xml_content, str):
            error_msg = "LLM response content is None or not a string"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Apply sanitization to fix common issues
        xml_content = sanitize_xml_response(xml_content, expected_root="resume")

        # Store a reference to the XML content before attempting to validate it
        # This ensures it's available to the caller even if validation fails
        result_xml = xml_content

        # Validate the XML is well-formed by attempting to parse it
        try:
            ET.fromstring(xml_content)
            logger.info("XML validation successful")
        except ET.ParseError as e:
            # Use the centralized error reporting module
            log_xml_error(e, xml_content)
            # Re-raise to ensure the error propagates, but ensure the XML content is available for diagnostics
            raise

        return result_xml

    except requests.exceptions.RequestException as e:
        logger.error("API request failed: %s", str(e))
        # For RequestException, we need to carefully check for response attributes
        # since they might not exist or might be None
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
