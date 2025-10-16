"""
Shared XML utility helpers for sanitising and parsing LLM responses.
"""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


def sanitize_xml_response(xml_content: str, expected_root: str | None = None) -> str:
    """Clean up code-fenced and malformed XML so it can be parsed safely."""

    # Remove Markdown triple-backtick fences
    if xml_content.strip().startswith("```"):
        first_line_end = xml_content.find("\n")
        if first_line_end != -1:
            opening_fence = xml_content[:first_line_end].strip()
            closing_index = xml_content.rfind("```")
            if closing_index > len(opening_fence):
                xml_content = xml_content[first_line_end + 1 : closing_index].strip()
                logger.debug("Sanitization: Removed Markdown code block syntax")

    # Ensure expected root tag
    if expected_root:
        if not xml_content.strip().startswith(f"<{expected_root}>"):
            xml_content = f"<{expected_root}>{xml_content.strip()}</{expected_root}>"
            logger.debug("Sanitization: Added missing root <%s> element", expected_root)
        if (
            not xml_content.strip().endswith(f"</{expected_root}>")
            and f"</{expected_root}>" not in xml_content
        ):
            xml_content = f"{xml_content.strip()}</{expected_root}>"
            logger.debug("Sanitization: Added missing closing </%s> tag", expected_root)

    # Replace problematic characters / entities
    replacements = [
        ("\x0b", ""),
        ("\x0c", ""),
        ("\x1b", ""),
        ("&nbsp;", " "),
        ("&ndash;", "-"),
        ("&mdash;", "-"),
        ("&quot;", '"'),
        ("& ", "&amp; "),
    ]
    for old, new in replacements:
        if old in xml_content:
            count = xml_content.count(old)
            xml_content = xml_content.replace(old, new)
            logger.debug(
                "Sanitization: Replaced %s with %s (%d occurrences)",
                repr(old),
                repr(new),
                count,
            )

    # Escape lone ampersands not part of an entity
    pattern = r"&(?!amp;|quot;|lt;|gt;|apos;|#\d+;|#x[0-9a-fA-F]+;)"
    matches = re.findall(pattern, xml_content)
    if matches:
        xml_content = re.sub(pattern, "&amp;", xml_content)
        logger.debug("Sanitization: Escaped %d standalone ampersands", len(matches))

    return xml_content


def safe_parse(xml_content: str, expected_root: str | None = None) -> ET.Element:
    """Parse XML after sanitisation, raising detailed errors on failure."""

    sanitized = sanitize_xml_response(xml_content, expected_root)
    try:
        return ET.fromstring(sanitized)
    except ET.ParseError as exc:
        logger.error("XML parse error: %s", str(exc), exc_info=True)
        raise


def element_to_dict(element: ET.Element) -> dict[str, object]:
    """Convert an ElementTree element into a nested dict for easier inspection."""

    result: dict[str, object] = {}

    if element.text and element.text.strip():
        result["_text"] = element.text.strip()

    for child in element:
        result[child.tag] = element_to_dict(child)

    return result


def parse_llm_xml_response(
    response_content: str,
    expected_elements: list[str] | None = None,
    expected_root: str | None = None,
) -> ET.Element:
    """Parse XML response from LLM output with sanitisation and validation."""

    if not response_content:
        raise ValueError("Empty response from LLM")

    # Strip Markdown fences if present
    cleaned = response_content.strip()
    fence_match = re.search(r"```(?:xml)?\s*(.*?)\s*```", cleaned, flags=re.S)
    xml_to_parse = fence_match.group(1) if fence_match else cleaned

    xml_to_parse = sanitize_xml_response(xml_to_parse, expected_root)

    try:
        root = ET.fromstring(xml_to_parse)
    except ET.ParseError as exc:
        # Import lazily to avoid heavy dependency / cycles
        try:
            from apps.candidates.services.resume_processing.xml_error_reporting import (  # type: ignore
                log_xml_error,
            )
        except ImportError:
            log_xml_error = None  # fallback

        if log_xml_error:
            log_xml_error(exc, xml_to_parse)  # type: ignore[arg-type]

        # Attempt fallback parse
        try:
            root = _fallback_xml_parse(xml_to_parse, expected_root)
            logger.warning("Used fallback XML parse for malformed structure")
        except Exception:
            raise

    # Validate required elements
    if expected_elements:
        missing = [el for el in expected_elements if root.find(el) is None]
        if missing:
            raise ValueError(f"Missing required elements: {', '.join(missing)}")

    return root


def _fallback_xml_parse(
    xml_content: str, expected_root: str | None = None
) -> ET.Element:
    """Attempt to reconstruct minimal valid XML when original is malformed."""

    summary_match = re.search(r"<summary[^>]*>(.*?)</summary>", xml_content, re.S)
    analysis_match = re.search(r"<analysis[^>]*>(.*?)</analysis>", xml_content, re.S)

    if not summary_match or not analysis_match:
        raise ValueError("Could not extract summary or analysis from malformed XML")

    def _clean(text: str) -> str:
        text = re.sub(r"<[^>]+>", "", text)
        return (
            text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").strip()
        )

    summary_text = _clean(summary_match.group(1))
    analysis_text = _clean(analysis_match.group(1))

    root_name = expected_root or "match_analysis"
    reconstructed = f"<{root_name}>\n  <summary>{summary_text}</summary>\n  <analysis>{analysis_text}</analysis>\n</{root_name}>"

    return ET.fromstring(reconstructed)


def extract_element_text(root: ET.Element, element_name: str, default: str = "") -> str:
    """Safely extract text from an XML element, returning default if absent."""

    element = root.find(element_name)
    if element is not None and element.text:
        return element.text.strip()
    return default
