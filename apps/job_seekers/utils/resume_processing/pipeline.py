"""
Resume processing pipeline orchestration.

This module defines the complete resume processing pipeline and provides
both synchronous and asynchronous execution options.
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


def process_resume_sync(file_path: str, profile: JobSeekerProfile) -> dict[str, Any]:
    """
    Process a resume file synchronously, updating the job seeker profile.

    Args:
        file_path: Path to the resume file
        profile: The JobSeekerProfile to update

    Returns:
        Dictionary with success status and result details.
        In case of failure, includes detailed error information.
    """
    # Get absolute path to the file
    try:
        absolute_path = default_storage.path(file_path)

        if not os.path.exists(absolute_path):
            error_msg = f"File not found: {file_path}"
            logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "error_type": "file_not_found",
            }
    except Exception as e:
        error_msg = f"Error accessing file: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "message": error_msg,
            "error_type": "file_access_error",
        }

    # Track each step of the pipeline
    pipeline_steps = {
        "text_extraction": False,
        "xml_conversion": False,
        "xml_parsing": False,
        "profile_update": False,
    }

    # Variable to hold XML content, initialized as None to handle errors properly
    xml_content: str | None = None

    try:
        # Step 1: Extract text from PDF
        logger.info("Extracting text from %s", os.path.basename(absolute_path))
        try:
            raw_text = extract_text_from_pdf(absolute_path)
            if not raw_text:
                error_msg = "Failed to extract text from PDF (empty result)"
                logger.error(error_msg)
                return {
                    "success": False,
                    "message": error_msg,
                    "error_type": "text_extraction_error",
                    "pipeline_steps": pipeline_steps,
                }
            pipeline_steps["text_extraction"] = True
            logger.info("Successfully extracted %s characters from PDF", len(raw_text))
        except Exception as e:
            error_msg = f"Error extracting text from PDF: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "error_type": "text_extraction_error",
                "pipeline_steps": pipeline_steps,
                "exception": str(e),
            }

        # Step 2: Convert text to structured XML using LLM
        logger.info("Converting text to structured XML using LLM")
        try:
            xml_content = convert_text_to_xml(raw_text)
            pipeline_steps["xml_conversion"] = True
            logger.info("Successfully generated XML (%s characters)", len(xml_content))
        except ET.ParseError as e:
            error_msg = f"Error converting text to XML: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())

            # Only attempt to log and save XML if we have content
            result = {
                "success": False,
                "message": error_msg,
                "error_type": "xml_conversion_error",
                "pipeline_steps": pipeline_steps,
                "exception": str(e),
            }

            # Check if xml_content is available (set in llm_processor.py before validation error)
            if xml_content:
                # Use the centralized error reporting and save diagnostic file
                log_xml_error(e, xml_content)
                diagnostic_path = save_diagnostic_xml(
                    e, xml_content, absolute_path, "conversion"
                )

                # Include diagnostic path in result if available
                if diagnostic_path:
                    result["diagnostic_file"] = diagnostic_path

            return result

        except Exception as e:
            error_msg = f"Error converting text to XML: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "message": error_msg,
                "error_type": "xml_conversion_error",
                "pipeline_steps": pipeline_steps,
                "exception": str(e),
            }

        # At this point we can be sure xml_content is not None (if it was, we'd have returned from an exception handler)
        assert xml_content is not None, "XML content should not be None at this point"

        # Step 3: Parse XML into structured data
        logger.info("Parsing XML into structured data")
        try:
            parsed_data = parse_resume_xml(xml_content)
            pipeline_steps["xml_parsing"] = True
            logger.info("Successfully parsed XML data")
        except ET.ParseError as e:
            error_msg = f"Error parsing XML data: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())

            # Use the centralized error reporting and save diagnostic file
            log_xml_error(e, xml_content)
            diagnostic_path = save_diagnostic_xml(
                e, xml_content, absolute_path, "parsing"
            )

            # Include diagnostic path in result if available
            result = {
                "success": False,
                "message": error_msg,
                "error_type": "xml_parsing_error",
                "pipeline_steps": pipeline_steps,
                "exception": str(e),
            }

            if diagnostic_path:
                result["diagnostic_file"] = diagnostic_path

            return result

        except ValueError as e:
            error_msg = f"Error parsing XML data: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())

            # Save the XML with a note about the error
            try:
                base_filename = os.path.basename(absolute_path)
                diagnostic_path = os.path.join(
                    os.path.dirname(absolute_path),
                    f"{base_filename}.failed_xml_structure.xml",
                )

                # Add error information as XML comments
                diagnostic_xml = f"<!-- XML STRUCTURE ERROR: {str(e)} -->\n"
                diagnostic_xml += "<!-- This error indicates a problem with the XML structure, not the syntax -->\n"
                diagnostic_xml += xml_content

                with open(diagnostic_path, "w", encoding="utf-8") as f:
                    f.write(diagnostic_xml)
                logger.info("Saved problematic XML to %s", diagnostic_path)

                result = {
                    "success": False,
                    "message": error_msg,
                    "error_type": "xml_structure_error",
                    "pipeline_steps": pipeline_steps,
                    "exception": str(e),
                    "diagnostic_file": diagnostic_path,
                }

                return result

            except Exception as save_error:
                logger.warning("Could not save diagnostic XML file: %s", save_error)

                return {
                    "success": False,
                    "message": error_msg,
                    "error_type": "xml_structure_error",
                    "pipeline_steps": pipeline_steps,
                    "exception": str(e),
                }

        except Exception as e:
            error_msg = f"Error parsing XML data: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "message": error_msg,
                "error_type": "xml_parsing_error",
                "pipeline_steps": pipeline_steps,
                "exception": str(e),
            }

        # Step 4: Update profile with parsed data
        logger.info("Updating profile for user %s", profile.user.username)
        try:
            update_success = update_profile(profile, parsed_data, xml_content)
            if not update_success:
                error_msg = "Failed to update profile with extracted data"
                logger.error(error_msg)
                return {
                    "success": False,
                    "message": error_msg,
                    "error_type": "profile_update_error",
                    "pipeline_steps": pipeline_steps,
                }
            pipeline_steps["profile_update"] = True
            logger.info("Successfully updated profile")
        except Exception as e:
            error_msg = f"Error updating profile: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "error_type": "profile_update_error",
                "pipeline_steps": pipeline_steps,
                "exception": str(e),
            }

        # Clean up temp file
        try:
            default_storage.delete(file_path)
        except Exception as e:
            # Log but don't fail the overall process for cleanup errors
            logger.warning("Error cleaning up temporary file: %s", str(e))

        return {
            "success": True,
            "message": "Resume processed successfully",
            "pipeline_steps": pipeline_steps,
            "profile_data": {
                "skills": profile.skills_list,
                "years_of_experience": profile.years_of_experience,
                "current_position": profile.current_position,
            },
        }

    except Exception as e:
        # This is a catch-all for unexpected errors
        error_msg = f"Unexpected error in resume processing pipeline: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "message": error_msg,
            "error_type": "unexpected_error",
            "pipeline_steps": pipeline_steps,
            "exception": str(e),
        }


async def process_resume_async(file_path: str, profile_id: int) -> dict[str, Any]:
    """
    Process a resume file asynchronously in a Django Q task.

    This is a wrapper around the synchronous function that handles the task context.

    Args:
        file_path: Path to the resume file
        profile_id: ID of the JobSeekerProfile to update

    Returns:
        Dictionary with task result
    """
    # Get the profile
    try:
        try:
            profile = JobSeekerProfile.objects.get(id=profile_id)
        except JobSeekerProfile.DoesNotExist:
            error_msg = f"Profile not found: id={profile_id}"
            logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "error_type": "profile_not_found",
            }

        # Process the resume
        return process_resume_sync(file_path, profile)

    except Exception as e:
        error_msg = f"Unexpected error in async resume processing: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "message": error_msg,
            "error_type": "async_task_error",
            "exception": str(e),
        }
