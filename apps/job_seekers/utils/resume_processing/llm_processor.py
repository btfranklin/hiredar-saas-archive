"""
LLM integration for resume processing.

This module contains functions for sending resume text to LLM services
and processing the responses.
"""

import logging
import os
import xml.etree.ElementTree as ET
from typing import Any, Iterable, Optional, cast

import requests
from dotenv import load_dotenv
from openai import OpenAI
from promptdown import StructuredPrompt

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
    logger.debug(f"Resume text length: {len(resume_text)} characters")

    # Make the API call with proper error handling
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=cast(Iterable[Any], messages),
            temperature=0.2,  # Lower temperature for more deterministic output
        )

        # Extract the XML content from the response
        xml_content = completion.choices[0].message.content

        # Perform basic validation
        if not xml_content or not isinstance(xml_content, str):
            error_msg = "LLM response content is None or not a string"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Check for basic XML structure - log but don't immediately fail
        if not xml_content.strip().startswith("<resume>"):
            logger.warning("LLM response does not start with <resume> tag")
            # Log a snippet of what we received for diagnostic purposes
            logger.warning(f"Response begins with: {xml_content[:100]}...")

        if not xml_content.strip().endswith("</resume>"):
            logger.warning("LLM response does not end with </resume> tag")
            # Log a snippet of what we received for diagnostic purposes
            logger.warning(
                f"Response ends with: {xml_content[-100:] if len(xml_content) > 100 else xml_content}"
            )

        # Validate the XML is well-formed by attempting to parse it
        try:
            ET.fromstring(xml_content)
            logger.info("XML validation successful")
        except ET.ParseError as e:
            logger.error(f"LLM generated invalid XML: {e}")
            # Log a sample of the problematic XML
            logger.error(f"Invalid XML sample: {xml_content[:500]}...")
            # Re-raise to ensure the error propagates
            raise

        return xml_content

    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {str(e)}")
        if hasattr(e, "response") and e.response is not None:
            logger.error(f"Response status: {e.response.status_code}")
            logger.error(f"Response body: {e.response.text[:500]}...")
        raise

    except (KeyError, IndexError) as e:
        error_msg = f"Failed to extract content from API response: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg)

    except Exception as e:
        logger.error(f"Unexpected error in LLM processing: {str(e)}")
        raise
