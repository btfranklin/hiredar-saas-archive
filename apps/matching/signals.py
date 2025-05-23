"""
Signal handlers for matching app.

This module connects Django signals to task execution for matching operations.
"""

from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.core.tasks import safe_async_task, safe_async_task_once
from apps.matching.tasks.job_opening_tasks import remove_job_opening_embeddings
from apps.matching.tasks.matching_tasks import (
    remove_job_opening_matches,
    remove_talent_sheet_matches,
)
from apps.matching.tasks.talent_sheet_tasks import remove_talent_sheet_embeddings

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
        # Create embeddings with deduplication (triggers matching on completion)
        transaction.on_commit(
            lambda: safe_async_task_once(
                "apps.matching.tasks.create_job_opening_embeddings",
                instance.id,
                task_name=f"embed_job_opening_{instance.id}",
            )
        )
    else:
        # Remove embeddings and matches for inactive jobs
        def _cleanup_inactive():
            async_task(remove_job_opening_embeddings, instance.id)
            async_task(remove_job_opening_matches, instance.id)

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
    async_task(remove_job_opening_embeddings, instance.id)
    async_task(remove_job_opening_matches, instance.id)


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
            async_task(remove_talent_sheet_embeddings, instance.id)
            async_task(remove_talent_sheet_matches, instance.id)

        transaction.on_commit(_cleanup_unpublished)
    # Handle publish or re-publish -> enqueue embedding task (deduplicated)
    else:
        # Publish or republish: create embeddings with deduplication
        transaction.on_commit(
            lambda: safe_async_task_once(
                "apps.matching.tasks.create_talent_sheet_embeddings",
                instance.id,
                task_name=f"embed_talent_sheet_{instance.id}",
            )
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
    async_task(remove_talent_sheet_embeddings, instance.id)
    async_task(remove_talent_sheet_matches, instance.id)
