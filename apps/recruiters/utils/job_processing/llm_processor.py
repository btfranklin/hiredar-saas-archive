"""
LLM processing utilities for job descriptions.

This module contains functions for using Large Language Models (LLMs)
to convert job description text into structured XML format.
"""

import logging
import os
import re
import xml.etree.ElementTree as ET
from typing import Any, Iterable, cast

import requests
from django.conf import settings  # Import Django settings
from dotenv import load_dotenv
from openai import OpenAI
from promptdown import StructuredPrompt

# Load environment variables
load_dotenv()

# Setup logging
logger = logging.getLogger(__name__)


def convert_text_to_xml(job_title: str, job_description: str) -> str:
    """
    Convert job description text to structured XML using LLM.

    Args:
        job_title: The title of the job
        job_description: The full text description of the job

    Returns:
        XML string representation of the job

    Raises:
        ValueError: If the API key is missing or the LLM response is invalid
        ET.ParseError: If the generated XML is not well-formed
        requests.exceptions.RequestException: If the API request fails
        Exception: For any other processing errors
    """
    # Use settings for API key if available, fall back to env var (for compatibility)
    api_key = settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
    if not api_key:
        error_msg = "No API key found. Set OPENAI_API_KEY environment variable."
        logger.error(error_msg)
        raise ValueError(error_msg)

    prompt_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "prompts",
        "convert_job_description_to_xml.prompt.md",
    )
    structured_prompt = StructuredPrompt.from_promptdown_file(prompt_path)
    structured_prompt.apply_template_values(
        {
            "job_title": job_title,
            "job_description": job_description,
        }
    )
    messages = structured_prompt.to_chat_completion_messages()

    client = OpenAI(api_key=api_key)

    # Capture the start of processing for logging
    logger.info("Sending job description to LLM for XML conversion")
    logger.debug("Job title: %s", job_title)
    logger.debug("Job description length: %d characters", len(job_description))

    # Make the API call with proper error handling
    try:
        completion = client.chat.completions.create(
            model=settings.RECRUITERS_JOB_PROCESSING_MODEL,
            messages=cast(Iterable[Any], messages),
            temperature=settings.RECRUITERS_JOB_PROCESSING_TEMPERATURE,  # Use settings
        )

        # Extract the XML content from the response
        xml_content = completion.choices[0].message.content

        # Perform basic validation
        if not xml_content or not isinstance(xml_content, str):
            error_msg = "LLM response content is None or not a string"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Apply sanitization to fix common issues
        xml_content = sanitize_xml(xml_content)

        # Store a reference to the XML content before attempting to validate it
        # This ensures it's available to the caller even if validation fails
        result_xml = xml_content

        # Validate the XML is well-formed by attempting to parse it
        try:
            ET.fromstring(xml_content)
            logger.info("XML validation successful")
        except ET.ParseError as e:
            logger.error("XML ParseError: %s", str(e))
            logger.error(
                "Problem XML: %s",
                xml_content[:500] + "..." if len(xml_content) > 500 else xml_content,
            )
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


def sanitize_xml(xml_content: str) -> str:
    """Sanitize XML content if needed to ensure it is well-formed.

    This function performs several sanitization steps on XML content:
    1. Removes Markdown code block syntax if present
    2. Ensures the XML has a root <job> element
    3. Ensures the XML ends with the closing </job> tag
    4. Sanitizes problematic characters for XML parsing

    Args:
        xml_content: The XML content to sanitize

    Returns:
        The sanitized XML content, as a string
    """
    # Handle Markdown code blocks
    if xml_content.strip().startswith("```"):
        # Find the opening code fence
        first_line_end = xml_content.find("\n")
        if first_line_end != -1:
            # This will capture ```xml, ```html, etc.
            opening_fence = xml_content[:first_line_end].strip()

            # Find the closing code fence
            closing_index = xml_content.rfind("```")
            if closing_index > len(
                opening_fence
            ):  # Ensure we're not finding the opening fence
                # Remove both the opening and closing fences
                xml_content = xml_content[first_line_end + 1 : closing_index].strip()
                logger.debug("Sanitization: Removed Markdown code block syntax")

    # Ensure XML has a root element
    if not xml_content.strip().startswith("<job>"):
        xml_content = f"<job>{xml_content.strip()}</job>"
        logger.debug("Sanitization: Added missing root <job> element")

    # Ensure XML ends with the closing root tag
    if not xml_content.strip().endswith("</job>"):
        # If we already have a closing tag, don't add another one
        if "</job>" not in xml_content:
            xml_content = f"{xml_content.strip()}</job>"
            logger.debug("Sanitization: Added missing closing </job> tag")

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
            count = xml_content.count(old)
            xml_content = xml_content.replace(old, new)
            # Use repr() to safely show control characters
            logger.debug(
                "Sanitization: Replaced %s with %s (%d occurrences)",
                repr(old),
                repr(new),
                count,
            )

    # Handle ampersands in all contexts (not just followed by space)
    # We need to be careful not to double-escape already escaped ampersands
    # This pattern matches & that isn't part of an entity like &amp; or &quot;
    pattern = r"&(?!amp;|quot;|lt;|gt;|apos;|#\d+;|#x[0-9a-fA-F]+;)"
    matches = re.findall(pattern, xml_content)
    if matches:
        xml_content = re.sub(pattern, "&amp;", xml_content)
        logger.debug("Sanitization: Escaped %d standalone ampersands", len(matches))

    return xml_content
