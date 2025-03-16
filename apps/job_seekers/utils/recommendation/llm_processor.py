"""
LLM integration for job seeker recommendations.

This module contains functions for sending resume data to LLM services
and processing the responses to generate recommendations.
"""

import logging
import os
from typing import Any, Iterable, cast

import requests
from dotenv import load_dotenv
from openai import OpenAI
from promptdown import StructuredPrompt

# Load environment variables
load_dotenv()

# Setup logging
logger = logging.getLogger(__name__)


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
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        error_msg = "No API key found. Set OPENAI_API_KEY environment variable."
        logger.error(error_msg)
        raise ValueError(error_msg)

    # Debug XML content
    if not resume_xml:
        logger.error("Resume XML is empty or None!")
        return "Unable to generate tagline: No resume data provided"

    prompt_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
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
        resume_xml = f"```xml\n{resume_xml}\n```"

        # Apply the template values with the original XML
        structured_prompt.apply_template_values(
            {
                "resume_xml": resume_xml,
            }
        )

        # Get messages for the API call
        messages = structured_prompt.to_chat_completion_messages()
        logger.debug("Number of messages to send: %d", len(messages))

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
            model="gpt-4o-mini",
            messages=cast(Iterable[Any], messages),
            temperature=0.7,  # Slightly higher temperature for creative output
            max_tokens=50,  # Tagline should be short
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
