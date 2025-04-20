"""
XML parsing utilities for resume processing.

This module contains functions for parsing XML resume representations
and extracting structured data.
"""

import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any

# Setup logging
logger = logging.getLogger(__name__)


def parse_resume_xml(xml_content: str) -> dict[str, Any]:
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
        logger.error("XML parsing error: %s", e)
        # Log a sample of the problematic XML for diagnosis
        content_sample = (
            xml_content[:500] + "..." if len(xml_content) > 500 else xml_content
        )
        logger.error("Invalid XML sample: %s", content_sample)
        # Re-raise to ensure the error propagates
        raise

    # Check for required elements (basic validation)
    if root.tag != "resume":
        logger.error("XML root element is '%s', expected 'resume'", root.tag)
        raise ValueError(
            f"Invalid XML structure: root element is '{root.tag}', expected 'resume'"
        )

    # Extract the structured data
    result = {
        "skills": extract_skills(xml_content),
        "most_recent_title": extract_most_recent_title(xml_content),
        "years_of_experience": calculate_years_experience(xml_content),
        "professional_summary": extract_professional_summary(xml_content),
        "education": extract_education(xml_content),
        "experience": extract_experience(xml_content),
        "personal_details": extract_personal_details(xml_content),
        "certifications": extract_certifications(xml_content),
    }

    # Warn about missing key sections
    warn_missing_sections(result)

    return result


def warn_missing_sections(result: dict[str, Any]) -> None:
    """
    Log warnings for any missing key sections in the resume.

    Args:
        result: The parsed resume data
    """
    if not result.get("skills"):
        logger.warning("No skills were extracted from the resume")

    if not result.get("most_recent_title"):
        logger.warning("No most recent title was extracted from the resume")

    if result.get("years_of_experience") is None:
        logger.warning("No years of experience were calculated from the resume")

    if not result.get("education"):
        logger.warning("No education information was extracted from the resume")

    if not result.get("experience"):
        logger.warning("No experience information was extracted from the resume")


def extract_skills(xml_content: str) -> str | None:
    """
    Extract skills from the XML resume representation and format as a string.

    Args:
        xml_content: XML string representation of a resume

    Returns:
        Pipe-separated string of skills or None if no skills found

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

    if not skills:
        return None

    # Convert the list of skills to a pipe-separated string
    return " | ".join(skills)  # Added spaces around pipe for better readability


def extract_most_recent_title(xml_content: str) -> str | None:
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


def extract_professional_summary(xml_content: str) -> str | None:
    """
    Extract a professional summary from the XML resume.

    Args:
        xml_content: XML string representation of a resume

    Returns:
        Professional summary as a string or None

    Raises:
        ET.ParseError: If the XML is not well-formed
    """
    root = ET.fromstring(xml_content)

    # First, try to find a dedicated professional summary element
    summary_elem = root.find(".//professionalSummary")
    if summary_elem is not None and summary_elem.text:
        return summary_elem.text.strip()

    # Next, try to find it within the personal section
    summary_elem = root.find(".//personal/summary")
    if summary_elem is not None and summary_elem.text:
        return summary_elem.text.strip()

    # Finally, try to find it directly in the personal section as professionalSummary
    summary_elem = root.find(".//personal/professionalSummary")
    if summary_elem is not None and summary_elem.text:
        return summary_elem.text.strip()

    return None


def extract_education(xml_content: str) -> str | None:
    """
    Extract education information from the XML resume and format as a string.

    Args:
        xml_content: XML string representation of a resume

    Returns:
        Formatted string containing education information or None if not found

    Raises:
        ET.ParseError: If the XML is not well-formed
    """
    root = ET.fromstring(xml_content)

    # Find all institution elements
    institution_elements = root.findall(".//education/institution")

    if not institution_elements:
        return None

    education_blocks = []

    for institution in institution_elements:
        entry_parts = []

        # Extract institution name
        name_elem = institution.find("name")
        if name_elem is not None and name_elem.text:
            entry_parts.append(f"Institution: {name_elem.text.strip()}")

        # Extract degree
        degree_elem = institution.find("degree")
        if degree_elem is not None and degree_elem.text:
            entry_parts.append(f"Degree: {degree_elem.text.strip()}")

        # Extract field
        field_elem = institution.find("field")
        if field_elem is not None and field_elem.text:
            entry_parts.append(f"Field: {field_elem.text.strip()}")

        # Include dates if available - using the new format
        start_date_elem = institution.find("startDate")
        end_date_elem = institution.find("endDate")

        start_date = (
            start_date_elem.text.strip()
            if start_date_elem is not None and start_date_elem.text
            else None
        )
        end_date = (
            end_date_elem.text.strip()
            if end_date_elem is not None and end_date_elem.text
            else None
        )

        if start_date and end_date:
            entry_parts.append(f"Dates: {start_date} - {end_date}")
        elif start_date:
            entry_parts.append(f"Start Date: {start_date}")
        elif end_date:
            entry_parts.append(f"End Date: {end_date}")

        if entry_parts:  # Only add if we have some data
            education_blocks.append("\n".join(entry_parts))

    if not education_blocks:
        return None

    return "\n\n".join(education_blocks)


def extract_experience(xml_content: str) -> str | None:
    """
    Extract all work experience as a formatted text block from the XML resume.

    Args:
        xml_content: XML string representation of a resume

    Returns:
        Formatted string containing work experience information or None if not found

    Raises:
        ET.ParseError: If the XML is not well-formed
    """
    root = ET.fromstring(xml_content)

    # Find the experience section
    experience_elem = root.find(".//experience")
    if experience_elem is None:
        return None

    # Find all job elements
    job_elements = experience_elem.findall("job")
    if not job_elements:
        return None

    # Build a formatted text representation of the experience
    experience_text = []

    for job in job_elements:
        job_parts = []

        # Extract job title
        title_elem = job.find("title")
        if title_elem is not None and title_elem.text:
            job_parts.append(f"Position: {title_elem.text.strip()}")

        # Extract company
        company_elem = job.find("company")
        if company_elem is not None and company_elem.text:
            job_parts.append(f"Company: {company_elem.text.strip()}")

        # Extract dates - using the new format
        start_date = job.find("startDate")
        end_date = job.find("endDate")

        start_date_text = (
            start_date.text.strip()
            if start_date is not None and start_date.text
            else None
        )
        end_date_text = (
            end_date.text.strip() if end_date is not None and end_date.text else None
        )

        # Format dates according to the new requirements
        if start_date_text and end_date_text:
            if end_date_text.lower() == "present":
                job_parts.append(f"Dates: {start_date_text} - Present")
            else:
                job_parts.append(f"Dates: {start_date_text} - {end_date_text}")
        elif start_date_text:
            job_parts.append(f"Start Date: {start_date_text}")
        elif end_date_text:
            job_parts.append(f"End Date: {end_date_text}")

        # Extract description
        description_elem = job.find("description")
        if description_elem is not None and description_elem.text:
            job_parts.append(f"Description: {description_elem.text.strip()}")

        # Add this job entry to the full experience text
        if job_parts:
            experience_text.append("\n".join(job_parts))

    if not experience_text:
        return None

    return "\n\n".join(experience_text)


def extract_personal_details(xml_content: str) -> dict[str, str | None]:
    """
    Extract personal details from the XML resume.

    Args:
        xml_content: XML string representation of a resume

    Returns:
        Dictionary containing name, email, phone, and location

    Raises:
        ET.ParseError: If the XML is not well-formed
    """
    root = ET.fromstring(xml_content)

    # Initialize the results dictionary with None values
    result: dict[str, str | None] = {
        "name": None,
        "email": None,
        "phone": None,
        "location": None,
    }

    # Find the personal section
    personal_elem = root.find(".//personal")
    if personal_elem is None:
        return result

    # Extract name
    name_elem = personal_elem.find("name")
    if name_elem is not None and name_elem.text:
        result["name"] = name_elem.text.strip()

    # Extract email
    email_elem = personal_elem.find("email")
    if email_elem is not None and email_elem.text:
        result["email"] = email_elem.text.strip()

    # Extract phone
    phone_elem = personal_elem.find("phone")
    if phone_elem is not None and phone_elem.text:
        result["phone"] = phone_elem.text.strip()

    # Extract location
    location_elem = personal_elem.find("location")
    if location_elem is not None and location_elem.text:
        result["location"] = location_elem.text.strip()

    return result


def extract_certifications(xml_content: str) -> str | None:
    """
    Extract certifications from the XML resume and format as a string.

    Args:
        xml_content: XML string representation of a resume

    Returns:
        Formatted string containing certification information or None if not found

    Raises:
        ET.ParseError: If the XML is not well-formed
    """
    root = ET.fromstring(xml_content)

    # Find all certification elements
    certification_elements = root.findall(".//certifications/certification")

    if not certification_elements:
        return None

    certification_blocks = []

    for cert in certification_elements:
        cert_parts = []

        # Extract certification name
        name_elem = cert.find("name")
        if name_elem is not None and name_elem.text:
            cert_parts.append(f"Certification: {name_elem.text.strip()}")

        # Extract issuer
        issuer_elem = cert.find("issuer")
        if issuer_elem is not None and issuer_elem.text:
            cert_parts.append(f"Issuer: {issuer_elem.text.strip()}")

        # Extract date
        date_elem = cert.find("date")
        if date_elem is not None and date_elem.text:
            cert_parts.append(f"Date: {date_elem.text.strip()}")

        # Check for start/end dates if available (some XML formats might use these)
        start_date_elem = cert.find("startDate")
        end_date_elem = cert.find("endDate")

        start_date = (
            start_date_elem.text.strip()
            if start_date_elem is not None and start_date_elem.text
            else None
        )
        end_date = (
            end_date_elem.text.strip()
            if end_date_elem is not None and end_date_elem.text
            else None
        )

        # Only add date information if we haven't already found a single date
        if (start_date or end_date) and not date_elem:
            if start_date and end_date:
                cert_parts.append(f"Dates: {start_date} - {end_date}")
            elif start_date:
                cert_parts.append(f"Date: {start_date}")
            elif end_date:
                cert_parts.append(f"Date: {end_date}")

        # Only add if we have at least some parts
        if cert_parts:
            certification_blocks.append("\n".join(cert_parts))

    if not certification_blocks:
        return None

    return "\n\n".join(certification_blocks)
