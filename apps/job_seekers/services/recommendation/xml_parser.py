"""
XML Parser for LLM responses.

This module contains functions for parsing XML responses from LLM services
and converting them into model instances.
"""

import logging
import re
import xml.etree.ElementTree as ET

from apps.job_seekers.models import JobSeekerProfile, RoleRecommendation, TalentSheet

# Setup logging
logger = logging.getLogger(__name__)


# Helper to remove XML 1.0 invalid control characters
def remove_invalid_xml_chars(text: str) -> str:
    return re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", text)


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

    # Sanitize XML: remove invalid control chars and escape stray ampersands
    xml_content = remove_invalid_xml_chars(xml_content)
    xml_content = re.sub(
        r"&(?!amp;|lt;|gt;|apos;|quot;|#[0-9]+;)", "&amp;", xml_content
    )

    # Attempt parsing, with fallback for malformed XML
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        logger.warning(
            "xml.etree parser failed for role recommendations: %s, attempting recovery",
            str(e),
        )
        try:
            from lxml import etree as lxml_etree

            parser = lxml_etree.XMLParser(recover=True)
            root = lxml_etree.fromstring(xml_content.encode("utf-8"), parser)
        except ImportError:
            logger.error(
                "lxml not installed; cannot recover malformed XML for role recommendations"
            )
            logger.debug("Response content: %s", xml_response[:1000])
            return []
        except Exception as rec_e:
            logger.error(
                "Failed to recover malformed XML for role recommendations: %s",
                str(rec_e),
            )
            logger.debug("Response content: %s", xml_response[:1000])
            return []

    # Build recommendation objects from parsed XML
    recommendations: list[RoleRecommendation] = []
    for role_elem in root.findall("./role_recommendation"):
        title_elem = role_elem.find("title")
        desc_elem = role_elem.find("description")
        if (
            title_elem is not None
            and title_elem.text
            and desc_elem is not None
            and desc_elem.text
        ):
            rec = RoleRecommendation(
                job_seeker=job_seeker,
                role_title=title_elem.text.strip(),
                description=desc_elem.text.strip(),
                is_candidate_interested=False,
            )
            recommendations.append(rec)

    if not recommendations:
        logger.warning("No role recommendations found in XML response")
    else:
        logger.info("Parsed %d role recommendations from XML", len(recommendations))
    return recommendations


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

    # Clean out any invalid XML control characters before parsing
    xml_content = remove_invalid_xml_chars(xml_content)
    # Escape stray ampersands not part of an entity to avoid parse errors
    xml_content = re.sub(
        r"&(?!amp;|lt;|gt;|apos;|quot;|#[0-9]+;)", "&amp;", xml_content
    )

    # Attempt to parse XML, with fallback to lxml if necessary
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as error:
        logger.warning("xml.etree parser failed: %s, attempting recovery", str(error))
        try:
            from lxml import etree as lxml_etree

            parser = lxml_etree.XMLParser(recover=True)
            root = lxml_etree.fromstring(xml_content.encode("utf-8"), parser)
        except ImportError:
            logger.error("lxml not installed, cannot recover malformed XML")
            logger.debug("Response content: %s", xml_response[:1000])
            raise ValueError(
                f"Failed to parse talent sheet XML: {str(error)}"
            ) from error

    # Extract required elements
    promotional_blurb_elem = root.find("./promotional_blurb")
    experience_overview_elem = root.find("./experience_overview")
    ideal_roles_elem = root.find("./ideal_roles")
    salary_min_elem = root.find("./salary_min")

    # Validate required elements exist
    if promotional_blurb_elem is None or not promotional_blurb_elem.text:
        raise ValueError("Missing promotional_blurb element in talent sheet XML")

    if experience_overview_elem is None:
        raise ValueError("Missing experience_overview element in talent sheet XML")

    # Build a human-readable summary from <experience> children if they exist
    experience_blocks: list[str] = []
    for exp in experience_overview_elem.findall("./experience"):
        position = exp.findtext("position", default="").strip()
        dates = exp.findtext("dates", default="").strip()
        impact = exp.findtext("impact", default="").strip()

        # Skip completely empty items
        if not (position or dates or impact):
            continue

        block_lines: list[str] = []
        if position:
            block_lines.append(f"Position: {position}")
        if dates:
            block_lines.append(f"Dates: {dates}")
        if impact:
            block_lines.append(f"Impact: {impact}")

        experience_blocks.append("\n".join(block_lines))

    # If children provided, join them with double newlines; otherwise use raw text
    if experience_blocks:
        experience_overview_text = "\n\n".join(experience_blocks)
    else:
        # Fallback: use any direct text content inside the element
        raw_text = experience_overview_elem.text or ""
        experience_overview_text = raw_text.strip()

    if not experience_overview_text:
        raise ValueError("experience_overview element contained no usable content")

    # Create TalentSheet instance
    talent_sheet = TalentSheet(
        job_seeker=job_seeker,
        promotional_blurb=promotional_blurb_elem.text.strip(),
        experience_overview=experience_overview_text,
        is_published=True,  # Default to published - talent sheets are created and published together
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

    logger.info(
        "Successfully parsed talent sheet XML for %s",
        (
            job_seeker.user_owner.get_full_name()
            if job_seeker and job_seeker.user_owner
            else "unknown user"
        ),
    )
    return talent_sheet
