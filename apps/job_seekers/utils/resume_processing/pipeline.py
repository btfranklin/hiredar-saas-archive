"""
Resume processing pipeline orchestration.

This module defines the complete resume processing pipeline for processing resumes.
"""

import logging
import os
import traceback
import xml.etree.ElementTree as ET
from typing import Any

from django.core.files.storage import default_storage

from apps.job_seekers.models import JobSeekerProfile
from apps.job_seekers.utils.resume_processing.extraction import extract_text_from_pdf
from apps.job_seekers.utils.resume_processing.llm_processor import convert_text_to_xml
from apps.job_seekers.utils.resume_processing.profile_updater import update_profile
from apps.job_seekers.utils.resume_processing.xml_error_reporting import (
    log_xml_error,
    save_diagnostic_xml,
)
from apps.job_seekers.utils.resume_processing.xml_parser import parse_resume_xml

# Setup logging
logger = logging.getLogger(__name__)


def process_resume(file_path: str, profile: JobSeekerProfile) -> dict[str, Any]:
    """
    Process a resume file and update a JobSeekerProfile.

    This function orchestrates the complete resume processing pipeline:
    1. Extract text from PDF
    2. Convert to structured XML using LLM
    3. Parse XML to extract key information
    4. Update the JobSeekerProfile with extracted information

    Args:
        file_path: Path to the resume file (absolute or relative to MEDIA_ROOT)
        profile: JobSeekerProfile instance to update

    Returns:
        Dictionary with processing results
    """
    pipeline_steps = []
    resume_text: str | None = None
    xml_content: str | None = None
    parsed_data: dict[str, Any] | None = None

    try:
        # Step 1: Get the absolute file path
        if not os.path.isabs(file_path):
            abs_file_path = default_storage.path(file_path)
        else:
            abs_file_path = file_path
        pipeline_steps.append("file_path_resolved")

        # Step 2: Extract text from PDF
        logger.info("Extracting text from PDF: %s", file_path)
        resume_text = extract_text_from_pdf(abs_file_path)
        if not resume_text:
            return {
                "success": False,
                "message": "Failed to extract any text from PDF",
                "error_type": "text_extraction_error",
                "pipeline_steps": pipeline_steps,
            }

        text_preview = resume_text[:100] + "..."
        logger.info("Extracted text (preview): %s", text_preview)
        pipeline_steps.append("text_extracted")

        # Step 3: Convert resume text to XML via LLM
        logger.info("Converting text to XML via LLM")
        xml_content = convert_text_to_xml(resume_text)
        pipeline_steps.append("xml_generated")

        # Step 4: Parse XML string into a structured dictionary
        logger.info("Parsing XML")
        try:
            parsed_data = parse_resume_xml(xml_content)
            pipeline_steps.append("xml_parsed")
        except ET.ParseError as e:
            # Log the XML error
            log_xml_error(e, xml_content)
            # Save diagnostic file
            diagnostic_path = save_diagnostic_xml(
                e, xml_content, abs_file_path, "parsing"
            )
            return {
                "success": False,
                "message": f"Error parsing XML: {str(e)}",
                "error_type": "xml_parse_error",
                "diagnostic_file": diagnostic_path,
                "pipeline_steps": pipeline_steps,
            }

        # Step 5: Update profile
        logger.info("Updating profile for user %s", profile.user.email)
        update_success = update_profile(profile, parsed_data, xml_content)
        pipeline_steps.append("profile_updated")

        # Step 6: Delete the temporary file if it's in MEDIA_ROOT
        if not os.path.isabs(file_path):
            logger.info("Deleting temporary file: %s", file_path)
            default_storage.delete(file_path)
            pipeline_steps.append("temp_file_deleted")

        # Return success response
        logger.info("Resume processing completed successfully")
        return {
            "success": update_success,
            "message": "Resume processed successfully",
            "profile_data": parsed_data,
            "pipeline_steps": pipeline_steps,
        }

    except Exception as e:
        logger.error("Error processing resume: %s", str(e))
        logger.error(traceback.format_exc())

        # Save diagnostic information if possible
        diagnostic_info = {}
        if resume_text:
            diagnostic_info["text_sample"] = resume_text[:500] + "..."
        if xml_content:
            diagnostic_info["xml_sample"] = xml_content[:500] + "..."

        return {
            "success": False,
            "message": f"Error processing resume: {str(e)}",
            "error_type": "processing_error",
            "diagnostic_info": diagnostic_info,
            "pipeline_steps": pipeline_steps,
            "exception": str(e),
        }
