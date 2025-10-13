"""
Job processing services for the recruiters app.

This package hosts orchestration helpers for converting recruiter-supplied job
descriptions into structured data and persisting the resulting openings.
"""

from apps.recruiters.services.job_processing.llm_processor import convert_text_to_xml
from apps.recruiters.services.job_processing.xml_parser import (
    create_job_opening_from_xml,
)

__all__ = [
    "convert_text_to_xml",
    "create_job_opening_from_xml",
]
