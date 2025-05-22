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

from apps.job_seekers.models.profile import JobSeekerProfile
from apps.resume_processing.models import ResumeProcessingTaskProgress
from apps.resume_processing.utils.extraction import extract_text
from apps.resume_processing.utils.llm_processor import convert_text_to_xml
from apps.resume_processing.utils.profile_updater import (
    generate_and_save_personal_tagline,
    update_profile_fields,
)
from apps.resume_processing.utils.xml_error_reporting import (
    log_xml_error,
    save_diagnostic_xml,
)
from apps.resume_processing.utils.xml_parser import parse_resume_xml

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
    5. Generate personal tagline (integrated into the profile update step)

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

    # Get a profile identifier that works for logging
    if profile.user_owner:
        profile_identifier = f"Profile #{profile.pk} (User: {profile.user_owner.email})"
    elif profile.candidate_pool:
        profile_identifier = (
            f"Profile #{profile.pk} (Pool: {profile.candidate_pool.name})"
        )
    else:
        profile_identifier = f"Profile #{profile.pk} (Orphaned)"

    # Log that we're starting processing
    logger.info("Starting resume processing for %s", profile_identifier)

    # Initialize or get progress tracker if task_id is provided
    progress_tracker = None
    if task_id:
        try:
            # The tracking record is created in ResumeUploadView before the task is queued
            progress_tracker = ResumeProcessingTaskProgress.objects.get(task_id=task_id)
            # Update status to running if not already
            if progress_tracker.status == "pending":
                progress_tracker.status = "running"
                progress_tracker.message = "Processing resume..."
                progress_tracker.save(update_fields=["status", "message"])
        except ResumeProcessingTaskProgress.DoesNotExist:
            logger.error("Progress tracker not found for task_id: %s", task_id)
            # Continue with processing even if tracking fails
        except Exception as e:
            logger.error("Error getting progress tracker: %s", e)
            # Continue with processing even if tracking fails

    try:
        # Step 1: Get the absolute file path
        if os.path.isabs(file_path):
            # Already an absolute path, use it directly
            abs_file_path = file_path
        else:
            # Relative path, try to use default_storage.path if possible
            try:
                abs_file_path = default_storage.path(file_path)
            except NotImplementedError:
                # If the storage doesn't support path, we need to use the file directly
                logger.warning(
                    "Storage doesn't support absolute paths. Using original path: %s",
                    file_path,
                )
                abs_file_path = file_path

        logger.info("Resolved file path: %s", abs_file_path)
        pipeline_steps.append("file_path_resolved")

        # Update progress
        if progress_tracker:
            progress_tracker.mark_step_complete("file_path_resolved")

        # Step 2: Extract text from resume (any supported format)
        logger.info("Extracting text from file: %s", file_path)
        resume_text = extract_text(abs_file_path)
        if not resume_text:
            error_msg = "Failed to extract any text from resume"
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
        logger.debug("Extracted text (preview): %s", text_preview)
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

        # Step 5: Update profile (fields only)
        logger.info("Updating fields for %s", profile_identifier)
        update_success = update_profile_fields(profile, parsed_data)
        pipeline_steps.append("profile_updated")
        # Update progress for profile update
        if progress_tracker:
            progress_tracker.mark_step_complete("profile_updated")

        # Step 6: Generate personal tagline
        logger.info("Generating personal tagline for %s", profile_identifier)
        # Generate and save personal tagline
        tagline_success = generate_and_save_personal_tagline(
            profile, xml_content, parsed_data
        )
        pipeline_steps.append("personal_tagline_generated")
        # Update progress for tagline generation
        if progress_tracker:
            progress_tracker.mark_step_complete("personal_tagline_generated")

        # Step 7: Delete the temporary file if it's not an absolute path
        if not os.path.isabs(file_path):
            try:
                logger.info("Deleting temporary file: %s", file_path)
                default_storage.delete(file_path)
                pipeline_steps.append("temp_file_deleted")
            except Exception as e:
                logger.warning(
                    "Could not delete temporary file: %s - %s", file_path, str(e)
                )

            # Update progress
            if progress_tracker:
                progress_tracker.mark_step_complete("temp_file_deleted")

        # Calculate processing time
        processing_time = time.time() - start_time
        logger.info(
            "Resume processing completed successfully for %s in %.2fs",
            profile_identifier,
            processing_time,
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
            "success": update_success and tagline_success,
            "message": "Resume processed successfully",
            "profile_data": parsed_data,
            "pipeline_steps": pipeline_steps,
            "processing_time": processing_time,
        }

    except Exception as e:
        logger.error("Error processing resume: %s", str(e))
        logger.error(traceback.format_exc())

        # Save diagnostic information if possible
        diagnostic_info = {
            "text_sample": "Resume text unavailable or error extracting sample",
            "xml_sample": "XML content unavailable or error extracting sample",
            "error": str(e),
        }

        if resume_text:
            diagnostic_info["text_sample"] = (
                resume_text[:500] + "..." if len(resume_text) > 500 else resume_text
            )

        if xml_content:
            diagnostic_info["xml_sample"] = (
                xml_content[:500] + "..." if len(xml_content) > 500 else xml_content
            )

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
