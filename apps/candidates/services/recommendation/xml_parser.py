"""XML parsing helpers for candidate recommendation workflows."""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from apps.candidates.models import (
    CandidateProfile,
    CandidateRoleRecommendation,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class CandidateProfileEnrichment:
    """Container for talent sheet content mapped onto CandidateProfile fields."""

    promotional_blurb: str
    experience_overview: str
    ideal_roles: str


def _remove_invalid_xml_chars(text: str) -> str:
    """Strip control characters that violate XML 1.0."""
    return re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", text)


def _sanitize_xml(text: str) -> str:
    """Escape stray ampersands to keep parsers happy."""
    return re.sub(r"&(?!amp;|lt;|gt;|apos;|quot;|#[0-9]+;)", "&amp;", text)


def parse_role_recommendations_xml(
    xml_response: str,
    candidate_profile: CandidateProfile | None = None,
) -> list[CandidateRoleRecommendation]:
    """
    Parse an XML payload into unsaved CandidateRoleRecommendation objects.
    """
    xml_start = xml_response.find("<role_recommendations>")
    xml_end = xml_response.find("</role_recommendations>") + len(
        "</role_recommendations>"
    )

    if xml_start == -1 or xml_end == -1:
        logger.error("Missing <role_recommendations> envelope in LLM response")
        logger.debug("Response preview: %s", xml_response[:1000])
        raise ValueError("LLM response missing role_recommendations tags")

    xml_content = xml_response[xml_start:xml_end]
    xml_content = _sanitize_xml(_remove_invalid_xml_chars(xml_content))

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as exc:
        logger.warning(
            "ElementTree failed to parse role recommendations (%s). Attempting recovery.",
            exc,
        )
        try:
            from lxml import etree as lxml_etree

            parser = lxml_etree.XMLParser(recover=True)
            root = lxml_etree.fromstring(xml_content.encode("utf-8"), parser)
        except ImportError:
            logger.error("lxml unavailable; returning empty role recommendations list")
            logger.debug("Payload: %s", xml_response[:1000])
            return []
        except Exception as recovery_exc:  # pragma: no cover - defensive
            logger.error("Failed to recover malformed XML: %s", recovery_exc)
            logger.debug("Payload: %s", xml_response[:1000])
            return []

    recommendations: list[CandidateRoleRecommendation] = []
    for role_elem in root.findall("./role_recommendation"):
        title_text = role_elem.findtext("title", default="").strip()
        description_text = role_elem.findtext("description", default="").strip()
        if not (title_text and description_text):
            continue

        recommendations.append(
            CandidateRoleRecommendation(
                candidate_profile=candidate_profile,
                role_title=title_text,
                description=description_text,
            )
        )

    if not recommendations:
        logger.warning("Parsed zero role recommendations from XML payload")
    else:
        logger.info("Parsed %d role recommendations", len(recommendations))

    return recommendations


def parse_profile_enrichment_xml(
    xml_response: str,
    candidate_profile: CandidateProfile | None = None,
) -> CandidateProfileEnrichment:
    """Parse talent-sheet style XML into CandidateProfileEnrichment data."""
    xml_start = xml_response.find("<talent_sheet>")
    xml_end = xml_response.find("</talent_sheet>") + len("</talent_sheet>")

    if xml_start == -1 or xml_end == -1:
        logger.error("Missing <talent_sheet> envelope in LLM response")
        logger.debug("Response preview: %s", xml_response[:1000])
        raise ValueError("LLM response missing talent_sheet tags")

    xml_content = xml_response[xml_start:xml_end]
    xml_content = _sanitize_xml(_remove_invalid_xml_chars(xml_content))

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as exc:
        logger.warning(
            "ElementTree failed to parse talent sheet (%s). Attempting recovery.",
            exc,
        )
        try:
            from lxml import etree as lxml_etree

            parser = lxml_etree.XMLParser(recover=True)
            root = lxml_etree.fromstring(xml_content.encode("utf-8"), parser)
        except ImportError:
            logger.error("lxml unavailable; cannot recover malformed talent sheet XML")
            logger.debug("Payload: %s", xml_response[:1000])
            raise ValueError(f"Failed to parse talent sheet XML: {exc}") from exc

    promotional_blurb = root.findtext("./promotional_blurb", default="").strip()
    experience_overview_elem = root.find("./experience_overview")
    ideal_roles = root.findtext("./ideal_roles", default="").strip()

    if not promotional_blurb:
        raise ValueError("talent_sheet XML missing promotional_blurb content")
    if experience_overview_elem is None:
        raise ValueError("talent_sheet XML missing experience_overview element")

    experience_blocks: list[str] = []
    for exp in experience_overview_elem.findall("./experience"):
        position = exp.findtext("position", default="").strip()
        dates = exp.findtext("dates", default="").strip()
        impact = exp.findtext("impact", default="").strip()

        if not (position or dates or impact):
            continue

        lines = []
        if position:
            lines.append(f"Position: {position}")
        if dates:
            lines.append(f"Dates: {dates}")
        if impact:
            lines.append(f"Impact: {impact}")
        experience_blocks.append("\n".join(lines))

    if experience_blocks:
        experience_overview = "\n\n".join(experience_blocks)
    else:
        experience_overview = (experience_overview_elem.text or "").strip()

    if not experience_overview:
        raise ValueError("experience_overview element contained no usable content")

    logger.info(
        "Parsed talent sheet enrichment for candidate profile %s",
        candidate_profile.pk if candidate_profile else "unknown",
    )

    return CandidateProfileEnrichment(
        promotional_blurb=promotional_blurb,
        experience_overview=experience_overview,
        ideal_roles=ideal_roles,
    )
