"""
XML parsing utilities for job openings.

This module contains functions for parsing XML representations of job openings
and creating JobOpening models from that structured data.
"""

import logging
import re
import xml.etree.ElementTree as ET

from apps.recruiters.models import JobOpening, RecruiterProfile

# Setup logging
logger = logging.getLogger(__name__)


def create_job_opening_from_xml(
    xml_data: str, recruiter_profile: RecruiterProfile, original_description: str = ""
) -> JobOpening | None:
    """
    Create a JobOpening from XML data.

    Args:
        xml_data: XML string representation of the job
        recruiter_profile: RecruiterProfile instance for the job creator
        original_description: The original job description text as provided by the recruiter

    Returns:
        Created JobOpening instance or None if creation failed
    """
    try:
        # Parse XML
        root = ET.fromstring(xml_data)

        # Extract basic information
        title = _get_xml_text(root, "title")
        company = _get_xml_text(root, "company")
        location = _get_xml_text(root, "location")
        description = _get_xml_text(root, "description")

        # Extract job details
        details = root.find("details")
        job_level = _get_xml_text(details, "job_level") if details is not None else ""
        employment_type = (
            _get_xml_text(details, "employment_type") if details is not None else ""
        )

        # Extract salary information
        salary_min_text = (
            _get_xml_text(details, "salary_min") if details is not None else ""
        )
        salary_max_text = (
            _get_xml_text(details, "salary_max") if details is not None else ""
        )

        salary_min = (
            float(salary_min_text)
            if salary_min_text and salary_min_text.replace(".", "", 1).isdigit()
            else None
        )
        salary_max = (
            float(salary_max_text)
            if salary_max_text and salary_max_text.replace(".", "", 1).isdigit()
            else None
        )

        benefits = _get_xml_text(details, "benefits") if details is not None else ""
        perks = _get_xml_text(details, "perks") if details is not None else ""

        # Extract requirements
        requirements = root.find("requirements")

        # Extract skills
        skills = []
        if requirements is not None:
            skills_elem = requirements.find("skills")
            if skills_elem is not None:
                for skill_elem in skills_elem.findall("skill"):
                    if skill_elem.text and skill_elem.text.strip():
                        skills.append(skill_elem.text.strip())

        required_skills = "\n".join(skills)

        # Extract qualifications
        qualifications = []
        if requirements is not None:
            quals_elem = requirements.find("qualifications")
            if quals_elem is not None:
                for qual_elem in quals_elem.findall("qualification"):
                    if qual_elem.text and qual_elem.text.strip():
                        qualifications.append(qual_elem.text.strip())

        required_qualifications = "\n".join(qualifications)

        # Extract experience
        experience = (
            _get_xml_text(requirements, "experience")
            if requirements is not None
            else ""
        )

        # Extract responsibilities
        responsibilities_list = []
        responsibilities_elem = root.find("responsibilities")
        if responsibilities_elem is not None:
            for resp_elem in responsibilities_elem.findall("responsibility"):
                if resp_elem.text and resp_elem.text.strip():
                    responsibilities_list.append(resp_elem.text.strip())

        responsibilities = "\n".join(responsibilities_list)

        # Extract working conditions
        working_conditions = root.find("working_conditions")
        working_hours = (
            _get_xml_text(working_conditions, "hours")
            if working_conditions is not None
            else ""
        )
        work_environment = (
            _get_xml_text(working_conditions, "environment")
            if working_conditions is not None
            else ""
        )
        reporting_to = (
            _get_xml_text(working_conditions, "reporting_to")
            if working_conditions is not None
            else ""
        )
        travel_requirements = (
            _get_xml_text(working_conditions, "travel")
            if working_conditions is not None
            else ""
        )

        # Extract soft skills – expect a <soft_skills> section that may contain
        # either nested <skill> elements (preferred) or plain text fallback.
        soft_skills_list: list[str] = []
        if requirements is not None:
            soft_skills_elem = requirements.find("soft_skills")
            if soft_skills_elem is not None:
                # First, check for nested <skill> elements (preferred format)
                for skill_elem in soft_skills_elem.findall("skill"):
                    if skill_elem.text and skill_elem.text.strip():
                        soft_skills_list.append(skill_elem.text.strip())

                # Fallback: if there were no nested <skill> elements but there is
                # text content directly under <soft_skills>, capture it.
                if (
                    not soft_skills_list
                    and soft_skills_elem.text
                    and soft_skills_elem.text.strip()
                ):
                    # Split on common separators to produce a list – pipe, comma, semicolon
                    raw_text = soft_skills_elem.text.strip()
                    for token in re.split(r"[|,;]", raw_text):
                        token = token.strip()
                        if token:
                            soft_skills_list.append(token)

        # Join the list using the same delimiter pattern used for technical skills
        soft_skills = "\n".join(soft_skills_list)

        # Extract performance expectations (may be missing in some XML formats)
        performance_expectations = ""
        details_elem = root.find("details")
        if details_elem is not None:
            perf_elem = details_elem.find("performance_expectations")
            if perf_elem is not None and perf_elem.text:
                performance_expectations = perf_elem.text.strip()

        # Extract daily tasks (may be missing in some XML formats)
        daily_tasks = ""
        details_elem = root.find("details")
        if details_elem is not None:
            tasks_elem = details_elem.find("daily_tasks")
            if tasks_elem is not None and tasks_elem.text:
                daily_tasks = tasks_elem.text.strip()

        # Create JobOpening
        job_opening = JobOpening.objects.create(
            recruiter=recruiter_profile,
            title=title,
            company=company,
            location=location,
            description=description,
            job_level=job_level,
            employment_type=employment_type,
            salary_min=salary_min,
            salary_max=salary_max,
            benefits=benefits,
            additional_perks=perks,
            required_skills=required_skills,
            required_qualifications=required_qualifications,
            experience_required=experience,
            soft_skills=soft_skills,
            responsibilities=responsibilities,
            daily_tasks=daily_tasks,
            performance_expectations=performance_expectations,
            working_hours=working_hours,
            work_environment=work_environment,
            reporting_to=reporting_to,
            travel_requirements=travel_requirements,
            status="draft",
            original_description=original_description,
        )

        # Log successful creation
        logger.info(
            "Created job opening: %s (ID: %d) for recruiter: %s",
            job_opening.title,
            job_opening.pk,
            recruiter_profile.user.email,
        )

        return job_opening

    except Exception as e:
        logger.error("Error creating job opening from XML: %s", str(e))
        return None


def _get_xml_text(parent: ET.Element | None, tag: str) -> str:
    """
    Helper function to safely get text from an XML element.

    Args:
        parent: Parent XML element
        tag: Tag name to find

    Returns:
        Text content of the element or empty string if not found
    """
    if parent is None:
        return ""

    element = parent.find(tag)
    if element is not None and element.text:
        return element.text.strip()

    return ""
