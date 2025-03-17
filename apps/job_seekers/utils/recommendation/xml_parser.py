"""
XML Parser for LLM responses.

This module contains functions for parsing XML responses from LLM services
and converting them into model instances.
"""

import logging
import xml.etree.ElementTree as ET

from apps.job_seekers.models import JobSeekerProfile, RoleRecommendation

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
