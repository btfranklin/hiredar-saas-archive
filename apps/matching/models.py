"""
Models for the matching app.

This module defines the models for handling candidate matching.
"""

from decimal import Decimal

from django.db import models


class CandidateMatch(models.Model):
    """
    Model for matching talent sheets to job openings.

    Represents a potential match between a talent sheet and job opening,
    with metadata about the quality of the match and its current status.

    Similarity scores from Pinecone are stored directly (0-1 range).
    Rating properties convert these to a 1-10 scale for display.
    """

    job_opening = models.ForeignKey(
        "recruiters.JobOpening",
        on_delete=models.CASCADE,
        related_name="candidate_matches",
    )
    talent_sheet = models.ForeignKey(
        "job_seekers.TalentSheet",
        on_delete=models.CASCADE,  # When a talent sheet is deleted, delete the match
        related_name="job_matches",
    )
    holistic_score = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal("0.0"),
        help_text="Holistic similarity score (0-1)",
    )
    skills_score = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal("0.0"),
        help_text="Skills similarity score (0-1)",
    )
    experience_score = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal("0.0"),
        help_text="Experience similarity score (0-1)",
    )
    wildcard_score = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal("0.0"),
        help_text="Wildcard similarity score (0-1)",
    )
    qualifications_score = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal("0.0"),
        help_text="Qualifications similarity score (0-1)",
    )
    status = models.CharField(
        max_length=20,
        choices=(
            ("identified", "Identified"),
            ("open", "Open"),
            ("contacted", "Contacted"),
            ("candidate_interested", "Candidate Interested"),
            ("candidate_declined", "Candidate Declined"),
            ("recruiter_rejected", "Recruiter Rejected"),
        ),
        default="identified",
    )
    is_analyzed = models.BooleanField(
        default=False,
        help_text="Whether this match has been analyzed by AI",
    )
    match_summary = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="A headline summarizing why this is a good match",
    )
    match_analysis = models.TextField(
        blank=True,
        null=True,
        help_text="Detailed analysis of why this job and candidate match",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "matching"
        # Ensure we don't have duplicate matches for the same job opening and talent sheet
        unique_together = ["job_opening", "talent_sheet"]

    def __str__(self) -> str:
        # Dynamically determine the active lens for display purposes
        current_type = getattr(self, "match_type", "holistic")

        match_type_display = {
            "holistic": "Holistic Match",
            "skills": "Skills Match",
            "experience": "Experience Match",
            "wildcard": "Wildcard Match",
            "qualifications": "Qualifications Match",
        }.get(current_type, current_type)

        # Access job seeker name through talent sheet and user_owner
        job_seeker_profile = self.talent_sheet.job_seeker
        job_owner = job_seeker_profile.user_owner
        job_seeker_name = (
            job_owner.get_full_name()
            if job_owner
            else f"Profile {job_seeker_profile.pk}"
        )
        return (
            f"{job_seeker_name} - {self.job_opening} "
            f"({self.get_score_for_type():.2f}, {match_type_display})"
        )

    @property
    def holistic_rating(self) -> int:
        """Convert holistic score to a 1-10 integer rating."""
        return self._score_to_rating(self.holistic_score)

    @property
    def skills_rating(self) -> int:
        """Convert skills score to a 1-10 integer rating."""
        return self._score_to_rating(self.skills_score)

    @property
    def experience_rating(self) -> int:
        """Convert experience score to a 1-10 integer rating."""
        return self._score_to_rating(self.experience_score)

    @property
    def wildcard_rating(self) -> int:
        """Convert wildcard score to a 1-10 integer rating."""
        return self._score_to_rating(self.wildcard_score)

    @property
    def qualifications_rating(self) -> int:
        """Convert qualifications score to a 1-10 integer rating."""
        return self._score_to_rating(self.qualifications_score)

    def _score_to_rating(self, score: Decimal) -> int:
        """
        Convert a similarity score (0-1) to a rating (1-10).

        This uses a non-linear scale to better differentiate between scores,
        as similarity scores tend to cluster in the upper range.
        """
        # Convert score to float
        float_score = float(score)

        # Ensure minimum rating is 1 and maximum is 10
        if float_score < 0.5:
            # Scores below 0.5 are considered poor matches
            return max(1, round(float_score * 10))
        else:
            # Scores 0.5 and above use a different scale to spread out the ratings
            # For example: 0.5 -> 5, 0.65 -> 7, 0.8 -> 9, 0.95+ -> 10
            return min(10, 5 + round((float_score - 0.5) * 10))

    def get_score_for_type(self) -> Decimal:
        """Get the score for the current match type."""
        # Dynamically determine the active lens for display purposes
        current_type = getattr(self, "match_type", "holistic")

        if current_type == "holistic":
            return self.holistic_score
        elif current_type == "skills":
            return self.skills_score
        elif current_type == "experience":
            return self.experience_score
        elif current_type == "wildcard":
            return self.wildcard_score
        elif current_type == "qualifications":
            return self.qualifications_score
        return Decimal("0.0")  # Fallback

    def get_rating_for_type(self) -> int:
        """Get the rating for the current match type."""
        # Dynamically determine the active lens for display purposes
        current_type = getattr(self, "match_type", "holistic")

        if current_type == "holistic":
            return self.holistic_rating
        elif current_type == "skills":
            return self.skills_rating
        elif current_type == "experience":
            return self.experience_rating
        elif current_type == "wildcard":
            return self.wildcard_rating
        elif current_type == "qualifications":
            return self.qualifications_rating
        return 1  # Fallback

    def get_all_match_ratings(self):
        """
        Get ratings for all match types for this talent sheet and job.

        Returns:
            A list of tuples containing (match_type, match_type_display, rating)
        """
        return [
            ("holistic", "Holistic", self.holistic_rating),
            ("skills", "Skills", self.skills_rating),
            ("experience", "Experience", self.experience_rating),
            ("qualifications", "Qualifications", self.qualifications_rating),
            ("wildcard", "Wildcard", self.wildcard_rating),
        ]


class ShortlistedMatch(models.Model):
    """A candidate match that a recruiter has added to their shortlist for a job opening."""

    job_opening = models.ForeignKey(
        "recruiters.JobOpening",
        on_delete=models.CASCADE,
        related_name="shortlisted_matches",
    )
    candidate_match = models.ForeignKey(
        "matching.CandidateMatch",
        on_delete=models.CASCADE,
        related_name="shortlists",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "matching"
        # Only allow each candidate match to be shortlisted once per job opening
        unique_together = ["job_opening", "candidate_match"]

    def __str__(self) -> str:  # noqa: D401 – admin friendly string
        job_title = self.job_opening.title
        seeker_name = (
            self.candidate_match.talent_sheet.job_seeker.user_owner.get_full_name()
            if self.candidate_match.talent_sheet.job_seeker.user_owner
            else f"Profile {self.candidate_match.talent_sheet.job_seeker.pk}"
        )
        return f"Shortlist • {seeker_name} for {job_title}"

    @property
    def holistic_rating(self) -> int:
        """Expose the holistic rating directly on the shortlist object for convenience."""
        return self.candidate_match.holistic_rating
