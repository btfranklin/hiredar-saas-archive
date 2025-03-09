"""
Resume parsing utilities.

This module contains functions for extracting and processing resume data.
"""

import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any

import pdfplumber

from apps.job_seekers.models import JobSeekerProfile

# Setup logging
logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_path: str) -> str | None:
    """
    Extract text content from a PDF file.

    Args:
        file_path: Path to the PDF file

    Returns:
        The extracted text content or None if extraction fails
    """
    try:
        text_content = []

        with pdfplumber.open(file_path) as pdf:
            # Extract text from each page
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_content.append(text)

        # Join all the text with newlines
        return "\n".join(text_content)

    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        return None


def extract_skills_from_xml(xml_content: str) -> list[str]:
    """
    Extract skills from the XML resume representation.

    Args:
        xml_content: XML string representation of a resume

    Returns:
        List of skill names
    """
    skills = []
    try:
        root = ET.fromstring(xml_content)

        # Find all skill elements
        skill_elements = root.findall(".//skills/skill")
        for skill_elem in skill_elements:
            if skill_elem.text:
                skills.append(skill_elem.text.strip())

        return skills

    except Exception as e:
        logger.error(f"Error extracting skills from XML: {str(e)}")
        return []


def extract_most_recent_title(xml_content: str) -> str | None:
    """
    Extract the most recent job title from the XML resume.

    Args:
        xml_content: XML string representation of a resume

    Returns:
        The most recent job title or None
    """
    try:
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

    except Exception as e:
        logger.error(f"Error extracting job title from XML: {str(e)}")
        return None


def calculate_years_experience(xml_content: str) -> int:
    """
    Calculate total years of experience from the XML resume.

    This is a simplified calculation that adds up the duration of all jobs.

    Args:
        xml_content: XML string representation of a resume

    Returns:
        Total years of experience (integer)
    """
    try:
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
            if (
                end_date is None
                or not end_date.text
                or "present" in end_date.text.lower()
            ):
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

    except Exception as e:
        logger.error(f"Error calculating years of experience: {str(e)}")
        return 0


def extract_bio(xml_content: str) -> str | None:
    """
    Extract a personal summary/bio from the XML resume.

    Args:
        xml_content: XML string representation of a resume

    Returns:
        Personal summary as a string or None
    """
    try:
        root = ET.fromstring(xml_content)

        # Find the personal summary element
        summary_elem = root.find(".//personal/summary")
        if summary_elem is not None and summary_elem.text:
            return summary_elem.text.strip()

        return None

    except Exception as e:
        logger.error(f"Error extracting bio from XML: {str(e)}")
        return None


def extract_education(xml_content: str) -> list[dict[str, Any]]:
    """
    Extract education information from the XML resume.

    Args:
        xml_content: XML string representation of a resume

    Returns:
        List of education entries as dictionaries
    """
    education_entries = []
    try:
        root = ET.fromstring(xml_content)

        # Find all institution elements
        institution_elements = root.findall(".//education/institution")

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

    except Exception as e:
        logger.error(f"Error extracting education from XML: {str(e)}")
        return []


def update_profile_from_xml(profile: JobSeekerProfile, xml_content: str) -> bool:
    """
    Update a JobSeekerProfile with information extracted from XML resume.

    Args:
        profile: The JobSeekerProfile instance to update
        xml_content: XML string representation of a resume

    Returns:
        Boolean indicating success or failure
    """
    try:
        # Extract and update skills
        skills = extract_skills_from_xml(xml_content)
        if skills:
            profile.skills = ", ".join(skills)

        # Extract and update current position
        current_title = extract_most_recent_title(xml_content)
        if current_title:
            profile.current_position = current_title

        # Calculate and update years of experience
        years_exp = calculate_years_experience(xml_content)
        if years_exp > 0:
            profile.years_of_experience = years_exp

        # Extract and update bio/about me
        bio = extract_bio(xml_content)
        if bio:
            profile.about_me = bio

        # Store the full XML representation
        profile.resume_xml = xml_content

        # Save all changes
        profile.save()

        return True

    except Exception as e:
        logger.error(f"Error updating profile from XML: {str(e)}")
        return False
