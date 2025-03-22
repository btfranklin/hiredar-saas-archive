"""
Talent sheet embedding tasks.

This module contains tasks for embedding talent sheets in vector space.
"""

from typing import Any

# Use get_model to handle importing from another app without circular imports
from django.apps import apps

# Import shared utilities
from apps.matching.tasks.common import get_embedding, index, logger


def generate_enriched_text_for_talent(section_name: str, raw_text: str) -> str:
    """
    Generate a standardized, enriched text string for embedding talent sheets.
    Uses a simple template to provide context without modifying already-processed text.

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
    Upsert a talent-related vector into Pinecone.

    Args:
        vector_id: Unique identifier for the vector
        embedding: The embedding vector
        metadata: Dictionary of metadata to store with the vector

    Raises:
        Exception: If the Pinecone API call fails
    """
    try:
        # Using the current Pinecone client format
        # Type ignore is needed because the pinecone-client has inconsistent type definitions
        index.upsert(
            vectors=[(vector_id, embedding, metadata)],  # type: ignore
            namespace="talent_sheets",  # Using namespaces for organization
        )
    except Exception as e:
        logger.error("Error upserting talent vector %s to Pinecone: %s", vector_id, e)
        raise


def process_talent_sheet(talent_sheet_id: int) -> None:
    """
    Process a TalentSheet: extract text, generate embeddings,
    and upsert them into Pinecone. Note that talent sheet text
    is already processed by an LLM prior to this step.

    Args:
        talent_sheet_id: ID of the TalentSheet to process
    """
    # Get TalentSheet model dynamically to avoid circular imports
    TalentSheet = apps.get_model("job_seekers", "TalentSheet")

    try:
        talent_sheet = TalentSheet.objects.get(id=talent_sheet_id)
    except TalentSheet.DoesNotExist:
        logger.error("TalentSheet with id %s does not exist.", talent_sheet_id)
        return

    # Skip processing if talent sheet is not published
    if talent_sheet.status != "PUBLISHED":
        logger.info(
            "Skipping embedding for non-published TalentSheet %s (status: %s)",
            talent_sheet_id,
            talent_sheet.status,
        )
        return

    # Define the fields to process - note these are already LLM-processed fields
    fields = {
        "Promotional Blurb": talent_sheet.promotional_blurb,
        "Skill Overview": talent_sheet.skill_overview,
        "Ideal Roles": talent_sheet.ideal_roles,
    }

    # Process each field, ignoring empty ones
    for section, raw_text in fields.items():
        if not raw_text:
            continue

        enriched_text = generate_enriched_text_for_talent(section, raw_text)
        embedding = get_embedding(enriched_text)

        # Create a unique vector ID for each section
        section_slug = section.lower().replace(" ", "_")
        vector_id = f"talent_{talent_sheet.id}_{section_slug}"

        # Enhanced metadata for better search filtering and result display
        metadata = {
            "talent_sheet_id": talent_sheet.id,
            "section": section,
            "job_seeker_id": talent_sheet.job_seeker.id,
            "job_seeker_name": talent_sheet.job_seeker.user.get_full_name(),
            "content_preview": (
                raw_text[:100] + "..." if len(raw_text) > 100 else raw_text
            ),
        }

        # Remove None values from metadata
        metadata = {k: v for k, v in metadata.items() if v is not None}

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

    Args:
        talent_sheet_id: ID of the TalentSheet to remove embeddings for

    Raises:
        Exception: If the Pinecone API call fails
    """
    try:
        # Using a filter to find all vectors for this talent sheet
        # Type ignore is needed because the pinecone-client has inconsistent type definitions
        filter_dict = {"talent_sheet_id": talent_sheet_id}

        index.delete(filter=filter_dict, namespace="talent_sheets")  # type: ignore

        logger.info("Deleted embeddings for TalentSheet %s", talent_sheet_id)
    except Exception as e:
        logger.error(
            "Error deleting embeddings for TalentSheet %s: %s", talent_sheet_id, e
        )
        raise
