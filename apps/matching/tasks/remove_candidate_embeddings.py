"""
Task for removing embeddings associated with a CandidateProfile from Pinecone.
"""

from celery import shared_task

from apps.matching.tasks.common import DIMENSIONS, get_index, logger


@shared_task(name="apps.matching.tasks.remove_candidate_embeddings")
def remove_candidate_embeddings(candidate_profile_id: int) -> None:
    """
    Remove all embeddings associated with a CandidateProfile from Pinecone.
    """
    try:
        index = get_index()

        stats = index.describe_index_stats()
        if "candidate_profiles" not in stats.namespaces.keys():
            logger.warning(
                "Namespace 'candidate_profiles' doesn't exist yet - nothing to delete for CandidateProfile %s",
                candidate_profile_id,
            )
            return

        metadata_filter = {"candidate_profile_id": {"$eq": candidate_profile_id}}
        dummy_vector = [0.0] * DIMENSIONS
        query_response = index.query(
            namespace="candidate_profiles",
            vector=dummy_vector,
            top_k=100,
            filter=metadata_filter,
            include_values=False,
            include_metadata=False,
        )
        vector_ids = [match.id for match in getattr(query_response, "matches", [])]
        if vector_ids:
            index.delete(ids=vector_ids, namespace="candidate_profiles")
        logger.info(
            "Deleted %d embeddings for CandidateProfile %s",
            len(vector_ids),
            candidate_profile_id,
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error(
            "Error deleting embeddings for CandidateProfile %s: %s",
            candidate_profile_id,
            exc,
        )
