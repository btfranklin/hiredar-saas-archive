"""
XML parsing utilities for resume processing.

This module contains functions for parsing XML resume representations
and extracting structured data.
"""

import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Dict, List, Optional

# Setup logging
logger = logging.getLogger(__name__)


def parse_resume_xml(xml_content: str) -> Dict[str, Any]:
    """
    Parse XML resume representation into a structured dictionary.

    Args:
        xml_content: XML string representation of a resume

    Returns:
        Dictionary containing structured resume data

    Raises:
        ET.ParseError: If the XML is not well-formed
        ValueError: If the XML structure is invalid or missing required elements
        Exception: For any other parsing errors
    """
    if not xml_content:
        logger.error("Empty XML content received")
        raise ValueError("Empty XML content received")

    # First, validate the XML is well-formed by attempting to parse it
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        logger.error(f"XML parsing error: {e}")
        # Log a sample of the problematic XML for diagnosis
        content_sample = (
            xml_content[:500] + "..." if len(xml_content) > 500 else xml_content
        )
        logger.error(f"Invalid XML sample: {content_sample}")
        # Re-raise to ensure the error propagates
        raise

    # Check for required elements (basic validation)
    if root.tag != "resume":
        logger.error(f"XML root element is '{root.tag}', expected 'resume'")
        raise ValueError(
            f"Invalid XML structure: root element is '{root.tag}', expected 'resume'"
        )

    # Extract the structured data - each extraction function will now raise exceptions
    # rather than silently returning empty values
    result = {
        "skills": extract_skills(xml_content),
        "current_position": extract_most_recent_title(xml_content),
        "years_of_experience": calculate_years_experience(xml_content),
        "about_me": extract_bio(xml_content),
        "education": extract_education(xml_content),
    }

    # Warn about missing key sections
    warn_missing_sections(result)

    return result


def warn_missing_sections(result: Dict[str, Any]) -> None:
    """
    Log warnings for any missing key sections in the resume.

    Args:
        result: The parsed resume data
    """
    if not result.get("skills"):
        logger.warning("No skills were extracted from the resume")

    if not result.get("current_position"):
        logger.warning("No current position was extracted from the resume")

    if not result.get("years_of_experience"):
        logger.warning("No years of experience were calculated from the resume")


def extract_skills(xml_content: str) -> List[str]:
    """
    Extract skills from the XML resume representation.

    Args:
        xml_content: XML string representation of a resume

    Returns:
        List of skill names

    Raises:
        ET.ParseError: If the XML is not well-formed
    """
    root = ET.fromstring(xml_content)

    # Find all skill elements
    skill_elements = root.findall(".//skills/skill")
    skills = []

    for skill_elem in skill_elements:
        if skill_elem.text:
            skills.append(skill_elem.text.strip())

    return skills


def extract_most_recent_title(xml_content: str) -> Optional[str]:
    """
    Extract the most recent job title from the XML resume.

    Args:
        xml_content: XML string representation of a resume

    Returns:
        The most recent job title or None

    Raises:
        ET.ParseError: If the XML is not well-formed
    """
    root = ET.fromstring(xml_content)

    # Find all job elements
    job_elements = root.findall(".//experience/job")

    # For simplicity, assume the first job is the most recent
    # In a more robust implementation, we would parse and compare dates
    if job_elements and len(job_elements) > 0:
        title_elem = job_elements[0].find("title")
        if title_elem is not None and title_elem.text:
            return title_elem.text.strip()

    return None


def calculate_years_experience(xml_content: str) -> int:
    """
    Calculate total years of experience from the XML resume.

    This is a simplified calculation that adds up the duration of all jobs.

    Args:
        xml_content: XML string representation of a resume

    Returns:
        Total years of experience (integer)

    Raises:
        ET.ParseError: If the XML is not well-formed
    """
    root = ET.fromstring(xml_content)

    # Find all job elements
    job_elements = root.findall(".//experience/job")

    total_years = 0
    for job in job_elements:
        start_date = job.find("startDate")
        end_date = job.find("endDate")

        # Skip if we don't have both dates
        if start_date is None or start_date.text is None:
            continue

        # For current positions, use current year
        if end_date is None or not end_date.text or "present" in end_date.text.lower():
            end_year = datetime.now().year
        else:
            # Try to extract the year from the end date
            try:
                # Assume format like "2022" or "May 2022"
                end_year = int(end_date.text.strip().split()[-1])
            except (ValueError, IndexError):
                continue

        # Try to extract the year from the start date
        try:
            # Assume format like "2018" or "June 2018"
            start_year = int(start_date.text.strip().split()[-1])

            # Add the difference to our total
            duration = end_year - start_year
            if duration > 0:
                total_years += duration
        except (ValueError, IndexError):
            continue

    return total_years


def extract_bio(xml_content: str) -> Optional[str]:
    """
    Extract a personal summary/bio from the XML resume.

    Args:
        xml_content: XML string representation of a resume

    Returns:
        Personal summary as a string or None

    Raises:
        ET.ParseError: If the XML is not well-formed
    """
    root = ET.fromstring(xml_content)

    # Find the personal summary element
    summary_elem = root.find(".//personal/summary")
    if summary_elem is not None and summary_elem.text:
        return summary_elem.text.strip()

    return None


def extract_education(xml_content: str) -> List[Dict[str, Any]]:
    """
    Extract education information from the XML resume.

    Args:
        xml_content: XML string representation of a resume

    Returns:
        List of education entries as dictionaries

    Raises:
        ET.ParseError: If the XML is not well-formed
    """
    root = ET.fromstring(xml_content)

    # Find all institution elements
    institution_elements = root.findall(".//education/institution")
    education_entries = []

    for institution in institution_elements:
        entry = {}

        name_elem = institution.find("name")
        if name_elem is not None and name_elem.text:
            entry["institution"] = name_elem.text.strip()

        degree_elem = institution.find("degree")
        if degree_elem is not None and degree_elem.text:
            entry["degree"] = degree_elem.text.strip()

        field_elem = institution.find("field")
        if field_elem is not None and field_elem.text:
            entry["field"] = field_elem.text.strip()

        # Include dates if available
        start_date_elem = institution.find("startDate")
        if start_date_elem is not None and start_date_elem.text:
            entry["start_date"] = start_date_elem.text.strip()

        end_date_elem = institution.find("endDate")
        if end_date_elem is not None and end_date_elem.text:
            entry["end_date"] = end_date_elem.text.strip()

        if entry:  # Only add if we have some data
            education_entries.append(entry)

    return education_entries
