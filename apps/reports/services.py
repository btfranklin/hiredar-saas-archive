"""
Service functions for generating reports from candidate match data.

This module provides functions to generate CSV and PDF reports for recruiters
based on candidate matches for job openings.
"""

import csv
import io
from datetime import datetime
from typing import Any

from django.template.loader import render_to_string
from weasyprint import HTML

from apps.matching.models import ShortlistedMatch
from apps.recruiters.models import JobOpening


def generate_csv(job: JobOpening, limit: int | None = None) -> bytes:
    """
    Generate a CSV report of shortlisted candidate matches for a job opening.

    Args:
        job: The JobOpening instance to generate a report for
        limit: Optional limit on number of candidates to include

    Returns:
        CSV data as bytes
    """
    # Get shortlisted matches ordered by creation date (most recent first)
    shortlisted_matches = (
        ShortlistedMatch.objects.filter(job_opening=job)
        .select_related(
            "candidate_match",
            "candidate_match__candidate_profile",
            "candidate_match__candidate_profile__pool",
        )
        .order_by("-created_at")
    )

    if limit:
        shortlisted_matches = shortlisted_matches[:limit]

    # Create CSV in memory
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    # Write header row
    writer.writerow(
        [
            "candidate_id",
            "full_name",
            "email",
            "phone",
            "current_title",
            "location",
            "years_experience_total",
            "skills",
            "match_score_overall",
            "score_by_skills",
            "score_by_experience",
            "score_by_qualifications",
            "score_by_wildcard",
            "ai_tagline",
            "recruiter_notes",
        ]
    )

    # Write data rows
    for shortlisted_match in shortlisted_matches:
        match = shortlisted_match.candidate_match
        candidate_profile = match.candidate_profile

        full_name = candidate_profile.display_name
        email = ""

        skills_list = candidate_profile.skills_list
        skills = ", ".join(skills_list) if skills_list else ""

        writer.writerow(
            [
                candidate_profile.pk,
                full_name,
                email,
                candidate_profile.phone or "",
                candidate_profile.most_recent_title or "",
                candidate_profile.location or "",
                candidate_profile.years_of_experience or "",
                skills,
                f"{float(match.holistic_score) * 100:.1f}%",
                f"{float(match.skills_score) * 100:.1f}%",
                f"{float(match.experience_score) * 100:.1f}%",
                f"{float(match.qualifications_score) * 100:.1f}%",
                f"{float(match.wildcard_score) * 100:.1f}%",
                match.match_summary or candidate_profile.personal_tagline or "",
                "",  # recruiter_notes - empty for now, could be added later
            ]
        )

    return buffer.getvalue().encode("utf-8")


def _build_candidate_entry(
    job: JobOpening, shortlisted_match: ShortlistedMatch, rank: int
) -> dict[str, Any]:
    """Construct the candidate payload used by the PDF export."""
    match = shortlisted_match.candidate_match
    candidate_profile = match.candidate_profile

    full_name = candidate_profile.display_name
    email = ""

    skills_list: list[str] = candidate_profile.skills_list

    required_skills = list(job.required_skills_list)
    skills_matrix = [
        {
            "skill": req_skill,
            "has_skill": any(
                req_skill.lower() in candidate_skill.lower()
                for candidate_skill in skills_list
            ),
        }
        for req_skill in required_skills
    ]

    return {
        "rank": rank,
        "name": full_name,
        "email": email,
        "phone": candidate_profile.phone or "",
        "current_title": candidate_profile.most_recent_title or "",
        "location": candidate_profile.location or "",
        "years_experience": candidate_profile.years_of_experience or "",
        "holistic_score": match.holistic_rating,
        "skills_score": match.skills_rating,
        "experience_score": match.experience_rating,
        "qualifications_score": match.qualifications_rating,
        "wildcard_score": match.wildcard_rating,
        "tagline": match.match_summary or candidate_profile.personal_tagline or "",
        "promotional_blurb": candidate_profile.promotional_blurb,
        "experience_overview": candidate_profile.experience_overview,
        "qualifications": candidate_profile.qualifications,
        "skills_list": skills_list,
        "skills_matrix": skills_matrix,
        "match_analysis": match.match_analysis or "",
    }


def generate_pdf(job: JobOpening, limit: int | None = None) -> bytes:
    """
    Generate a PDF report of shortlisted candidate matches for a job opening.

    Args:
        job: The JobOpening instance to generate a report for
        limit: Optional limit on number of candidates to include

    Returns:
        PDF data as bytes
    """
    # Get shortlisted matches ordered by creation date (most recent first)
    shortlisted_matches = (
        ShortlistedMatch.objects.filter(job_opening=job)
        .select_related(
            "candidate_match",
            "candidate_match__candidate_profile",
            "candidate_match__candidate_profile__pool",
        )
        .order_by("-created_at")
    )

    if limit:
        shortlisted_matches = shortlisted_matches[:limit]

    # Prepare context data for template
    candidates = [
        _build_candidate_entry(job, shortlisted_match, rank)
        for rank, shortlisted_match in enumerate(shortlisted_matches, 1)
    ]

    context = {
        "job": job,
        "candidates": candidates,
        "total_candidates": len(candidates),
        "generated_date": datetime.now().strftime("%B %d, %Y"),
        "recruiter_name": job.recruiter.user.get_full_name()
        or job.recruiter.user.email,
        "recruiter_email": job.recruiter.user.email,
    }

    # Render HTML template
    html_string = render_to_string("reports/candidate_slate.html", context)

    # Convert HTML to PDF
    html = HTML(string=html_string)
    pdf_bytes = html.write_pdf()

    if pdf_bytes is None:
        raise RuntimeError("Failed to generate PDF")

    return pdf_bytes


def get_export_filename(job: JobOpening, file_type: str) -> str:
    """
    Generate a filename for the export file.

    Args:
        job: The JobOpening instance
        file_type: Either 'csv' or 'pdf'

    Returns:
        Filename string
    """
    # Clean job title for filename
    clean_title = "".join(
        c for c in job.title if c.isalnum() or c in (" ", "-", "_")
    ).strip()
    clean_title = clean_title.replace(" ", "_")

    # Add date
    date_str = datetime.now().strftime("%Y%m%d")

    return f"hiredar_candidates_{clean_title}_{date_str}.{file_type}"
