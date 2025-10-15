"""
Views for matching functionality.

This module provides API endpoints for matching candidate profiles with job openings.
"""

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from apps.matching.core.matching import match_candidate_to_jobs, match_job_to_candidates


@require_GET
@login_required
def match_candidate_api(request, candidate_id: int) -> JsonResponse:
    """
    API endpoint to match a CandidateProfile against all JobOpenings.

    Args:
        request: The HTTP request
        candidate_id: The ID of the CandidateProfile to match

    Returns:
        JsonResponse with match results
    """
    try:
        top_k = int(request.GET.get("top_k", 10))
        results = match_candidate_to_jobs(candidate_id, top_k=top_k)
        return JsonResponse({"status": "success", "matches": results})
    except Exception as e:
        return JsonResponse({"status": "error", "error": str(e)}, status=500)


@require_GET
@login_required
def match_job_api(request, job_id: int) -> JsonResponse:
    """
    API endpoint to match a JobOpening against all candidate profiles.

    Args:
        request: The HTTP request
        job_id: The ID of the JobOpening to match

    Returns:
        JsonResponse with match results
    """
    try:
        top_k = int(request.GET.get("top_k", 10))
        results = match_job_to_candidates(job_id, top_k=top_k)
        return JsonResponse({"status": "success", "matches": results})
    except Exception as e:
        return JsonResponse({"status": "error", "error": str(e)}, status=500)
