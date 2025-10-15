"""
Tests for matching functionality.

This module contains tests for the matching system between candidate profiles and job openings.
"""

from unittest.mock import MagicMock, patch

from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase

from apps.matching.core.matching import (
    JOB_OVERVIEW,
    JOB_REQUIRED_SKILLS,
    JOB_RESPONSIBILITIES,
    TALENT_CAREER_DIRECTION,
    TALENT_EXPERIENCE_OVERVIEW,
    TALENT_SKILLS,
    match_candidate_to_jobs,
    match_job_to_candidates,
)
from apps.matching.core.pinecone_client import query_pinecone
from apps.matching.core.retrieval import (
    get_candidate_section_embedding,
    get_job_section_embedding,
)
from apps.matching.core.vector_operations import average_vectors


class MatchingUtilsTests(TestCase):
    """Test utility functions used in the matching system."""

    def test_average_vectors(self):
        """Test the averaging of vectors."""
        vectors = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
        avg = average_vectors(vectors)
        self.assertEqual(avg, [2.5, 3.5, 4.5])

        # Test with single vector
        single_vector = [[1.0, 2.0, 3.0]]
        avg = average_vectors(single_vector)
        self.assertEqual(avg, [1.0, 2.0, 3.0])

        # Test with empty list
        with self.assertRaises(ValueError):
            average_vectors([])

    @patch("apps.matching.core.pinecone_client.get_index")
    def test_query_pinecone(self, mock_get_index):
        """Test querying Pinecone for similar vectors."""
        # Mock the Pinecone client response with a match
        mock_match = MagicMock()
        mock_match.id = "test_vector_id"
        mock_match.score = 0.95
        mock_match.metadata = {"key": "value"}

        # Mock the response object with a matches attribute
        mock_response = MagicMock()
        mock_response.matches = [mock_match]

        # Set up the index mock
        mock_index = MagicMock()
        mock_index.query.return_value = mock_response
        mock_get_index.return_value = mock_index

        # Call the function and assert results
        results = query_pinecone(
            query_vector=[0.1, 0.2, 0.3], namespace="test_namespace", top_k=5
        )

        # Verify the results - should be the matches list
        self.assertEqual(len(results), 1)
        match = results[0]  # type: ignore
        self.assertEqual(match.id, "test_vector_id")  # type: ignore
        self.assertEqual(match.score, 0.95)  # type: ignore
        self.assertEqual(match.metadata, {"key": "value"})  # type: ignore

        # Verify the query was called with correct parameters
        mock_index.query.assert_called_once()
        args, kwargs = mock_index.query.call_args
        self.assertEqual(kwargs.get("vector"), [0.1, 0.2, 0.3])
        self.assertEqual(kwargs.get("top_k"), 5)
        self.assertEqual(kwargs.get("namespace"), "test_namespace")

        # Test error handling
        mock_index.query.side_effect = Exception("Test error")
        results = query_pinecone(
            query_vector=[0.1, 0.2, 0.3], namespace="test_namespace"
        )
        self.assertEqual(results, [])


class MatchingEmbeddingRetrievalTests(TestCase):
    """Test functions that retrieve embeddings from Pinecone."""

    @patch("apps.matching.core.retrieval.get_index")
    def test_get_candidate_section_embedding(self, mock_get_index):
        """Test retrieving candidate profile section embeddings."""
        # Create a mock vector with values attribute
        mock_vector = MagicMock()
        mock_vector.values = [0.1, 0.2, 0.3]

        # Create a mock response with vectors dictionary - use the slug format
        mock_response = MagicMock()
        mock_response.vectors = {"candidate_123_career_direction": mock_vector}

        # Set up the mock index to return our response
        mock_index = MagicMock()
        mock_index.fetch.return_value = mock_response
        mock_get_index.return_value = mock_index

        # Call the function
        embedding = get_candidate_section_embedding(123, "Career Direction")

        # Verify the result
        self.assertEqual(embedding, [0.1, 0.2, 0.3])

        # Verify the fetch was called with correct parameters
        mock_index.fetch.assert_called_once()
        args, kwargs = mock_index.fetch.call_args
        self.assertEqual(kwargs.get("ids"), ["candidate_123_career_direction"])
        self.assertEqual(kwargs.get("namespace"), "candidate_profiles")

        # Test non-existent vector
        mock_response.vectors = {}
        embedding = get_candidate_section_embedding(123, "Career Direction")
        self.assertIsNone(embedding)

        # Test error handling
        mock_index.fetch.side_effect = Exception("Test error")
        embedding = get_candidate_section_embedding(123, "Career Direction")
        self.assertIsNone(embedding)

    @patch("apps.matching.core.retrieval.get_index")
    def test_get_job_section_embedding(self, mock_get_index):
        """Test retrieving job opening section embeddings."""
        # Create a mock vector with values attribute
        mock_vector = MagicMock()
        mock_vector.values = [0.4, 0.5, 0.6]

        # Create a mock response with vectors dictionary - use the slug format
        mock_response = MagicMock()
        mock_response.vectors = {"job_456_required_skills": mock_vector}

        # Set up the mock index to return our response
        mock_index = MagicMock()
        mock_index.fetch.return_value = mock_response
        mock_get_index.return_value = mock_index

        # Call the function
        embedding = get_job_section_embedding(456, "Required Skills")

        # Verify the result
        self.assertEqual(embedding, [0.4, 0.5, 0.6])

        # Verify the fetch was called with correct parameters
        mock_index.fetch.assert_called_once()
        args, kwargs = mock_index.fetch.call_args
        self.assertEqual(kwargs.get("ids"), ["job_456_required_skills"])
        self.assertEqual(kwargs.get("namespace"), "job_openings")


class MatchingFunctionsTests(TestCase):
    """Test the main matching functions."""

    @patch("apps.matching.core.matching.get_candidate_section_embedding")
    @patch("apps.matching.core.matching.query_pinecone")
    @patch("apps.matching.core.matching.apps.get_model")
    def test_match_candidate_to_jobs(
        self, mock_get_model, mock_query_pinecone, mock_get_candidate_embedding
    ):
        """Test matching a candidate profile to job openings."""
        mock_candidate = MagicMock()
        mock_candidate.is_published = True

        mock_model = MagicMock()
        mock_model.objects.get.return_value = mock_candidate
        mock_get_model.return_value = mock_model

        mock_get_candidate_embedding.side_effect = lambda candidate_id, section: {
            TALENT_CAREER_DIRECTION: [0.1, 0.2, 0.3],
            TALENT_EXPERIENCE_OVERVIEW: [0.4, 0.5, 0.6],
            TALENT_SKILLS: [0.7, 0.8, 0.9],
        }.get(section)

        # Mock the Pinecone query results
        mock_match = MagicMock()
        mock_match.id = "job_123_job_overview"
        mock_match.score = 0.95
        mock_match.metadata = {"title": "Software Engineer"}

        mock_query_pinecone.return_value = [mock_match]

        # Call the matching function
        results = match_candidate_to_jobs(123, top_k=5)

        # Verify the results - check for new keys
        self.assertIn("holistic_matches", results)
        self.assertIn("skills_matches", results)
        self.assertIn("experience_matches", results)
        self.assertIn("wildcard_matches", results)

        # Should have been called 4 times (once for each perspective)
        self.assertEqual(mock_query_pinecone.call_count, 4)

        # Test handling of non-existent candidate profile
        mock_model.objects.get.side_effect = ObjectDoesNotExist(
            "CandidateProfile not found"
        )
        results = match_candidate_to_jobs(999)
        self.assertEqual(results.get("holistic_matches", -1), [])  # Check specific key

        # Reset mock for next test case
        mock_model.objects.get.side_effect = None
        mock_model.objects.get.return_value = mock_candidate

        # Test handling of unpublished candidate profile
        mock_candidate.is_published = False
        results = match_candidate_to_jobs(123)
        self.assertEqual(results.get("holistic_matches", -1), [])  # Check specific key
        self.assertEqual(
            mock_query_pinecone.call_count, 4
        )  # Query should not run if unpublished

    @patch("apps.matching.core.matching.get_job_section_embedding")
    @patch("apps.matching.core.matching.query_pinecone")
    @patch("apps.matching.core.matching.apps.get_model")
    def test_match_job_to_candidates(
        self, mock_get_model, mock_query_pinecone, mock_get_job_embedding
    ):
        """Test matching a job opening to candidate profiles."""
        # Mock the JobOpening model - make it active
        mock_job = MagicMock()
        mock_job.is_active = True  # Ensure it's active

        mock_model = MagicMock()
        mock_model.objects.get.return_value = mock_job
        mock_get_model.return_value = mock_model

        # Mock the embedding retrieval for specific sections
        mock_get_job_embedding.side_effect = lambda job_id, section: {
            JOB_OVERVIEW: [0.1, 0.2, 0.3],
            JOB_REQUIRED_SKILLS: [0.4, 0.5, 0.6],
            JOB_RESPONSIBILITIES: [0.7, 0.8, 0.9],
        }.get(section)

        # Mock the Pinecone query results
        mock_match = MagicMock()
        mock_match.id = "candidate_456_career_direction"
        mock_match.score = 0.92
        mock_match.metadata = {"candidate_name": "John Doe"}

        mock_query_pinecone.return_value = [mock_match]

        # Call the matching function
        results = match_job_to_candidates(456, top_k=5)

        # Verify the results - check for new keys
        self.assertIn("holistic_matches", results)
        self.assertIn("skills_matches", results)
        self.assertIn("experience_matches", results)
        self.assertIn("wildcard_matches", results)

        # Should have been called 4 times (once for each perspective)
        self.assertEqual(mock_query_pinecone.call_count, 4)

        # Test handling of non-existent job
        mock_model.objects.get.side_effect = ObjectDoesNotExist("JobOpening not found")
        results = match_job_to_candidates(999)
        self.assertEqual(results.get("holistic_matches", -1), [])  # Check specific key

        # Reset mock for next test case
        mock_model.objects.get.side_effect = None
        mock_model.objects.get.return_value = mock_job

        # Test handling of inactive job
        mock_job.is_active = False
        results = match_job_to_candidates(456)
        self.assertEqual(results.get("holistic_matches", -1), [])  # Check specific key
        self.assertEqual(
            mock_query_pinecone.call_count, 4
        )  # Query should not run if inactive
