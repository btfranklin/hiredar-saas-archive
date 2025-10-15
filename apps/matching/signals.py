"""
Signal handlers for matching app.

This module connects Django signals to task execution for matching operations.
"""

from celery import chain
from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.core.tasks import safe_async_task

# Import tasks directly instead of aliasing to avoid type inference issues
from apps.matching.tasks.create_candidate_matches import create_candidate_matches
from apps.matching.tasks.create_job_opening_embeddings import (
    create_job_opening_embeddings,
)
from apps.matching.tasks.create_candidate_embeddings import create_candidate_embeddings
from apps.matching.tasks.match_candidate_to_active_jobs import match_candidate_to_active_jobs
from apps.matching.tasks.remove_job_opening_embeddings import (
    remove_job_opening_embeddings,
)
from apps.matching.tasks.remove_job_opening_matches import remove_job_opening_matches
from apps.matching.tasks.remove_candidate_embeddings import remove_candidate_embeddings
from apps.matching.tasks.remove_candidate_matches import remove_candidate_matches

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
        def _create_embeddings_and_matches():
            chain(
                create_job_opening_embeddings.si(instance.id), create_candidate_matches.s()  # type: ignore[misc]
            ).apply_async()

        transaction.on_commit(_create_embeddings_and_matches)
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


@receiver(post_save, sender="candidates.CandidateProfile")
def handle_candidate_profile_save(sender, instance, created, **kwargs):
    """
    Handle CandidateProfile save events.

    Process published candidate profiles and remove embeddings for withdrawn/inactive ones.

    Args:
        sender: The model class
        instance: The actual instance being saved
        created: A boolean; True if a new record was created
    """
    # Handle unpublish -> clean up
    if not instance.is_published:

        def _cleanup_unpublished():
            async_task(
                remove_candidate_embeddings,
                instance.id,
                task_name=f"remove_candidate_embeddings_{instance.id}",
            )
            async_task(
                remove_candidate_matches,
                instance.id,
                task_name=f"remove_candidate_matches_{instance.id}",
            )

        transaction.on_commit(_cleanup_unpublished)
    # Handle publish or re-publish -> enqueue embedding task and matching
    else:
        # Create embeddings and then match to active jobs using Celery chain
        def _create_embeddings_and_match():
            chain(
                create_candidate_embeddings.si(instance.id), match_candidate_to_active_jobs.s()  # type: ignore[misc]
            ).apply_async()

        transaction.on_commit(_create_embeddings_and_match)


@receiver(post_delete, sender="candidates.CandidateProfile")
def handle_candidate_profile_delete(sender, instance, **kwargs):
    """
    Handle CandidateProfile deletion events.

    Remove embeddings when a candidate profile is deleted.

    Args:
        sender: The model class
        instance: The actual instance being deleted
    """
    async_task(
        remove_candidate_embeddings,
        instance.id,
        task_name=f"cleanup_candidate_embeddings_{instance.id}",
    )
    async_task(
        remove_candidate_matches,
        instance.id,
        task_name=f"cleanup_candidate_matches_{instance.id}",
    )
