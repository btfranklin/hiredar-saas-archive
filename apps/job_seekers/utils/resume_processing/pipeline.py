"""
Resume processing pipeline orchestration.

This module defines the complete resume processing pipeline for processing resumes.
"""

import logging
import os
import time
import traceback
import xml.etree.ElementTree as ET
from typing import Any

from django.core.files.storage import default_storage

from apps.job_seekers.models import JobSeekerProfile, ResumeProcessingTaskProgress
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


def process_resume(
    file_path: str,
    profile: JobSeekerProfile,
    task_id: str | None = None,
) -> dict[str, Any]:
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
        task_id: Optional task ID for progress tracking

    Returns:
        Dictionary with processing results
    """
    pipeline_steps = []
    resume_text: str | None = None
    xml_content: str | None = None
    parsed_data: dict[str, Any] | None = None
    start_time = time.time()

    # Initialize or get progress tracker if task_id is provided
    progress_tracker = None
    if task_id:
        try:
            progress_tracker, _ = ResumeProcessingTaskProgress.objects.get_or_create(
                task_id=task_id,
                defaults={
                    "user": profile.user,
                    "task_type": "resume_processing",
                    "status": "running",
                    "message": "Processing resume...",
                    "current_step": "file_path_resolved",
                },
            )
        except Exception as e:
            logger.error("Error creating progress tracker: %s", e)
            # Continue with processing even if tracking fails

    try:
        # Step 1: Get the absolute file path
        if not os.path.isabs(file_path):
            abs_file_path = default_storage.path(file_path)
        else:
            abs_file_path = file_path
        pipeline_steps.append("file_path_resolved")

        # Update progress
        if progress_tracker:
            progress_tracker.mark_step_complete("file_path_resolved")

        # Step 2: Extract text from PDF
        logger.info("Extracting text from PDF: %s", file_path)
        resume_text = extract_text_from_pdf(abs_file_path)
        if not resume_text:
            error_msg = "Failed to extract any text from PDF"
            if progress_tracker:
                progress_tracker.status = "failed"
                progress_tracker.message = error_msg
                progress_tracker.save(update_fields=["status", "message"])

            return {
                "success": False,
                "message": error_msg,
                "error_type": "text_extraction_error",
                "pipeline_steps": pipeline_steps,
            }

        text_preview = resume_text[:100] + "..."
        logger.info("Extracted text (preview): %s", text_preview)
        pipeline_steps.append("text_extracted")

        # Update progress
        if progress_tracker:
            progress_tracker.mark_step_complete("text_extracted")

        # Step 3: Convert resume text to XML via LLM
        logger.info("Converting text to XML via LLM")
        xml_content = convert_text_to_xml(resume_text)
        pipeline_steps.append("xml_generated")

        # Update progress
        if progress_tracker:
            progress_tracker.mark_step_complete("xml_generated")

        # Step 4: Parse XML string into a structured dictionary
        logger.info("Parsing XML")
        try:
            parsed_data = parse_resume_xml(xml_content)
            pipeline_steps.append("xml_parsed")

            # Update progress
            if progress_tracker:
                progress_tracker.mark_step_complete("xml_parsed")

        except ET.ParseError as e:
            # Log the XML error
            log_xml_error(e, xml_content)
            # Save diagnostic file
            diagnostic_path = save_diagnostic_xml(
                e, xml_content, abs_file_path, "parsing"
            )

            error_msg = f"Error parsing XML: {str(e)}"
            if progress_tracker:
                progress_tracker.status = "failed"
                progress_tracker.message = error_msg
                progress_tracker.save(update_fields=["status", "message"])

            return {
                "success": False,
                "message": error_msg,
                "error_type": "xml_parse_error",
                "diagnostic_file": diagnostic_path,
                "pipeline_steps": pipeline_steps,
            }

        # Step 5: Update profile
        logger.info("Updating profile for user %s", profile.user.email)
        update_success = update_profile(profile, parsed_data, xml_content)
        pipeline_steps.append("profile_updated")

        # Update progress
        if progress_tracker:
            progress_tracker.mark_step_complete("profile_updated")

        # Step 6: Delete the temporary file if it's in MEDIA_ROOT
        if not os.path.isabs(file_path):
            logger.info("Deleting temporary file: %s", file_path)
            default_storage.delete(file_path)
            pipeline_steps.append("temp_file_deleted")

            # Update progress
            if progress_tracker:
                progress_tracker.mark_step_complete("temp_file_deleted")

        # Calculate processing time
        processing_time = time.time() - start_time
        logger.info(
            "Resume processing completed successfully in %.2fs", processing_time
        )

        # Final progress update
        if progress_tracker:
            progress_tracker.status = "completed"
            progress_tracker.message = "Resume processed successfully"
            progress_tracker.progress_percent = 100
            progress_tracker.save(
                update_fields=["status", "message", "progress_percent"]
            )

        # Return success response
        return {
            "success": update_success,
            "message": "Resume processed successfully",
            "profile_data": parsed_data,
            "pipeline_steps": pipeline_steps,
            "processing_time": processing_time,
        }

    except Exception as e:
        logger.error("Error processing resume: %s", str(e))
        logger.error(traceback.format_exc())

        # Save diagnostic information if possible
        diagnostic_info = {}
        if resume_text and isinstance(resume_text, str):
            # Safe way to extract a sample that won't trigger unsubscriptable errors
            sample_length = min(len(resume_text), 500)
            diagnostic_info["text_sample"] = resume_text[0:sample_length] + "..."

        if xml_content and isinstance(xml_content, str):
            # Safe way to extract a sample that won't trigger unsubscriptable errors
            sample_length = min(len(xml_content), 500)
            diagnostic_info["xml_sample"] = xml_content[0:sample_length] + "..."

        # Update progress tracker
        if progress_tracker:
            progress_tracker.status = "failed"
            progress_tracker.message = f"Error processing resume: {str(e)}"
            progress_tracker.save(update_fields=["status", "message"])

        return {
            "success": False,
            "message": f"Error processing resume: {str(e)}",
            "error_type": "processing_error",
            "diagnostic_info": diagnostic_info,
            "pipeline_steps": pipeline_steps,
            "exception": str(e),
        }
