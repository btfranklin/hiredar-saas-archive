"""
Service-layer helpers for the resume_processing app.

Modules in this package orchestrate the resume ingestion pipeline, including
raw text extraction, LLM conversions, and structured XML parsing.
"""

from . import resume_processing

__all__ = [
    "resume_processing",
]
