"""
Recommendation utilities for job seekers.

This package contains utilities for generating recommendations,
taglines, and insights for job seekers.
"""

from apps.job_seekers.utils.recommendation.llm_processor import (
    generate_personal_tagline,
)

__all__ = ["generate_personal_tagline"]
