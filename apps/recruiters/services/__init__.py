"""
Service-layer helpers for the recruiters app.

Modules in this package manage recruiter-facing workflows such as job ingestion
and downstream automation.
"""

from . import job_processing

__all__ = [
    "job_processing",
]
