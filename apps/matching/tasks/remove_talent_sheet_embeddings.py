"""
Task for removing embeddings associated with a TalentSheet from Pinecone.
"""

from celery import shared_task

from apps.matching.tasks.common import get_index, logger, DIMENSIONS

@shared_task(name="apps.matching.tasks.remove_talent_sheet_embeddings")
def remove_talent_sheet_embeddings(talent_sheet_id: int) -> None:
    """
    Remove all embeddings associated with a TalentSheet from Pinecone.

    Since Serverless/Starter Pinecone indexes don't support delete-by-filter operations,
    we delete by the predictable vector IDs instead.

    Args:
        talent_sheet_id: ID of the TalentSheet to remove embeddings for
    """
    try:
        index = get_index()

        stats = index.describe_index_stats()
        if "talent_sheets" not in stats.namespaces.keys():
            logger.warning(
                "Namespace 'talent_sheets' doesn't exist yet - nothing to delete for TalentSheet %s",
                talent_sheet_id,
            )
            return

        metadata_filter = {"talent_sheet_id": {"$eq": talent_sheet_id}}
        dummy_vector = [0.0] * DIMENSIONS
        query_response = index.query(
            namespace="talent_sheets",
            vector=dummy_vector,
            top_k=100,
            filter=metadata_filter,
            include_values=False,
            include_metadata=False,
        )
        vector_ids = [match.id for match in getattr(query_response, "matches", [])]
        index.delete(ids=vector_ids, namespace="talent_sheets")
        logger.info(
            "Deleted %d embeddings for TalentSheet %s", len(vector_ids), talent_sheet_id
        )
    except Exception as e:
        logger.error(
            "Error deleting embeddings for TalentSheet %s: %s", talent_sheet_id, e
        )