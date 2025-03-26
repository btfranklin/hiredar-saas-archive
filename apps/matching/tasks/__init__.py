"""
Task functions for the matching app.

This package contains task functions for embedding and matching functionality.
"""

# Re-export all task functions from the tasks submodules
from apps.matching.tasks.job_opening_tasks import (
    create_job_opening_embeddings,
    remove_job_opening_embeddings,
)
from apps.matching.tasks.talent_sheet_tasks import (
    create_talent_sheet_embeddings,
    remove_talent_sheet_embeddings,
)

__all__ = [
    "create_job_opening_embeddings",
    "remove_job_opening_embeddings",
    "create_talent_sheet_embeddings",
    "remove_talent_sheet_embeddings",
]
