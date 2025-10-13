"""
Job processing pipeline orchestration.

This module defines the complete job processing pipeline for converting
text job descriptions into structured JobOpening objects.
"""

import logging
import time
from typing import Any

from apps.recruiters.models import (
    JobOpening,
    JobOpeningProcessingTask,
    RecruiterProfile,
)
from apps.recruiters.services.job_processing.llm_processor import convert_text_to_xml
from apps.recruiters.services.job_processing.xml_parser import create_job_opening_from_xml

# Setup logging
logger = logging.getLogger(__name__)


def process_job_description(
    task_id: str,
    job_title: str,
    job_description: str,
    recruiter_profile: RecruiterProfile,
) -> dict[str, Any]:
    """
    Process a job description text and create a JobOpening.

    This function orchestrates the complete job processing pipeline:
    1. Prepare the job description text
    2. Convert to structured XML using LLM
    3. Parse XML to create a JobOpening

    Args:
        task_id: The task ID for tracking progress
        job_title: The title of the job
        job_description: The full text description of the job
        recruiter_profile: The RecruiterProfile instance

    Returns:
        Dictionary with processing results
    """
    start_time = time.time()
    pipeline_steps = []
    xml_data: str | None = None
    job_opening: JobOpening | None = None

    try:
        # Get the task object
        task = JobOpeningProcessingTask.objects.get(task_id=task_id)

        # Update task status to processing
        task.status = "processing"
        task.save()
        pipeline_steps.append("initialized")

        # Step 1: Pre-process the text (clean and prepare)
        task.update_progress(
            "Pre-processing text", 10, "Preparing job description text for processing"
        )
        # In the future, we could add text preprocessing here if needed
        pipeline_steps.append("text_preprocessed")

        # Step 2: Convert to XML using LLM
        task.update_progress(
            "Converting to structured format", 30, "Analyzing job description with AI"
        )
        xml_data = convert_text_to_xml(job_title, job_description)

        if not xml_data:
            task.mark_failed("Failed to generate structured data from job description")
            return {
                "status": "failed",
                "message": "LLM processing failed",
                "pipeline_steps": pipeline_steps,
            }

        pipeline_steps.append("xml_generated")

        # Step 3: Parse XML and create JobOpening
        task.update_progress(
            "Creating job opening",
            70,
            "Creating structured job opening from processed data",
        )
        job_opening = create_job_opening_from_xml(
            xml_data, recruiter_profile, original_description=job_description
        )

        if not job_opening:
            task.mark_failed("Failed to create job opening from structured data")
            return {
                "status": "failed",
                "message": "Job opening creation failed",
                "pipeline_steps": pipeline_steps,
            }

        pipeline_steps.append("job_opening_created")

        # Step 4: Finalize
        task.mark_completed(job_opening.pk, xml_data)
        pipeline_steps.append("completed")

        # Calculate processing time
        processing_time = time.time() - start_time
        logger.info(
            "Job description processing completed successfully in %.2fs",
            processing_time,
        )

        return {
            "status": "completed",
            "job_opening_id": job_opening.pk,
            "xml_data": xml_data,
            "pipeline_steps": pipeline_steps,
            "processing_time": processing_time,
        }

    except Exception as e:
        logger.error("Error processing job description: %s", str(e))

        # Try to update the task status if possible
        try:
            task = JobOpeningProcessingTask.objects.get(task_id=task_id)
            task.mark_failed(f"Error: {str(e)}")
        except Exception as task_error:
            logger.error("Error updating task status: %s", str(task_error))

        return {"status": "failed", "message": str(e), "pipeline_steps": pipeline_steps}
