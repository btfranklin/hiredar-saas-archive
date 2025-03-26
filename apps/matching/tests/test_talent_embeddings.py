"""
Tests for talent sheet embedding functionality.
"""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.matching.tasks.talent_sheet_tasks import (
    create_talent_sheet_embeddings,
    generate_enriched_text_for_talent,
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

    @patch("apps.matching.tasks.talent_sheet_tasks.get_embedding")
    @patch("apps.matching.tasks.talent_sheet_tasks.upsert_talent_embedding")
    @patch("apps.matching.tasks.talent_sheet_tasks.apps.get_model")
    def test_create_talent_sheet_embeddings(
        self, mock_get_model, mock_upsert, mock_get_embedding
    ):
        """Test processing a talent sheet."""
        # Mock the TalentSheet model and a sample object
        mock_talent_sheet = MagicMock()
        mock_talent_sheet.id = 123
        mock_talent_sheet.is_published = True
        mock_talent_sheet.promotional_blurb = "Experienced developer"
        mock_talent_sheet.skill_overview = "Python, Django, JavaScript"
        mock_talent_sheet.ideal_roles = "Backend Developer, Full Stack"
        mock_talent_sheet.job_seeker.id = 456
        mock_talent_sheet.job_seeker.user.get_full_name.return_value = "John Doe"

        # Make the get_model return a mock model class that returns our mock object
        mock_model = MagicMock()
        mock_model.objects.get.return_value = mock_talent_sheet
        mock_get_model.return_value = mock_model

        # Mock the embedding function to return a sample vector
        mock_get_embedding.return_value = [0.1, 0.2, 0.3]

        # Call the function
        create_talent_sheet_embeddings(123)

        # Assertions
        # Should be called for all 3 fields in the talent sheet
        self.assertEqual(mock_get_embedding.call_count, 3)
        self.assertEqual(mock_upsert.call_count, 3)

        # Check one of the calls to verify parameters
        args, kwargs = mock_upsert.call_args_list[0]
        self.assertEqual(
            len(args),
            3,
            "Should have vector_id, embedding, and metadata positional args",
        )

        # The first positional argument should be the vector_id
        vector_id = args[0]
        self.assertTrue(
            vector_id.startswith("talent_123_"),
            "vector_id should start with talent_123_",
        )

        # Second positional argument should be the embedding
        embedding = args[1]
        self.assertEqual(
            embedding, [0.1, 0.2, 0.3], "embedding should match the mocked value"
        )

        # Third positional argument should be the metadata
        metadata = args[2]
        self.assertEqual(metadata["talent_sheet_id"], 123)
        self.assertEqual(metadata["job_seeker_id"], 456)
        self.assertEqual(metadata["job_seeker_name"], "John Doe")
        self.assertTrue("content_preview" in metadata)

    @patch("apps.matching.tasks.talent_sheet_tasks.get_index")
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
