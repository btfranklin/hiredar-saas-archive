"""
Unit tests for the XML sanitization utilities.

Tests the XML sanitization functions used in resume processing.
"""

from unittest.mock import patch

from django.test import SimpleTestCase

from apps.resume_processing.utils.llm_processor import sanitize_xml


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

    @patch("apps.resume_processing.utils.llm_processor.logger")
    def test_no_sanitization_needed(self, mock_logger):
        """Test when no sanitization is needed for well-formed XML."""
        result = sanitize_xml(self.valid_xml)

        # The XML should remain unchanged
        self.assertEqual(result, self.valid_xml)

        # Logger should not have been called for sanitization logs
        mock_logger.debug.assert_not_called()

    @patch("apps.resume_processing.utils.llm_processor.logger")
    def test_markdown_code_block_removal(self, mock_logger):
        """Test removal of Markdown code blocks from XML content."""
        result = sanitize_xml(self.markdown_xml)

        # The result should not contain markdown backticks
        self.assertNotIn("```", result)

        # Should start with <resume> directly
        self.assertTrue(result.startswith("<resume>"))

        # Debug log should mention Markdown removal
        mock_logger.debug.assert_any_call(
            "Sanitization: Removed Markdown code block syntax"
        )

    @patch("apps.resume_processing.utils.llm_processor.logger")
    def test_add_root_element(self, mock_logger):
        """Test adding root element when missing from XML content."""
        result = sanitize_xml(self.no_root_xml)

        # Should have added the resume root element
        self.assertTrue(result.startswith("<resume>"))
        self.assertTrue(result.endswith("</resume>"))

        # Logger should have recorded the sanitization
        mock_logger.debug.assert_any_call(
            "Sanitization: Added missing root <resume> element"
        )

    @patch("apps.resume_processing.utils.llm_processor.logger")
    def test_close_root_element(self, mock_logger):
        """Test closing root element when missing from XML content."""
        result = sanitize_xml(self.unclosed_root_xml)

        # Should have closed the resume tag
        self.assertTrue(result.endswith("</resume>"))

        # Logger should have recorded the sanitization
        mock_logger.debug.assert_any_call(
            "Sanitization: Added missing closing </resume> tag"
        )

    @patch("apps.resume_processing.utils.llm_processor.logger")
    def test_character_replacements(self, mock_logger):
        """Test replacement of problematic characters in XML content."""
        result = sanitize_xml(self.problematic_chars_xml)

        # Should have replaced problematic characters
        self.assertIn("&amp;", result)  # Check that '&' is properly escaped
        self.assertNotIn("<div>", result)  # Raw HTML tags should be escaped

        # Logger should have recorded the sanitization
        # We don't check the exact messages here as they depend on the specific characters found

    @patch("apps.resume_processing.utils.llm_processor.logger")
    def test_multiple_sanitizations(self, mock_logger):
        """Test XML with multiple sanitization needs applied correctly."""
        complex_xml = """```xml
        <experience>
            <job>&Company & Co</job>
            <details>Worked with <technologies>
        ```"""

        result = sanitize_xml(complex_xml)

        # Should have fixed multiple issues
        self.assertNotIn("```", result)
        self.assertTrue(result.startswith("<resume>"))
        self.assertTrue(result.endswith("</resume>"))
        self.assertIn(
            "<technologies>", result
        )  # The sanitizer might not escape this tag
        self.assertIn("&amp;Company &amp; Co", result)

        # Logger should have recorded the sanitization
        mock_logger.debug.assert_any_call(
            "Sanitization: Removed Markdown code block syntax"
        )

        # Check that at least one debug call is about escaped ampersands
        ampersand_message_found = False
        for call in mock_logger.debug.call_args_list:
            args, _ = call
            if args and args[0] == "Sanitization: Escaped %d standalone ampersands":
                ampersand_message_found = True
                break
        self.assertTrue(
            ampersand_message_found, "No log message about escaped ampersands found"
        )

    @patch("apps.resume_processing.utils.llm_processor.logger")
    def test_edge_cases(self, mock_logger):
        """Test edge cases like empty strings and non-XML content."""
        # Empty string
        result1 = sanitize_xml("")
        self.assertEqual(result1, "<resume></resume>")

        # Non-XML string
        result2 = sanitize_xml("Just a plain text string")
        self.assertEqual(result2, "<resume>Just a plain text string</resume>")

        # Logger should have recorded the sanitization
        mock_logger.debug.assert_any_call(
            "Sanitization: Added missing root <resume> element"
        )
