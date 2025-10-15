"""
Follow-up tasks that run after candidate resume ingestion completes.
"""

from __future__ import annotations

import logging
from typing import Any

from celery import shared_task

from apps.candidates.models import CandidateProfile
from apps.candidates.tasks.profile_enrichment_tasks import (
    generate_profile_enrichment_task,
)
from apps.candidates.tasks.recommendation_tasks import generate_role_recommendations
from apps.core.tasks import safe_async_task
from apps.resume_processing.tasks.cleanup_tasks import (
    cleanup_resume_processing_progress,
)

logger = logging.getLogger(__name__)
async_task = safe_async_task


@shared_task(
    name="apps.candidates.tasks.post_resume_processing_tasks.resume_processing_completed"
)
def resume_processing_completed(
    result: dict[str, Any] | None = None,
    profile_id: int | None = None,
) -> dict[str, Any]:
    """
    Trigger downstream enrichment once resume processing succeeds.
    """
    logger.info("Candidate resume processing completion task triggered")

    if isinstance(result, dict):
        if result.get("status") != "success":
            logger.error(
                "Upstream resume processing reported non-success status: %s",
                result.get("status"),
            )
            return {
                "status": "error",
                "message": "Previous task failed, skipping follow-up tasks",
                "result": result,
            }
        profile_id = profile_id or result.get("profile_id")
    elif result is None and profile_id is None:
        return {"status": "error", "message": "No result or profile_id provided"}

    if profile_id is None:
        return {"status": "error", "message": "Cannot determine profile ID"}

    try:
        profile = CandidateProfile.objects.get(pk=profile_id)
    except CandidateProfile.DoesNotExist:
        error_msg = f"CandidateProfile with ID {profile_id} does not exist"
        logger.error(error_msg)
        return {"status": "error", "message": error_msg, "profile_id": profile_id}

    async_task(
        generate_role_recommendations,
        profile.pk,
        task_name=f"candidate_role_recommendations_{profile.pk}",
    )

    async_task(
        generate_profile_enrichment_task,
        profile.pk,
        task_name=f"candidate_profile_enrichment_{profile.pk}",
    )

    try:
        cleanup_resume_processing_progress()
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Error running resume processing cleanup: %s", exc)

    return {
        "status": "success",
        "message": "Candidate follow-up tasks queued",
        "profile_id": profile.pk,
    }

