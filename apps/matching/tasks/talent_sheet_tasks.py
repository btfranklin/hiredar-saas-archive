"""
Talent sheet embedding tasks.

This module contains tasks for embedding talent sheets in vector space.
"""

from typing import Any

# Use get_model to handle importing from another app without circular imports
from django.apps import apps

from apps.core.tasks import safe_async_task

# Import shared utilities and alias safe_async_task
from apps.matching.tasks.common import get_embedding, get_index, logger
from apps.resume_processing.utils.xml_parser import extract_personal_details

async_task = safe_async_task


def generate_enriched_text_for_talent(section_name: str, raw_text: str) -> str:
    """
    Enrich raw text from a talent sheet using a template.
    For example: "Section: Promotional Blurb | {raw_text}"

    Args:
        section_name: Name of the section (e.g., "Promotional Blurb", "Skill Overview")
        raw_text: The raw text content to enrich

    Returns:
        Formatted text with section context
    """
    return f"Section: {section_name} | {raw_text.strip()}"


def upsert_talent_embedding(
    vector_id: str, embedding: list[float], metadata: dict[str, Any]
) -> None:
    """
    Upsert a talent embedding vector to Pinecone.

    Args:
        vector_id: Unique ID for the vector
        embedding: The embedding vector
        metadata: Metadata to store with the vector
    """
    try:
        index = get_index()

        # Type ignore is needed because the pinecone-client has inconsistent type definitions
        index.upsert(
            vectors=[(vector_id, embedding, metadata)],  # type: ignore
            namespace="talent_sheets",  # Using namespaces for organization
        )
    except Exception as e:
        logger.error("Error upserting talent vector %s to Pinecone: %s", vector_id, e)
        raise


def create_talent_sheet_embeddings(talent_sheet_id: int, **kwargs) -> None:
    """
    Create and store embeddings for a TalentSheet in Pinecone.

    Process a TalentSheet by extracting key fields, generating embeddings for each section,
    and storing them in Pinecone with rich metadata.

    Args:
        talent_sheet_id: ID of the TalentSheet to process
        **kwargs: Additional keyword arguments (ignored)
    """
    # Get TalentSheet model dynamically to avoid circular imports
    TalentSheet = apps.get_model("job_seekers", "TalentSheet")

    try:
        talent_sheet = TalentSheet.objects.get(id=talent_sheet_id)
    except TalentSheet.DoesNotExist:
        logger.error("TalentSheet with id %s does not exist.", talent_sheet_id)
        return

    # Skip processing if talent sheet is not published
    if not talent_sheet.is_published:
        logger.info(
            "Skipping embedding for non-published TalentSheet %s (is_published: %s)",
            talent_sheet_id,
            talent_sheet.is_published,
        )
        return

    # Define the fields to process - note these are already LLM-processed fields
    fields = {
        "Promotional Blurb": talent_sheet.promotional_blurb,
        "Skill Overview": talent_sheet.skill_overview,
        "Ideal Roles": talent_sheet.ideal_roles,
    }

    # Track all vector IDs we create for this talent sheet for potential future deletion
    vector_ids = []

    # Process each field, ignoring empty ones
    for section, raw_text in fields.items():
        if not raw_text:
            continue

        enriched_text = generate_enriched_text_for_talent(section, raw_text)
        embedding = get_embedding(enriched_text)

        # Create a unique vector ID for each section
        section_slug = section.lower().replace(" ", "_")
        vector_id = f"talent_{talent_sheet.id}_{section_slug}"
        vector_ids.append(vector_id)

        # Determine candidate name from stored resume XML or fallback to profile's user owner name
        xml_content = talent_sheet.job_seeker.resume_xml or ""
        candidate_name: str | None = None
        if xml_content:
            try:
                personal_details = extract_personal_details(xml_content)
                candidate_name = personal_details.get("name")
            except Exception:
                candidate_name = None
        job_seeker_user = talent_sheet.job_seeker.user_owner
        job_seeker_name = candidate_name or (
            job_seeker_user.get_full_name() if job_seeker_user else None
        )

        metadata = {
            "talent_sheet_id": talent_sheet.id,
            "section": section,
            "job_seeker_id": talent_sheet.job_seeker.id,
            "job_seeker_name": job_seeker_name,
            "content_preview": (
                raw_text[:100] + "..." if len(raw_text) > 100 else raw_text
            ),
        }
        # Remove None values from metadata
        metadata = {k: v for k, v in metadata.items() if v is not None}
        # Add pool_id metadata (0 = global; else, the pool primary key)
        pool_owner = talent_sheet.job_seeker.uploaded_resume_pool
        metadata["pool_id"] = pool_owner.id if pool_owner else 0
        upsert_talent_embedding(vector_id, embedding, metadata)
        logger.info(
            "Upserted embedding for TalentSheet %s section '%s' (ID: %s)",
            talent_sheet.id,
            section,
            vector_id,
        )

    logger.info("Completed processing embeddings for TalentSheet %s", talent_sheet.id)


def remove_talent_sheet_embeddings(talent_sheet_id: int) -> None:
    """
    Remove all embeddings associated with a TalentSheet from Pinecone.

    Since Serverless/Starter Pinecone indexes don't support delete-by-filter operations,
    we delete by the predictable vector IDs instead.

    Args:
        talent_sheet_id: ID of the TalentSheet to remove embeddings for
    """
    try:
        # Get the Pinecone index
        index = get_index()

        # First check if the namespace exists
        stats = index.describe_index_stats()
        if "talent_sheets" not in stats.namespaces.keys():
            logger.warning(
                "Namespace 'talent_sheets' doesn't exist yet - nothing to delete for TalentSheet %s",
                talent_sheet_id,
            )
            return

        # For Serverless/Starter tiers, we can't use metadata filtering
        # Instead, we need to delete vectors by their IDs
        # Talent sheet vector IDs follow a predictable pattern:
        sections = [
            "promotional_blurb",
            "skill_overview",
            "ideal_roles",
        ]
        vector_ids = [f"talent_{talent_sheet_id}_{section}" for section in sections]

        # Delete vectors by IDs - this works on all Pinecone tiers
        index.delete(ids=vector_ids, namespace="talent_sheets")

        logger.info("Deleted embeddings for TalentSheet %s", talent_sheet_id)
    except Exception as e:
        # Log the error but don't raise it - we don't want to break the user experience
        # if there's an issue with the embedding system
        logger.error(
            "Error deleting embeddings for TalentSheet %s: %s", talent_sheet_id, e
        )
