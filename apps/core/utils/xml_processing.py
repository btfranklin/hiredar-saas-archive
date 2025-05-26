"""
Common XML processing utilities.

This module provides shared XML sanitization and error handling utilities
used across the application for processing LLM responses.
"""

import logging
import re
import xml.etree.ElementTree as ET

# Setup logging
logger = logging.getLogger(__name__)


def sanitize_xml_response(xml_content: str, expected_root: str | None = None) -> str:
    """
    Sanitize XML content from LLM responses to ensure it is well-formed.

    This function performs several sanitization steps on XML content:
    1. Removes Markdown code block syntax if present
    2. Ensures the XML has the expected root element (if specified)
    3. Sanitizes problematic characters for XML parsing

    Args:
        xml_content: The XML content to sanitize
        expected_root: Optional expected root element name

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

    # Ensure XML has expected root element if specified
    if expected_root:
        if not xml_content.strip().startswith(f"<{expected_root}>"):
            xml_content = f"<{expected_root}>{xml_content.strip()}</{expected_root}>"
            logger.debug("Sanitization: Added missing root <%s> element", expected_root)

        # Ensure XML ends with the closing root tag
        if not xml_content.strip().endswith(f"</{expected_root}>"):
            # If we already have a closing tag, don't add another one
            if f"</{expected_root}>" not in xml_content:
                xml_content = f"{xml_content.strip()}</{expected_root}>"
                logger.debug(
                    "Sanitization: Added missing closing </%s> tag", expected_root
                )

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


def parse_llm_xml_response(
    response_content: str,
    expected_elements: list[str] | None = None,
    expected_root: str | None = None,
) -> ET.Element:
    """
    Parse XML response from LLM with comprehensive error handling.

    Args:
        response_content: Raw response content from LLM
        expected_elements: List of required element names to validate
        expected_root: Expected root element name for validation

    Returns:
        Parsed XML root element

    Raises:
        ValueError: If response is empty or missing required elements
        ET.ParseError: If XML is malformed after sanitization
    """
    if not response_content:
        raise ValueError("Empty response from LLM")

    # Strip Markdown code fences if present
    cleaned_content = response_content.strip()
    fence_match = re.search(r"```(?:xml)?\s*(.*?)\s*```", cleaned_content, flags=re.S)
    if fence_match:
        xml_to_parse = fence_match.group(1)
    else:
        xml_to_parse = cleaned_content

    # Apply sanitization
    xml_to_parse = sanitize_xml_response(xml_to_parse, expected_root)

    # Parse the XML
    try:
        root = ET.fromstring(xml_to_parse)
    except ET.ParseError as e:
        # Import here to avoid circular imports
        from apps.resume_processing.utils.xml_error_reporting import log_xml_error

        log_xml_error(e, xml_to_parse)

        # Try fallback parsing for common malformed XML patterns
        try:
            root = _fallback_xml_parse(xml_to_parse, expected_root)
            logger.warning("Used fallback XML parsing due to malformed structure")
        except Exception:
            # If fallback also fails, re-raise the original error
            raise e

    # Validate expected elements if specified
    if expected_elements:
        missing_elements = []
        for element_name in expected_elements:
            if root.find(element_name) is None:
                missing_elements.append(element_name)

        if missing_elements:
            raise ValueError(
                f"Missing required elements in LLM response: {', '.join(missing_elements)}"
            )

    return root


def _fallback_xml_parse(
    xml_content: str, expected_root: str | None = None
) -> ET.Element:
    """
    Fallback XML parsing for malformed XML using regex extraction.

    This attempts to extract content from common malformed XML patterns
    and reconstruct valid XML.

    Args:
        xml_content: The malformed XML content
        expected_root: Expected root element name

    Returns:
        Reconstructed XML root element

    Raises:
        ValueError: If content cannot be extracted
    """
    # Try to extract summary and analysis using regex
    summary_match = re.search(r"<summary[^>]*>(.*?)</summary>", xml_content, re.S)
    analysis_match = re.search(r"<analysis[^>]*>(.*?)</analysis>", xml_content, re.S)

    if not summary_match or not analysis_match:
        raise ValueError("Could not extract summary or analysis from malformed XML")

    summary_text = summary_match.group(1).strip()
    analysis_text = analysis_match.group(1).strip()

    # Clean up any nested XML tags in the content
    summary_text = re.sub(r"<[^>]+>", "", summary_text)
    analysis_text = re.sub(r"<[^>]+>", "", analysis_text)

    # Escape XML entities
    summary_text = (
        summary_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )
    analysis_text = (
        analysis_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )

    # Reconstruct valid XML
    root_name = expected_root or "match_analysis"
    reconstructed_xml = f"""<{root_name}>
  <summary>{summary_text}</summary>
  <analysis>{analysis_text}</analysis>
</{root_name}>"""

    return ET.fromstring(reconstructed_xml)


def extract_element_text(root: ET.Element, element_name: str, default: str = "") -> str:
    """
    Safely extract text content from an XML element.

    Args:
        root: Root XML element to search in
        element_name: Name of the element to find
        default: Default value if element not found or empty

    Returns:
        Text content of the element or default value
    """
    element = root.find(element_name)
    if element is not None and element.text:
        return element.text.strip()
    return default
