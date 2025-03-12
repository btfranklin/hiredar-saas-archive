"""
XML error reporting utilities.

This module provides functions for detailed XML error reporting and diagnostics,
centralizing error handling logic used across the resume processing pipeline.
"""

import logging
import xml.etree.ElementTree as ET
from typing import Any

# Setup logging
logger = logging.getLogger(__name__)


def get_error_position(error: ET.ParseError) -> tuple[int, int] | None:
    """
    Extract line and column position from an XML parse error.

    Args:
        error: The XML parse error

    Returns:
        Tuple of (line_number, column_number) or None if not available
    """
    try:
        return error.position
    except (AttributeError, ValueError):
        return None


def get_error_context(
    xml_content: str, line_no: int, col_no: int, context_lines: int = 2
) -> dict[str, Any]:
    """
    Get context information around an XML error.

    Args:
        xml_content: The XML content with the error
        line_no: Line number where the error occurred (1-indexed)
        col_no: Column number where the error occurred
        context_lines: Number of lines to include before and after the error

    Returns:
        Dictionary with error context information
    """
    lines = xml_content.split("\n")
    result: dict[str, Any] = {
        "error_line_no": line_no,
        "error_col_no": col_no,
        "context_lines": [],
        "error_line": "",
    }

    # Check if line number is valid
    if 0 <= line_no - 1 < len(lines):
        # Get the error line
        error_line = lines[line_no - 1]
        result["error_line"] = error_line

        # Get context lines
        start_line = max(0, line_no - 1 - context_lines)
        end_line = min(len(lines), line_no + context_lines)

        for i in range(start_line, end_line):
            context = {
                "line_no": i + 1,
                "content": lines[i],
                "is_error_line": i == line_no - 1,
            }
            result["context_lines"].append(context)

    return result


def format_error_for_console(error: ET.ParseError, xml_content: str) -> list[str]:
    """
    Format XML error details for console output.

    Args:
        error: The XML parse error
        xml_content: The XML content with the error

    Returns:
        List of formatted lines for console output
    """
    output_lines = []

    # Add error message
    output_lines.append(f"XML Error: {str(error)}")

    # Get error position
    pos = get_error_position(error)
    if not pos:
        output_lines.append("Error position not available")
        return output_lines

    line_no, col_no = pos
    context = get_error_context(xml_content, line_no, col_no)

    # Format error lines
    output_lines.append(f"Error at line {line_no}, column {col_no}:")

    for ctx in context["context_lines"]:
        line_prefix = f"{ctx['line_no']}: "
        if ctx["is_error_line"]:
            line = f"{line_prefix}{ctx['content']}"
            output_lines.append(line)

            # Add pointer to the error position
            pointer = " " * (len(line_prefix) + col_no - 1) + "^"
            output_lines.append(pointer)

            # Add explicit position marker
            position_marker = " " * (len(line_prefix) + col_no - 1) + "HERE"
            output_lines.append(position_marker)
        else:
            output_lines.append(f"{line_prefix}{ctx['content']}")

    # Add hint based on error type
    error_str = str(error).lower()
    if "invalid token" in error_str:
        output_lines.append(
            "Hint: This error often means there is an illegal character in the XML."
        )
    elif "unclosed" in error_str:
        output_lines.append("Hint: This error indicates an unclosed XML tag.")
    elif "not well-formed" in error_str:
        output_lines.append(
            "Hint: This error suggests malformed XML, like improperly nested tags or unescaped special characters."
        )

    return output_lines


def log_xml_error(error: ET.ParseError, xml_content: str) -> None:
    """
    Log detailed XML error information.

    Args:
        error: The XML parse error
        xml_content: The XML content with the error
    """
    lines = format_error_for_console(error, xml_content)
    for line in lines:
        logger.error(line)

    # Also log a sample of the problematic XML
    logger.error("XML sample: %s...", xml_content[:500])


def create_marked_xml(error: ET.ParseError, xml_content: str) -> str:
    """
    Create a version of the XML with error markers.

    Args:
        error: The XML parse error
        xml_content: The XML content with the error

    Returns:
        XML content with added error markers
    """
    pos = get_error_position(error)
    if not pos:
        return f"<!-- XML ERROR: {str(error)} (position unknown) -->\n{xml_content}"

    line_no, col_no = pos
    lines = xml_content.split("\n")

    # Add error markers if line number is valid
    if 0 <= line_no - 1 < len(lines):
        # Add an inline marker at the exact position
        error_line = lines[line_no - 1]
        if col_no <= len(error_line):
            lines[line_no - 1] = error_line[:col_no] + "❌" + error_line[col_no:]

        # Add error explanation comment
        lines.insert(
            line_no, f"<!-- ERROR: {str(error)} at line {line_no}, column {col_no} -->"
        )

    # Add XML comment with error information at the top
    lines.insert(0, f"<!-- XML PARSING ERROR: {str(error)} -->")
    lines.insert(
        1,
        "<!-- This file contains error indicators (❌) showing where parsing failed -->",
    )

    return "\n".join(lines)


def save_diagnostic_xml(
    error: ET.ParseError, xml_content: str, base_path: str, error_type: str = "parsing"
) -> str | None:
    """
    Save diagnostic XML with error markers to a file.

    Args:
        error: The XML parse error
        xml_content: The XML content with the error
        base_path: Base path to use for the filename
        error_type: Type of error (for filename)

    Returns:
        Path to the saved file or None if saving failed
    """
    try:
        # Generate a diagnostic filename
        diagnostic_path = f"{base_path}.failed_xml_{error_type}.xml"

        # Create error-marked XML
        marked_xml = create_marked_xml(error, xml_content)

        # Write to file
        with open(diagnostic_path, "w", encoding="utf-8") as f:
            f.write(marked_xml)

        logger.info("Saved diagnostic XML to %s", diagnostic_path)
        return diagnostic_path

    except Exception as e:
        logger.warning("Could not save diagnostic XML file: %s", str(e))
        return None
