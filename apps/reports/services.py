"""
Service functions for generating reports from candidate match data.

This module provides functions to generate CSV and PDF reports for recruiters
based on candidate matches for job openings.
"""

import csv
import io
from datetime import datetime

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
            "candidate_match__talent_sheet",
            "candidate_match__talent_sheet__job_seeker",
            "candidate_match__talent_sheet__job_seeker__user_owner",
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
    for rank, shortlisted_match in enumerate(shortlisted_matches, 1):
        match = shortlisted_match.candidate_match
        talent_sheet = match.talent_sheet
        job_seeker = talent_sheet.job_seeker
        user = job_seeker.user_owner

        # Get candidate name and contact info using the same logic as the UI
        if user:
            full_name = user.get_full_name()
            email = user.email
        else:
            # For pool-owned candidates, use the parsed candidate_name
            full_name = job_seeker.candidate_name or f"Candidate {job_seeker.pk}"
            email = ""

        # Convert skills from newline-separated to comma-separated
        skills = ""
        if talent_sheet.skills:
            skills_list = [
                s.strip() for s in talent_sheet.skills.splitlines() if s.strip()
            ]
            skills = ", ".join(skills_list)

        writer.writerow(
            [
                job_seeker.pk,
                full_name,
                email,
                job_seeker.phone or "",
                job_seeker.most_recent_title or "",
                job_seeker.location or "",
                job_seeker.years_of_experience or "",
                skills,
                f"{float(match.holistic_score) * 100:.1f}%",
                f"{float(match.skills_score) * 100:.1f}%",
                f"{float(match.experience_score) * 100:.1f}%",
                f"{float(match.qualifications_score) * 100:.1f}%",
                f"{float(match.wildcard_score) * 100:.1f}%",
                match.match_summary or "",
                "",  # recruiter_notes - empty for now, could be added later
            ]
        )

    return buffer.getvalue().encode("utf-8")


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
            "candidate_match__talent_sheet",
            "candidate_match__talent_sheet__job_seeker",
            "candidate_match__talent_sheet__job_seeker__user_owner",
        )
        .order_by("-created_at")
    )

    if limit:
        shortlisted_matches = shortlisted_matches[:limit]

    # Prepare context data for template
    candidates = []
    for rank, shortlisted_match in enumerate(shortlisted_matches, 1):
        match = shortlisted_match.candidate_match
        talent_sheet = match.talent_sheet
        job_seeker = talent_sheet.job_seeker
        user = job_seeker.user_owner

        # Get candidate name using the same logic as the UI
        if user:
            full_name = user.get_full_name()
            email = user.email
        else:
            # For pool-owned candidates, use the parsed candidate_name
            full_name = job_seeker.candidate_name or f"Candidate {job_seeker.pk}"
            email = ""

        # Parse skills into a list
        skills_list = []
        if talent_sheet.skills:
            skills_list = [
                s.strip() for s in talent_sheet.skills.splitlines() if s.strip()
            ]

        # Create skills matrix comparing job requirements to candidate skills
        required_skills = job.required_skills_list
        skills_matrix = []
        for req_skill in required_skills:
            has_skill = any(
                req_skill.lower() in candidate_skill.lower()
                for candidate_skill in skills_list
            )
            skills_matrix.append({"skill": req_skill, "has_skill": has_skill})

        candidates.append(
            {
                "rank": rank,
                "name": full_name,
                "email": email,
                "phone": job_seeker.phone or "",
                "current_title": job_seeker.most_recent_title or "",
                "location": job_seeker.location or "",
                "years_experience": job_seeker.years_of_experience or "",
                "holistic_score": match.holistic_rating,
                "skills_score": match.skills_rating,
                "experience_score": match.experience_rating,
                "qualifications_score": match.qualifications_rating,
                "wildcard_score": match.wildcard_rating,
                "tagline": match.match_summary or talent_sheet.personal_tagline or "",
                "promotional_blurb": talent_sheet.promotional_blurb,
                "experience_overview": talent_sheet.experience_overview,
                "qualifications": talent_sheet.qualifications,
                "skills_list": skills_list,
                "skills_matrix": skills_matrix,
                "match_analysis": match.match_analysis or "",
            }
        )

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
