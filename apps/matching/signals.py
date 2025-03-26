"""
Signal handlers for matching app.

This module connects Django signals to task execution for matching operations.
"""

# Get the JobOpening model dynamically to avoid circular imports
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django_q.tasks import async_task


@receiver(post_save, sender="recruiters.JobOpening")
def handle_job_opening_save(sender, instance, created, **kwargs):
    """
    Handle JobOpening save events.

    Process active job openings for embeddings and remove embeddings for inactive ones.

    Args:
        sender: The model class
        instance: The actual instance being saved
        created: A boolean; True if a new record was created
    """
    # Only process embeddings for active jobs
    if instance.status == "active":
        async_task("apps.matching.tasks.create_job_opening_embeddings", instance.id)
    else:
        # If a job is inactive, remove the embeddings
        async_task("apps.matching.tasks.remove_job_opening_embeddings", instance.id)


@receiver(post_delete, sender="recruiters.JobOpening")
def handle_job_opening_delete(sender, instance, **kwargs):
    """
    Handle JobOpening deletion events.

    Remove embeddings when a job opening is deleted.

    Args:
        sender: The model class
        instance: The actual instance being deleted
    """
    # On deletion, trigger removal of job embeddings
    async_task("apps.matching.tasks.remove_job_opening_embeddings", instance.id)


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
    # Only process published talent sheets
    if instance.is_published:
        async_task("apps.matching.tasks.create_talent_sheet_embeddings", instance.id)
    else:
        # If a talent sheet is unpublished, remove the embeddings
        async_task("apps.matching.tasks.remove_talent_sheet_embeddings", instance.id)


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
    async_task("apps.matching.tasks.remove_talent_sheet_embeddings", instance.id)
