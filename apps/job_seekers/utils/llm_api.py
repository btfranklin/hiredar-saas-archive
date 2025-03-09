"""
Utilities for interacting with LLM APIs.

This module contains functions for sending text to LLM services
and processing the responses.
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


def convert_text_resume_to_xml(resume_text: str) -> str | None:
    """
    Convert plain resume text into a structured XML representation using an LLM.

    Args:
        resume_text: The plain text extracted from a resume PDF

    Returns:
        A structured XML representation of the resume, or None if processing fails
    """

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("No API key found. Set OPENAI_API_KEY environment variable.")
        return None

    prompt_path = os.path.join(
        os.path.dirname(__file__), "prompts", "convert_resume_to_xml.prompt.md"
    )
    structured_prompt = StructuredPrompt.from_promptdown_file(prompt_path)
    structured_prompt.apply_template_values(
        {
            "resume_text": resume_text,
        }
    )
    messages = structured_prompt.to_chat_completion_messages()

    client = OpenAI(api_key=api_key)
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=cast(Iterable[Any], messages),
            temperature=0.2,  # Lower temperature for more deterministic output
        )

        # Extract the XML content from the response
        xml_content = completion.choices[0].message.content
        if xml_content and isinstance(xml_content, str):
            # Basic validation that it's XML (starts with <resume> and ends with </resume>)
            if xml_content.startswith("<resume>") and xml_content.endswith("</resume>"):
                return xml_content

            logger.error("LLM response doesn't look like valid XML")
            print(xml_content)
            return None

        logger.error("LLM response content is None or not a string")
        return None

    except requests.exceptions.RequestException as e:
        logger.error("API request failed: %s", str(e))
        return None
    except (KeyError, IndexError) as e:
        logger.error("Failed to extract content from API response: %s", str(e))
        return None
    except Exception as e:
        logger.error("Unexpected error in LLM processing: %s", str(e))
        return None
