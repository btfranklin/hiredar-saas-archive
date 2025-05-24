"""
Service functions for talent sheet embeddings.
"""

from typing import Any

from apps.matching.tasks.common import get_index, logger


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


def upsert_talent_embeddings(
    vectors: list[tuple[str, list[float], dict[str, Any]]],
) -> None:
    """
    Batch-upsert multiple talent embeddings to Pinecone in a single request.

    Args:
        vectors: List of `(vector_id, embedding, metadata)` tuples to upsert.
    """
    if not vectors:
        return

    try:
        index = get_index()

        index.upsert(
            vectors=vectors,  # type: ignore[arg-type]
            namespace="talent_sheets",
        )
        logger.info("Batch-upserted %d talent vectors to Pinecone", len(vectors))
    except Exception as e:
        logger.error("Error batch-upserting %d talent vectors: %s", len(vectors), e)
        raise
