"""
Signal handlers for matching app.

This module connects Django signals to task execution for matching operations.
"""

from celery import chain
from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.core.tasks import safe_async_task
from apps.matching.tasks.create_candidate_matches import (
    create_candidate_matches as create_matches_task,
)
from apps.matching.tasks.create_job_opening_embeddings import (
    create_job_opening_embeddings as create_job_embeddings_task,
)
from apps.matching.tasks.create_talent_sheet_embeddings import (
    create_talent_sheet_embeddings as create_talent_embeddings_task,
)
from apps.matching.tasks.match_talent_to_active_jobs import (
    match_talent_to_active_jobs as match_talent_task,
)
from apps.matching.tasks.remove_job_opening_embeddings import (
    remove_job_opening_embeddings,
)
from apps.matching.tasks.remove_job_opening_matches import remove_job_opening_matches
from apps.matching.tasks.remove_talent_sheet_embeddings import (
    remove_talent_sheet_embeddings,
)
from apps.matching.tasks.remove_talent_sheet_matches import remove_talent_sheet_matches

async_task = safe_async_task


@receiver(post_save, sender="recruiters.JobOpening")
def handle_job_opening_save(sender, instance, created, **kwargs):
    """
    Handle JobOpening save events.

    Process active job openings for embeddings, and remove embeddings
    and matches for inactive ones.

    Args:
        sender: The model class
        instance: The actual instance being saved
        created: A boolean; True if a new record was created
    """
    # Only process embeddings for active jobs
    if instance.status == "active":
        # Create embeddings and then create candidate matches using Celery chain
        transaction.on_commit(
            lambda: chain(
                create_job_embeddings_task.si(instance.id), create_matches_task.s()  # type: ignore[misc]
            ).apply_async(task_id=f"embed_and_match_job_{instance.id}")
        )
    else:
        # Remove embeddings and matches for inactive jobs
        def _cleanup_inactive():
            async_task(
                remove_job_opening_embeddings,
                instance.id,
                task_name=f"remove_job_embeddings_{instance.id}",
            )
            async_task(
                remove_job_opening_matches,
                instance.id,
                task_name=f"remove_job_matches_{instance.id}",
            )

        transaction.on_commit(_cleanup_inactive)


@receiver(post_delete, sender="recruiters.JobOpening")
def handle_job_opening_delete(sender, instance, **kwargs):
    """
    Handle JobOpening delete events.

    Remove embeddings and matches when a job opening is deleted.

    Args:
        sender: The model class
        instance: The actual instance being deleted
    """
    async_task(
        remove_job_opening_embeddings,
        instance.id,
        task_name=f"cleanup_job_embeddings_{instance.id}",
    )
    async_task(
        remove_job_opening_matches,
        instance.id,
        task_name=f"cleanup_job_matches_{instance.id}",
    )


@receiver(post_save, sender="job_seekers.TalentSheet")
def handle_talent_sheet_save(sender, instance, created, **kwargs):
    """
    Handle TalentSheet save events.

    Process published talent sheets and remove embeddings for withdrawn/inactive ones.

    Args:
        sender: The model class
        instance: The actual instance being saved
        created: A boolean; True if a new record was created
    """
    # Handle unpublish -> clean up
    if not instance.is_published:

        def _cleanup_unpublished():
            async_task(
                remove_talent_sheet_embeddings,
                instance.id,
                task_name=f"remove_talent_embeddings_{instance.id}",
            )
            async_task(
                remove_talent_sheet_matches,
                instance.id,
                task_name=f"remove_talent_matches_{instance.id}",
            )

        transaction.on_commit(_cleanup_unpublished)
    # Handle publish or re-publish -> enqueue embedding task and matching
    else:
        # Create embeddings and then match to active jobs using Celery chain
        transaction.on_commit(
            lambda: chain(
                create_talent_embeddings_task.si(instance.id), match_talent_task.s()  # type: ignore[misc]
            ).apply_async(task_id=f"embed_and_match_talent_{instance.id}")
        )


@receiver(post_delete, sender="job_seekers.TalentSheet")
def handle_talent_sheet_delete(sender, instance, **kwargs):
    """
    Handle TalentSheet deletion events.

    Remove embeddings when a talent sheet is deleted.

    Args:
        sender: The model class
        instance: The actual instance being deleted
    """
    # On deletion, trigger removal of talent sheet embeddings
    async_task(
        remove_talent_sheet_embeddings,
        instance.id,
        task_name=f"cleanup_talent_embeddings_{instance.id}",
    )
    async_task(
        remove_talent_sheet_matches,
        instance.id,
        task_name=f"cleanup_talent_matches_{instance.id}",
    )
