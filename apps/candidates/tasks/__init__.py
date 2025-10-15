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
from apps.resume_processing.tasks.cleanup_tasks import (
    cleanup_resume_processing_progress,
)
from apps.resume_processing.tasks.resume_processing_tasks import (
    handle_resume_upload_task,
    save_resume_file,
)

__all__ = [
    "save_resume_file",
    "handle_resume_upload_task",
    "cleanup_resume_processing_progress",
    "resume_processing_completed",
    "generate_role_recommendations",
    "generate_personal_tagline",
    "generate_profile_enrichment_task",
    "process_resume_for_pool",
    "cleanup_temp_resume_file",
]

