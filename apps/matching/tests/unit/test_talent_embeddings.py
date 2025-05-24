"""
Tests for talent sheet embedding functionality.
"""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.matching.tasks.create_talent_sheet_embeddings import (
    create_talent_sheet_embeddings,
    generate_enriched_text_for_talent,
)
from apps.matching.tasks.remove_talent_sheet_embeddings import (
    remove_talent_sheet_embeddings,
)


class TalentSheetEmbeddingTests(TestCase):
    """Test cases for talent sheet embedding functions."""

    def test_generate_enriched_text_for_talent(self):
        """Test the text enrichment function for talent sheets."""
        section = "Promotional Blurb"
        raw_text = "Developer with 5 years of experience"
        expected = "Section: Promotional Blurb | Developer with 5 years of experience"

        result = generate_enriched_text_for_talent(section, raw_text)
        self.assertEqual(result, expected)

        # Test with whitespace that should be trimmed
        raw_text_with_spaces = "  Developer with 5 years of experience  "
        result = generate_enriched_text_for_talent(section, raw_text_with_spaces)
        self.assertEqual(result, expected)

    @patch("apps.matching.tasks.create_talent_sheet_embeddings.get_embedding")
    @patch(
        "apps.matching.tasks.create_talent_sheet_embeddings.upsert_talent_embeddings"
    )
    @patch("apps.matching.tasks.create_talent_sheet_embeddings.apps.get_model")
    def test_create_talent_sheet_embeddings(
        self, mock_get_model, mock_batch_upsert, mock_get_embedding
    ):
        """Test processing a talent sheet."""
        # Mock the TalentSheet model and a sample object
        mock_talent_sheet = MagicMock()
        mock_talent_sheet.id = 123
        mock_talent_sheet.is_published = True
        mock_talent_sheet.promotional_blurb = "Experienced developer"
        mock_talent_sheet.experience_overview = (
            "Chief Researcher (2015-2017): Discovered six new biological compounds "
            "and managed five direct reports."
        )
        mock_talent_sheet.ideal_roles = "Backend Developer, Full Stack"
        mock_talent_sheet.skills = "Python\nDjango\nJavaScript"
        mock_talent_sheet.qualifications = ""
        # Set up job seeker ID and mock user_owner for naming
        mock_talent_sheet.job_seeker.id = 456
        mock_user_owner = MagicMock()
        mock_user_owner.get_full_name.return_value = "John Doe"
        mock_talent_sheet.job_seeker.user_owner = mock_user_owner

        # Make the get_model return a mock model class that returns our mock object
        mock_model = MagicMock()
        mock_model.objects.get.return_value = mock_talent_sheet
        mock_get_model.return_value = mock_model

        # Mock the embedding function to return a sample vector
        mock_get_embedding.return_value = [0.1, 0.2, 0.3]

        # Call the function
        create_talent_sheet_embeddings(123)

        # Assertions
        # Embedding generation still happens per section
        self.assertEqual(mock_get_embedding.call_count, 3)

        # We now batch-upsert, so the function should be called exactly once
        mock_batch_upsert.assert_called_once()

        # Inspect the single batch payload tuple list
        batch_args, _ = mock_batch_upsert.call_args
        self.assertEqual(
            len(batch_args), 1, "upsert_talent_embeddings expects only vectors arg"
        )

        vectors_payload = batch_args[0]
        # Expect 3 section vectors in the batch
        self.assertEqual(len(vectors_payload), 3)

        first_vector_id, first_embedding, first_metadata = vectors_payload[0]
        self.assertTrue(first_vector_id.startswith("talent_123_"))
        self.assertEqual(first_embedding, [0.1, 0.2, 0.3])
        self.assertEqual(first_metadata["talent_sheet_id"], 123)
        self.assertEqual(first_metadata["job_seeker_id"], 456)
        self.assertEqual(first_metadata["job_seeker_name"], "John Doe")
        self.assertIn("content_preview", first_metadata)

    @patch("apps.matching.tasks.remove_talent_sheet_embeddings.get_index")
    def test_remove_talent_sheet_embeddings(self, mock_get_index):
        """Test removing talent sheet embeddings."""
        # Setup the mock
        mock_index = MagicMock()
        mock_get_index.return_value = mock_index

        # Also mock the stats to prevent errors
        mock_stats = MagicMock()
        mock_stats.namespaces = {"talent_sheets": {}}
        mock_index.describe_index_stats.return_value = mock_stats

        # Call the function
        remove_talent_sheet_embeddings(123)

        # Verify delete was called with correct parameters
        mock_index.delete.assert_called_once()
        args, kwargs = mock_index.delete.call_args
        self.assertEqual(kwargs["namespace"], "talent_sheets")
        self.assertTrue(all("talent_123_" in id for id in kwargs["ids"]))
