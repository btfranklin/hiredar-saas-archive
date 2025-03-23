"""
Job processing utilities for the recruiters app.

This package contains utilities for processing job descriptions into structured data
and creating job openings from that data.
"""

# Import all utilities for easy access
from apps.recruiters.utils.job_processing.llm_processor import convert_text_to_xml
from apps.recruiters.utils.job_processing.pipeline import process_job_description
from apps.recruiters.utils.job_processing.xml_parser import create_job_opening_from_xml

# Export all utility functions
__all__ = [
    "convert_text_to_xml",
    "create_job_opening_from_xml",
    "process_job_description",
]
