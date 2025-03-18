"""
XML Parser for LLM responses.

This module contains functions for parsing XML responses from LLM services
and converting them into model instances.
"""

import logging
import xml.etree.ElementTree as ET

from apps.job_seekers.models import JobSeekerProfile, RoleRecommendation, TalentSheet

# Setup logging
logger = logging.getLogger(__name__)


def parse_role_recommendations_xml(
    xml_response: str, job_seeker: JobSeekerProfile | None = None
) -> list[RoleRecommendation]:
    """
    Parse an XML response from an LLM containing role recommendations.

    This function extracts role title and description information from
    an XML response and returns a list of RoleRecommendation model instances
    (unsaved to the database).

    Args:
        xml_response: The XML response from the LLM
        job_seeker: Optional JobSeekerProfile to associate with recommendations

    Returns:
        A list of RoleRecommendation model instances (unsaved)

    Raises:
        ValueError: If the XML is invalid or missing required elements
    """
    # Extract XML content from the response (in case there's any wrapping text)
    xml_start = xml_response.find("<role_recommendations>")
    xml_end = xml_response.find("</role_recommendations>") + len(
        "</role_recommendations>"
    )

    if xml_start == -1 or xml_end == -1:
        logger.error("Failed to find role_recommendations XML tags in response")
        logger.debug("Response content: %s", xml_response[:1000])
        raise ValueError(
            "LLM response does not contain valid XML with role_recommendations tags"
        )

    xml_content = xml_response[xml_start:xml_end]

    try:
        # Parse the XML
        root = ET.fromstring(xml_content)
        recommendations = []

        for role_elem in root.findall("./role_recommendation"):
            title_elem = role_elem.find("title")
            desc_elem = role_elem.find("description")

            if (
                title_elem is not None
                and title_elem.text
                and desc_elem is not None
                and desc_elem.text
            ):
                recommendation = RoleRecommendation(
                    job_seeker=job_seeker,
                    role_title=title_elem.text.strip(),
                    description=desc_elem.text.strip(),
                    is_candidate_interested=False,  # Default to not interested
                )
                recommendations.append(recommendation)

        if not recommendations:
            logger.warning("No role recommendations found in XML response")

        logger.info("Parsed %d role recommendations from XML", len(recommendations))
        return recommendations

    except ET.ParseError as e:
        logger.error("Failed to parse XML response: %s", str(e))
        logger.debug("Response content: %s", xml_response[:1000])
        raise ValueError(f"Failed to parse XML response: {str(e)}") from e


def parse_talent_sheet_xml(
    xml_response: str, job_seeker: JobSeekerProfile | None = None
) -> TalentSheet:
    """
    Parse an XML response from an LLM containing talent sheet data.

    This function extracts promotional blurb, skill overview, ideal roles,
    and salary expectations from an XML response and returns a TalentSheet
    model instance (unsaved to the database).

    Args:
        xml_response: The XML response from the LLM
        job_seeker: Optional JobSeekerProfile to associate with the talent sheet

    Returns:
        An unsaved TalentSheet model instance

    Raises:
        ValueError: If the XML is invalid or missing required elements
    """
    # Extract XML content from the response (in case there's any wrapping text)
    xml_start = xml_response.find("<talent_sheet>")
    xml_end = xml_response.find("</talent_sheet>") + len("</talent_sheet>")

    if xml_start == -1 or xml_end == -1:
        logger.error("Failed to find talent_sheet XML tags in response")
        logger.debug("Response content: %s", xml_response[:1000])
        raise ValueError(
            "LLM response does not contain valid XML with talent_sheet tags"
        )

    xml_content = xml_response[xml_start:xml_end]

    try:
        # Parse the XML
        root = ET.fromstring(xml_content)

        # Extract required elements
        promotional_blurb_elem = root.find("./promotional_blurb")
        skill_overview_elem = root.find("./skill_overview")
        ideal_roles_elem = root.find("./ideal_roles")
        salary_min_elem = root.find("./salary_min")
        salary_max_elem = root.find("./salary_max")

        # Validate required elements exist
        if promotional_blurb_elem is None or not promotional_blurb_elem.text:
            raise ValueError("Missing promotional_blurb element in talent sheet XML")

        if skill_overview_elem is None or not skill_overview_elem.text:
            raise ValueError("Missing skill_overview element in talent sheet XML")

        # Create TalentSheet instance
        talent_sheet = TalentSheet(
            job_seeker=job_seeker,
            promotional_blurb=promotional_blurb_elem.text.strip(),
            skill_overview=skill_overview_elem.text.strip(),
        )

        # Handle optional elements
        if ideal_roles_elem is not None and ideal_roles_elem.text:
            talent_sheet.ideal_roles = ideal_roles_elem.text.strip()

        # Handle salary expectations (convert to decimal)
        if salary_min_elem is not None and salary_min_elem.text:
            try:
                talent_sheet.salary_min = float(salary_min_elem.text.strip())
            except ValueError:
                logger.warning(
                    "Invalid salary_min value in talent sheet XML: %s",
                    salary_min_elem.text,
                )

        if salary_max_elem is not None and salary_max_elem.text:
            try:
                talent_sheet.salary_max = float(salary_max_elem.text.strip())
            except ValueError:
                logger.warning(
                    "Invalid salary_max value in talent sheet XML: %s",
                    salary_max_elem.text,
                )

        logger.info(
            "Successfully parsed talent sheet XML for %s",
            job_seeker.user.email if job_seeker else "unknown user",
        )
        return talent_sheet

    except ET.ParseError as e:
        logger.error("Failed to parse XML response: %s", str(e))
        logger.debug("Response content: %s", xml_response[:1000])
        raise ValueError(f"Failed to parse talent sheet XML: {str(e)}") from e
