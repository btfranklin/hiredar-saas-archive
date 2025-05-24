"""
Task for removing embeddings associated with a JobOpening from Pinecone.
"""

from celery import shared_task

from apps.matching.tasks.common import get_index, logger, DIMENSIONS

@shared_task(name="apps.matching.tasks.remove_job_opening_embeddings")
def remove_job_opening_embeddings(job_opening_id: int) -> None:
    """
    Remove all embeddings associated with a JobOpening from Pinecone.

    Since Serverless/Starter Pinecone indexes don't support delete-by-filter operations,
    we delete by the predictable vector IDs instead.

    Args:
        job_opening_id: ID of the JobOpening to remove embeddings for
    """
    try:
        index = get_index()

        stats = index.describe_index_stats()
        if "job_openings" not in stats.namespaces.keys():
            logger.warning(
                "Namespace 'job_openings' doesn't exist yet - nothing to delete for JobOpening %s",
                job_opening_id,
            )
            return

        metadata_filter = {"job_opening_id": {"$eq": job_opening_id}}
        dummy_vector = [0.0] * DIMENSIONS
        query_response = index.query(
            namespace="job_openings",
            vector=dummy_vector,
            top_k=100,
            filter=metadata_filter,
            include_values=False,
            include_metadata=False,
        )
        vector_ids = [match.id for match in getattr(query_response, "matches", [])]
        if vector_ids:
            index.delete(ids=vector_ids, namespace="job_openings")
        logger.info(
            "Deleted %d embeddings for JobOpening %s", len(vector_ids), job_opening_id
        )
    except Exception as e:
        logger.error(
            "Error deleting embeddings for JobOpening %s: %s", job_opening_id, e
        )