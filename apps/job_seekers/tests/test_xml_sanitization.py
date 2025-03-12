"""
Unit tests for the XML sanitization utilities.

Tests the XML sanitization functions used in resume processing.
"""

from unittest.mock import patch

from django.test import SimpleTestCase

from apps.job_seekers.utils.resume_processing.llm_processor import (
    sanitize_xml_if_needed,
)


class XMLSanitizationTests(SimpleTestCase):
    """
    Test cases for the XML sanitization utilities.

    Tests various scenarios where XML content needs to be sanitized:
    - Markdown code block removal
    - Adding missing root elements
    - Closing unclosed tags
    - Character replacements
    - Multiple sanitization needs
    - Edge cases
    """

    def setUp(self):
        """Set up test data for each test method."""
        # A well-formed XML
        self.valid_xml = """<resume>
  <personal>
    <name>John Doe</name>
    <email>john.doe@example.com</email>
    <phone>123-456-7890</phone>
  </personal>
  <summary>A skilled software engineer with experience in Python and Django</summary>
  <skills>
    <skill>Python</skill>
    <skill>Django</skill>
    <skill>JavaScript</skill>
  </skills>
</resume>"""

        # XML wrapped in Markdown code block
        self.markdown_xml = """```xml
<resume>
  <personal>
    <name>John Doe</name>
    <email>john.doe@example.com</email>
  </personal>
</resume>
```"""

        # XML without root element
        self.no_root_xml = """
  <personal>
    <name>John Doe</name>
    <email>john.doe@example.com</email>
  </personal>
  <skills>
    <skill>Python</skill>
  </skills>
"""

        # XML with unclosed root element
        self.unclosed_root_xml = """<resume>
  <personal>
    <name>John Doe</name>
  </personal>
"""

        # XML with problematic characters
        self.problematic_chars_xml = """<resume>
  <personal>
    <name>John & Jane Doe</name>
    <company>Smith&Jones Consulting</company>
    <notes>Used "quotes" and &nbsp; entity</notes>
  </personal>
</resume>"""

    @patch("apps.job_seekers.utils.resume_processing.llm_processor.logger")
    def test_no_sanitization_needed(self, mock_logger):
        """Test when no sanitization is needed for well-formed XML."""
        result, was_sanitized = sanitize_xml_if_needed(self.valid_xml)

        # The XML should remain unchanged
        self.assertEqual(result, self.valid_xml)
        self.assertFalse(was_sanitized)

        # Logger should not have been called for sanitization logs
        mock_logger.info.assert_not_called()

    @patch("apps.job_seekers.utils.resume_processing.llm_processor.logger")
    def test_markdown_code_block_removal(self, mock_logger):
        """Test removal of Markdown code blocks from XML content."""
        result, was_sanitized = sanitize_xml_if_needed(self.markdown_xml)

        # The result should not contain markdown backticks
        self.assertNotIn("```", result)
        self.assertTrue(was_sanitized)

        # Should start with <resume> directly
        self.assertTrue(result.strip().startswith("<resume>"))

        # Debug log should mention Markdown removal
        mock_logger.debug.assert_any_call("Removed Markdown code block syntax")

    @patch("apps.job_seekers.utils.resume_processing.llm_processor.logger")
    def test_add_root_element(self, mock_logger):
        """Test adding root element when missing from XML content."""
        result, was_sanitized = sanitize_xml_if_needed(self.no_root_xml)

        # The result should have <resume> tags added
        self.assertTrue(result.strip().startswith("<resume>"))
        self.assertTrue(result.strip().endswith("</resume>"))
        self.assertTrue(was_sanitized)

    @patch("apps.job_seekers.utils.resume_processing.llm_processor.logger")
    def test_close_root_element(self, mock_logger):
        """Test closing root element when missing from XML content."""
        result, was_sanitized = sanitize_xml_if_needed(self.unclosed_root_xml)

        # The result should have closing </resume> tag added
        self.assertTrue(result.strip().endswith("</resume>"))
        self.assertTrue(was_sanitized)

    @patch("apps.job_seekers.utils.resume_processing.llm_processor.logger")
    def test_character_replacements(self, mock_logger):
        """Test replacement of problematic characters in XML content."""
        result, was_sanitized = sanitize_xml_if_needed(self.problematic_chars_xml)

        # Check specific replacements
        self.assertIn("John &amp; Jane Doe", result)  # & in text should be escaped
        self.assertIn("Smith&amp;Jones", result)  # & in word should be escaped
        self.assertNotIn("&nbsp;", result)  # HTML entity should be replaced
        self.assertTrue(was_sanitized)

    def test_multiple_sanitizations(self):
        """Test XML with multiple sanitization needs applied correctly."""
        # Create XML with multiple issues
        complex_xml = """```xml
  <personal>
    <name>John & Jane</name>
  </personal>
  <skills>
    <skill>Python & Django</skill>
  </skills>
```"""

        result, was_sanitized = sanitize_xml_if_needed(complex_xml)

        # Check all sanitizations were applied
        self.assertNotIn("```", result)  # Markdown removed
        self.assertTrue(result.strip().startswith("<resume>"))  # Root added
        self.assertTrue(result.strip().endswith("</resume>"))  # Root closed
        self.assertIn("John &amp; Jane", result)  # Ampersand escaped
        self.assertTrue(was_sanitized)

    def test_edge_cases(self):
        """Test edge cases like empty strings and non-XML content."""
        # Empty string
        result1, was_sanitized1 = sanitize_xml_if_needed("")
        self.assertEqual(result1, "<resume></resume>")
        self.assertTrue(was_sanitized1)

        # Just whitespace
        result2, was_sanitized2 = sanitize_xml_if_needed("   \n   ")
        self.assertEqual(result2, "<resume></resume>")
        self.assertTrue(was_sanitized2)

        # Non-XML looking content
        non_xml = "This is just plain text, not XML."
        result3, was_sanitized3 = sanitize_xml_if_needed(non_xml)
        self.assertEqual(result3, f"<resume>{non_xml}</resume>")
        self.assertTrue(was_sanitized3)
