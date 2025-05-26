"""
Task for analyzing candidate matches using LLM.

This module contains the Celery task for generating detailed analysis
of why a candidate is a good match for a job opening.
"""

import logging
from typing import Any, Iterable, cast

from celery import shared_task
from django.apps import apps
from django.conf import settings
from promptdown import StructuredPrompt

from apps.matching.tasks.common import get_openai_client

# Setup logging
logger = logging.getLogger(__name__)


@shared_task(name="apps.matching.tasks.analyze_candidate_match")
def analyze_candidate_match(candidate_match_id: int) -> dict[str, Any]:
    """
    Analyze a candidate match using LLM to generate detailed analysis.

    This task takes a CandidateMatch and uses an LLM to generate:
    1. A detailed analysis of why the job and candidate are a good match
    2. A headline summarizing why they're a good match

    Args:
        candidate_match_id: ID of the CandidateMatch to analyze

    Returns:
        dict: Result containing status and analysis data
    """
    try:
        CandidateMatch = apps.get_model("matching", "CandidateMatch")

        try:
            candidate_match = CandidateMatch.objects.select_related(
                "job_opening", "talent_sheet", "talent_sheet__job_seeker"
            ).get(id=candidate_match_id)
        except CandidateMatch.DoesNotExist:
            logger.error(
                "CandidateMatch with id %s does not exist.", candidate_match_id
            )
            return {
                "status": "error",
                "message": f"CandidateMatch with id {candidate_match_id} does not exist",
            }

        # Skip if already analyzed
        if candidate_match.is_analyzed:
            logger.info(
                "CandidateMatch %s is already analyzed, skipping", candidate_match_id
            )
            return {
                "status": "skipped",
                "message": f"CandidateMatch {candidate_match_id} is already analyzed",
                "candidate_match_id": candidate_match_id,
            }

        # Get OpenAI client
        client = get_openai_client()
        if client is None:
            logger.error("OpenAI client unavailable; missing API key")
            return {
                "status": "error",
                "message": "OpenAI client unavailable; missing API key",
                "candidate_match_id": candidate_match_id,
            }

        # Load the prompt
        import os

        prompt_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "prompts",
            "analyze_candidate_match.prompt.md",
        )

        if not os.path.exists(prompt_path):
            logger.error("Prompt file not found at path: %s", prompt_path)
            return {
                "status": "error",
                "message": "Prompt file not found",
                "candidate_match_id": candidate_match_id,
            }

        try:
            structured_prompt = StructuredPrompt.from_promptdown_file(prompt_path)

            # Prepare the data for the prompt
            job_opening = candidate_match.job_opening
            talent_sheet = candidate_match.talent_sheet
            job_seeker = talent_sheet.job_seeker

            # Get candidate name
            if job_seeker.user_owner:
                candidate_name = job_seeker.user_owner.get_full_name()
            else:
                candidate_name = job_seeker.candidate_name or "Candidate"

            # Prepare job opening details
            job_details = f"""
Job Title: {job_opening.title}
Company: {job_opening.company}
Location: {job_opening.location}

Job Description:
{job_opening.description}

Required Skills: {job_opening.required_skills or 'Not specified'}
Soft Skills: {job_opening.soft_skills or 'Not specified'}
Required Qualifications: {job_opening.required_qualifications or 'Not specified'}
Responsibilities: {job_opening.responsibilities or 'Not specified'}
Daily Tasks: {job_opening.daily_tasks or 'Not specified'}
Performance Expectations: {job_opening.performance_expectations or 'Not specified'}
Experience Required: {job_opening.experience_required or 'Not specified'}
Salary Range: ${job_opening.salary_min or 0:,.0f} - ${job_opening.salary_max or 0:,.0f}
            """.strip()

            # Prepare talent sheet details
            talent_details = f"""
Candidate Name: {candidate_name}
Personal Tagline: {job_seeker.personal_tagline or 'Not specified'}

Promotional Summary:
{talent_sheet.promotional_blurb or 'Not available'}

Experience Overview:
{talent_sheet.experience_overview or 'Not available'}

Skills: {job_seeker.skills or 'Not specified'}

Qualifications:
{talent_sheet.qualifications or 'Not available'}

Ideal Roles: {talent_sheet.ideal_roles or 'Not specified'}

Years of Experience: {job_seeker.years_of_experience or 0}
Salary Expectation: ${talent_sheet.salary_min or 0:,.0f} minimum
            """.strip()

            # Apply template values
            structured_prompt.apply_template_values(
                {
                    "candidate_name": candidate_name,
                    "job_details": job_details,
                    "talent_details": talent_details,
                }
            )

            # Get messages for the API call
            messages = structured_prompt.to_chat_completion_messages()

        except Exception as e:
            logger.error("Error preparing prompt: %s", str(e))
            return {
                "status": "error",
                "message": f"Error preparing prompt: {str(e)}",
                "candidate_match_id": candidate_match_id,
            }

        # Call OpenAI API
        try:
            logger.info("Sending candidate match data to LLM for analysis")

            response = client.chat.completions.create(
                model=settings.MATCHING_ANALYSIS_MODEL,
                messages=cast(Iterable[Any], messages),
                timeout=60,
            )

            # Extract response content
            response_content = response.choices[0].message.content
            if not response_content:
                raise ValueError("Empty response from LLM")

            # Parse the XML response using common utilities
            from apps.core.utils.xml_processing import (
                extract_element_text,
                parse_llm_xml_response,
            )

            try:
                root = parse_llm_xml_response(
                    response_content,
                    expected_elements=["summary", "analysis"],
                    expected_root="match_analysis",
                )

                # Extract summary and analysis using safe extraction
                match_summary = extract_element_text(root, "summary")
                match_analysis = extract_element_text(root, "analysis")

                if not match_summary or not match_analysis:
                    raise ValueError("Empty summary or analysis in LLM response")

                # Validate and truncate summary to fit database constraints
                if len(match_summary) > 255:
                    logger.warning(
                        "Summary too long (%d chars), truncating to 255 characters",
                        len(match_summary),
                    )
                    match_summary = match_summary[:252] + "..."

            except Exception as e:
                logger.error("Failed to parse LLM response: %s", str(e))
                return {
                    "status": "error",
                    "message": f"Failed to parse LLM response: {str(e)}",
                    "candidate_match_id": candidate_match_id,
                }

            # Update the candidate match
            candidate_match.match_summary = match_summary
            candidate_match.match_analysis = match_analysis
            candidate_match.is_analyzed = True
            candidate_match.save(
                update_fields=["match_summary", "match_analysis", "is_analyzed"]
            )

            logger.info(
                "Successfully analyzed candidate match %s for %s",
                candidate_match_id,
                candidate_name,
            )

            return {
                "status": "success",
                "message": "Match analysis completed successfully",
                "candidate_match_id": candidate_match_id,
                "match_summary": match_summary,
                "match_analysis": match_analysis,
            }

        except Exception as e:
            logger.error("Error calling OpenAI API: %s", str(e), exc_info=True)
            return {
                "status": "error",
                "message": f"Error calling OpenAI API: {str(e)}",
                "candidate_match_id": candidate_match_id,
            }

    except Exception as e:
        logger.error(
            "Error analyzing candidate match %s: %s",
            candidate_match_id,
            str(e),
            exc_info=True,
        )
        return {
            "status": "error",
            "message": f"Error analyzing candidate match: {str(e)}",
            "candidate_match_id": candidate_match_id,
        }
