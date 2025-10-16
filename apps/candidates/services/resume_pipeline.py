"""Resume processing pipeline specialized for CandidateProfile records."""

from __future__ import annotations

import logging
import os
import tempfile
import time
import traceback
import xml.etree.ElementTree as ET
from typing import Any

from django.conf import settings
from django.core.files.storage import default_storage

from apps.candidates.models import CandidateProfile
from apps.candidates.services.profile_updater import (
    generate_and_save_personal_tagline,
    update_profile_fields,
)
from apps.resume_processing.models import ResumeProcessingTaskProgress
from apps.resume_processing.services.resume_processing.extraction import extract_text
from apps.resume_processing.services.resume_processing.llm_processor import (
    convert_text_to_xml,
)
from apps.resume_processing.services.resume_processing.xml_error_reporting import (
    log_xml_error,
    save_diagnostic_xml,
)
from apps.resume_processing.services.resume_processing.xml_parser import (
    parse_resume_xml,
)

logger = logging.getLogger(__name__)


def process_resume(
    file_path: str,
    profile: CandidateProfile,
    task_id: str | None = None,
) -> dict[str, Any]:
    """
    Process a résumé file and enrich a CandidateProfile with the result.
    """
    pipeline_steps: list[str] = []
    resume_text: str | None = None
    xml_content: str | None = None
    parsed_data: dict[str, Any] | None = None
    start_time = time.time()
    temp_artifacts: list[str] = []

    profile_identifier = f"CandidateProfile #{profile.pk}"
    if profile.pool:
        profile_identifier += f" (Pool: {profile.pool.name})"

    logger.info("Starting candidate résumé processing for %s", profile_identifier)

    progress_tracker = None
    if task_id:
        try:
            progress_tracker = ResumeProcessingTaskProgress.objects.get(task_id=task_id)
            if progress_tracker.status == "pending":
                progress_tracker.status = "running"
                progress_tracker.message = "Processing résumé..."
                progress_tracker.save(update_fields=["status", "message"])
        except ResumeProcessingTaskProgress.DoesNotExist:
            logger.warning("Progress tracker not found for task_id: %s", task_id)
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Error initialising progress tracker: %s", exc)

    try:
        if os.path.isabs(file_path):
            abs_file_path = file_path
        else:
            try:
                abs_file_path = default_storage.path(file_path)
            except NotImplementedError:
                abs_candidate = os.path.join(settings.MEDIA_ROOT, file_path)
                if os.path.exists(abs_candidate):
                    abs_file_path = abs_candidate
                else:
                    logger.warning(
                        "Storage backend does not expose absolute path for %s",
                        file_path,
                    )
                    abs_file_path = file_path

        if not (os.path.exists(abs_file_path) and os.access(abs_file_path, os.R_OK)):
            logger.info(
                "Creating temporary local copy for inaccessible file: %s",
                abs_file_path,
            )
            with default_storage.open(file_path, "rb") as stored_file:
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=os.path.splitext(file_path)[1]
                ) as tmp:
                    tmp.write(stored_file.read())
                    abs_file_path = tmp.name
                    temp_artifacts.append(tmp.name)

        pipeline_steps.append("file_path_resolved")
        if progress_tracker:
            progress_tracker.mark_step_complete("file_path_resolved")

        resume_text = extract_text(abs_file_path)
        if not resume_text:
            error_msg = "Failed to extract any text from résumé"
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

        pipeline_steps.append("text_extracted")
        if progress_tracker:
            progress_tracker.mark_step_complete("text_extracted")

        xml_content = convert_text_to_xml(resume_text)
        pipeline_steps.append("xml_generated")
        if progress_tracker:
            progress_tracker.mark_step_complete("xml_generated")

        try:
            parsed_data = parse_resume_xml(xml_content)
            pipeline_steps.append("xml_parsed")
            if progress_tracker:
                progress_tracker.mark_step_complete("xml_parsed")
        except ET.ParseError as exc:  # pragma: no cover - difficult to simulate
            log_xml_error(exc, xml_content)
            diagnostic_path = save_diagnostic_xml(
                exc,
                xml_content,
                abs_file_path,
                "parsing",
            )
            if diagnostic_path:
                temp_artifacts.append(diagnostic_path)

            error_msg = f"Error parsing XML: {exc}"
            if progress_tracker:
                progress_tracker.status = "failed"
                progress_tracker.message = error_msg
                progress_tracker.save(update_fields=["status", "message"])
            return {
                "success": False,
                "message": error_msg,
                "error_type": "xml_parse_error",
                "pipeline_steps": pipeline_steps,
                "xml_content": xml_content,
            }

        if not update_profile_fields(profile, parsed_data):
            error_msg = "Failed to update candidate profile fields"
            if progress_tracker:
                progress_tracker.status = "failed"
                progress_tracker.message = error_msg
                progress_tracker.save(update_fields=["status", "message"])
            return {
                "success": False,
                "message": error_msg,
                "error_type": "profile_update_error",
                "pipeline_steps": pipeline_steps,
            }

        if not generate_and_save_personal_tagline(profile, xml_content, parsed_data):
            logger.warning(
                "Personal tagline generation failed for CandidateProfile %s",
                profile.pk,
            )

        pipeline_steps.append("profile_updated")
        if progress_tracker:
            progress_tracker.mark_step_complete("profile_updated")
            progress_tracker.status = "success"
            progress_tracker.message = "Résumé processed successfully"
            progress_tracker.save(update_fields=["status", "message"])

        elapsed = time.time() - start_time
        logger.info(
            "Completed candidate résumé processing for %s in %.2fs",
            profile_identifier,
            elapsed,
        )
        return {
            "success": True,
            "message": "Résumé processed successfully",
            "profile_id": profile.pk,
            "pipeline_steps": pipeline_steps,
            "profile_data": parsed_data,
            "resume_text_preview": resume_text[:200] if resume_text else "",
        }

    except Exception as exc:  # pragma: no cover - defensive
        logger.error(
            "Unexpected error in candidate resume pipeline: %s\n%s",
            exc,
            traceback.format_exc(),
        )
        if progress_tracker:
            progress_tracker.status = "failed"
            progress_tracker.message = str(exc)
            progress_tracker.save(update_fields=["status", "message"])
        return {
            "success": False,
            "message": str(exc),
            "error_type": "unexpected_error",
            "pipeline_steps": pipeline_steps,
        }
    finally:
        for artifact in temp_artifacts:
            try:
                os.unlink(artifact)
            except OSError:
                logger.debug("Failed to delete temporary artifact %s", artifact)
