"""
Compatibility wrapper around the candidate resume pipeline.

Historically the resume-processing package exposed ``process_resume`` that
operated on ``JobSeekerProfile`` records.  The product now uses
``CandidateProfile`` exclusively, so this module forwards calls to the unified
candidate pipeline while preserving the import path used by legacy code.
"""

from __future__ import annotations

from typing import Any, cast

from apps.candidates.models import CandidateProfile
from apps.candidates.services.resume_pipeline import process_resume as _candidate_process_resume


def process_resume(
    file_path: str,
    profile: CandidateProfile,
    task_id: str | None = None,
) -> dict[str, Any]:
    """
    Delegate to the CandidateProfile-aware resume pipeline.

    Args:
        file_path: Absolute or storage-relative path to the resume file.
        profile: ``CandidateProfile`` instance that should be enriched.
        task_id: Optional Celery task identifier for progress tracking.
    """
    if not isinstance(profile, CandidateProfile):
        raise TypeError(
            "process_resume expects a CandidateProfile instance; "
            f"received {type(profile)!r}"
        )

    return cast(
        dict[str, Any],
        _candidate_process_resume(file_path=file_path, profile=profile, task_id=task_id),
    )
