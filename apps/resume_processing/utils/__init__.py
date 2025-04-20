"""
Resume processing utilities.

This package provides utilities for processing resume PDFs and
extracting structured information for job seeker profiles.
"""

from apps.resume_processing.utils.pipeline import process_resume

# Re-export the main function as a simple API
__all__ = ["process_resume"]
