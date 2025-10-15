"""
Tests for candidate profile embedding functionality.
"""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.matching.tasks.create_candidate_embeddings import (
    create_candidate_embeddings,
    generate_enriched_text_for_candidate,
)
from apps.matching.tasks.remove_candidate_embeddings import remove_candidate_embeddings


class CandidateEmbeddingTests(TestCase):
    """Test cases for candidate profile embedding functions."""

    def test_generate_enriched_text_for_candidate(self):
        """Test the text enrichment helper for candidate profiles."""
        section = "Promotional Blurb"
        raw_text = "Developer with 5 years of experience"
        expected = "Section: Promotional Blurb | Developer with 5 years of experience"

        result = generate_enriched_text_for_candidate(section, raw_text)
        self.assertEqual(result, expected)

        # Test with whitespace that should be trimmed
        raw_text_with_spaces = "  Developer with 5 years of experience  "
        result = generate_enriched_text_for_candidate(section, raw_text_with_spaces)
        self.assertEqual(result, expected)

    @patch("apps.matching.tasks.create_candidate_embeddings.get_embedding")
    @patch(
        "apps.matching.tasks.create_candidate_embeddings.upsert_candidate_embeddings"
    )
    @patch("apps.matching.tasks.create_candidate_embeddings.apps.get_model")
    def test_create_candidate_embeddings(
        self, mock_get_model, mock_batch_upsert, mock_get_embedding
    ):
        """Test processing a candidate profile."""
        mock_profile = MagicMock()
        mock_profile.id = 123
        mock_profile.is_published = True
        mock_profile.promotional_blurb = "Experienced developer"
        mock_profile.experience_overview = (
            "Chief Researcher (2015-2017): Discovered six new biological compounds "
            "and managed five direct reports."
        )
        mock_profile.ideal_roles = "Backend Developer, Full Stack"
        mock_profile.skills = "Python\nDjango\nJavaScript"
        mock_profile.qualifications = ""
        mock_profile.pool.id = 456
        mock_profile.display_name = "John Doe"

        mock_model = MagicMock()
        mock_model.objects.get.return_value = mock_profile
        mock_get_model.return_value = mock_model

        mock_get_embedding.return_value = [0.1, 0.2, 0.3]

        create_candidate_embeddings(123)

        self.assertEqual(mock_get_embedding.call_count, 3)

        mock_batch_upsert.assert_called_once()

        batch_args, _ = mock_batch_upsert.call_args
        self.assertEqual(
            len(batch_args), 1, "upsert_candidate_embeddings expects only vectors arg"
        )

        vectors_payload = batch_args[0]
        self.assertEqual(len(vectors_payload), 3)

        first_vector_id, first_embedding, first_metadata = vectors_payload[0]
        self.assertTrue(first_vector_id.startswith("candidate_123_"))
        self.assertEqual(first_embedding, [0.1, 0.2, 0.3])
        self.assertEqual(first_metadata["candidate_profile_id"], 123)
        self.assertEqual(first_metadata["pool_id"], 456)
        self.assertEqual(first_metadata["candidate_name"], "John Doe")
        self.assertIn("content_preview", first_metadata)

    @patch("apps.matching.tasks.remove_candidate_embeddings.get_index")
    def test_remove_candidate_embeddings(self, mock_get_index):
        """Test removing candidate embeddings."""
        mock_index = MagicMock()
        mock_get_index.return_value = mock_index

        mock_stats = MagicMock()
        mock_stats.namespaces = {"candidate_profiles": {}}
        mock_index.describe_index_stats.return_value = mock_stats

        remove_candidate_embeddings(123)

        mock_index.delete.assert_called_once()
        args, kwargs = mock_index.delete.call_args
        self.assertEqual(kwargs["namespace"], "candidate_profiles")
        self.assertTrue(all("candidate_123_" in vid for vid in kwargs["ids"]))
