"""
Service functions for candidate profile embeddings.
"""

from typing import Any

from apps.matching.tasks.common import get_index, logger


def generate_enriched_text_for_candidate(section_name: str, raw_text: str) -> str:
    """
    Enrich raw text from a candidate profile using a template.

    Args:
        section_name: Name of the section (e.g., "Professional Overview").
        raw_text: The raw text content to enrich.
    """
    return f"Section: {section_name} | {raw_text.strip()}"


def upsert_candidate_embeddings(
    vectors: list[tuple[str, list[float], dict[str, Any]]],
) -> None:
    """
    Batch-upsert multiple candidate embeddings to Pinecone in a single request.
    """
    if not vectors:
        return

    try:
        index = get_index()

        index.upsert(
            vectors=vectors,  # type: ignore[arg-type]
            namespace="candidate_profiles",
        )
        logger.info("Batch-upserted %d candidate vectors to Pinecone", len(vectors))
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Error batch-upserting %d candidate vectors: %s", len(vectors), exc)
        raise

