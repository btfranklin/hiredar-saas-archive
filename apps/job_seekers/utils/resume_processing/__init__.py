"""
Resume processing utilities.

This package provides utilities for processing resume PDFs and
extracting structured information for job seeker profiles.
"""

from apps.job_seekers.utils.resume_processing.pipeline import process_resume

# Re-export the main function as a simple API
__all__ = ["process_resume"]
