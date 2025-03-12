"""
LLM integration for resume processing.

This module contains functions for sending resume text to LLM services
and processing the responses.
"""

import logging
import os
import xml.etree.ElementTree as ET
from typing import Any, Iterable, cast

import requests
from dotenv import load_dotenv
from openai import OpenAI
from promptdown import StructuredPrompt

from apps.job_seekers.utils.resume_processing.xml_error_reporting import log_xml_error

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
        A structured XML representation of the resume

    Raises:
        ValueError: If the API key is missing or the LLM response is invalid
        ET.ParseError: If the generated XML is not well-formed
        requests.exceptions.RequestException: If the API request fails
        Exception: For any other processing errors
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        error_msg = "No API key found. Set OPENAI_API_KEY environment variable."
        logger.error(error_msg)
        raise ValueError(error_msg)

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
    messages = structured_prompt.to_chat_completion_messages()

    client = OpenAI(api_key=api_key)

    # Capture the start of processing for logging
    logger.info("Sending resume text to LLM for XML conversion")
    logger.debug("Resume text length: %d characters", len(resume_text))

    # Make the API call with proper error handling
    try:
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=cast(Iterable[Any], messages),
            temperature=0.7,  # Lower temperature for more deterministic output
        )

        # Extract the XML content from the response
        xml_content = completion.choices[0].message.content

        # Perform basic validation
        if not xml_content or not isinstance(xml_content, str):
            error_msg = "LLM response content is None or not a string"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Apply sanitization to fix common issues
        xml_content, was_sanitized = sanitize_xml_if_needed(xml_content)
        if was_sanitized:
            logger.info("Applied XML sanitization to fix potential issues")

        # Check for basic XML structure - log but don't immediately fail
        if not xml_content.strip().startswith("<resume>"):
            logger.warning(
                "LLM response does not start with <resume> tag even after sanitization"
            )
            # Log a snippet of what we received for diagnostic purposes
            logger.warning("Response begins with: %s...", xml_content[:100])

        if not xml_content.strip().endswith("</resume>"):
            logger.warning(
                "LLM response does not end with </resume> tag even after sanitization"
            )
            # Log a snippet of what we received for diagnostic purposes
            logger.warning(
                "Response ends with: %s",
                xml_content[-100:] if len(xml_content) > 100 else xml_content,
            )

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


def sanitize_xml_if_needed(xml_content: str) -> tuple[str, bool]:
    """
    Apply basic XML sanitization if necessary.

    Attempts to fix common issues in the XML content generated by the LLM.

    Args:
        xml_content: The XML content to sanitize

    Returns:
        Tuple of (sanitized_xml, was_modified)
    """
    original_xml = xml_content
    was_modified = False

    # Ensure XML has a root element
    if not xml_content.strip().startswith("<resume>"):
        xml_content = f"<resume>{xml_content.strip()}</resume>"
        was_modified = True

    # Ensure XML ends with the closing root tag
    if not xml_content.strip().endswith("</resume>"):
        # If we already have a closing tag, don't add another one
        if "</resume>" not in xml_content:
            xml_content = f"{xml_content.strip()}</resume>"
            was_modified = True

    # Sanitize common problematic characters
    replacements = [
        # Common XML-invalid control characters
        ("\x0b", ""),
        ("\x0c", ""),
        ("\x1b", ""),
        # Common XML entities
        ("&nbsp;", " "),
        ("&ndash;", "-"),
        ("&mdash;", "-"),
        ("&quot;", '"'),
        # Ensure proper escaping of ampersands
        ("& ", "&amp; "),
    ]

    for old, new in replacements:
        if old in xml_content:
            xml_content = xml_content.replace(old, new)
            was_modified = True

    # If we modified the XML, log it
    if was_modified:
        logger.info("Applied XML sanitization")
        if len(original_xml) > 100:
            logger.debug("Original XML sample: %s...", original_xml[:100])
        if len(xml_content) > 100:
            logger.debug("Sanitized XML sample: %s...", xml_content[:100])

    return xml_content, was_modified
