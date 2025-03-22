"""
Task functions for the matching app.

This package contains task functions for embedding and matching functionality.
"""

# Re-export all task functions from the tasks submodules
from apps.matching.tasks.job_opening_tasks import (
    process_job_opening,
    remove_job_opening_embeddings,
)
from apps.matching.tasks.talent_sheet_tasks import (
    process_talent_sheet,
    remove_talent_sheet_embeddings,
)

__all__ = [
    "process_job_opening",
    "remove_job_opening_embeddings",
    "process_talent_sheet",
    "remove_talent_sheet_embeddings",
]
