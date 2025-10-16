"""
Celery task exports for the candidates app.
"""

from apps.candidates.tasks.personal_tagline_tasks import generate_personal_tagline
from apps.candidates.tasks.pool_tasks import (
    cleanup_temp_resume_file,
    process_resume_for_pool,
)
from apps.candidates.tasks.post_resume_processing_tasks import (
    resume_processing_completed,
)
from apps.candidates.tasks.profile_enrichment_tasks import (
    generate_profile_enrichment_task,
)
from apps.candidates.tasks.recommendation_tasks import generate_role_recommendations

__all__ = [
    "resume_processing_completed",
    "generate_role_recommendations",
    "generate_personal_tagline",
    "generate_profile_enrichment_task",
    "process_resume_for_pool",
    "cleanup_temp_resume_file",
]
