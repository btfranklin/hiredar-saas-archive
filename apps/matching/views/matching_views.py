"""
Views for matching functionality.

This module provides API endpoints for matching talent sheets with job openings.
"""

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from apps.matching.match import match_job_to_talents, match_talent_to_jobs


@require_GET
@login_required
def match_talent_api(request, talent_id: int) -> JsonResponse:
    """
    API endpoint to match a TalentSheet against all JobOpenings.

    Args:
        request: The HTTP request
        talent_id: The ID of the TalentSheet to match

    Returns:
        JsonResponse with match results
    """
    try:
        top_k = int(request.GET.get("top_k", 10))
        results = match_talent_to_jobs(talent_id, top_k=top_k)
        return JsonResponse({"status": "success", "matches": results})
    except Exception as e:
        return JsonResponse({"status": "error", "error": str(e)}, status=500)


@require_GET
@login_required
def match_job_api(request, job_id: int) -> JsonResponse:
    """
    API endpoint to match a JobOpening against all TalentSheets.

    Args:
        request: The HTTP request
        job_id: The ID of the JobOpening to match

    Returns:
        JsonResponse with match results
    """
    try:
        top_k = int(request.GET.get("top_k", 10))
        results = match_job_to_talents(job_id, top_k=top_k)
        return JsonResponse({"status": "success", "matches": results})
    except Exception as e:
        return JsonResponse({"status": "error", "error": str(e)}, status=500)
