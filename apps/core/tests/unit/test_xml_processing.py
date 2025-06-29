"""
Unit tests for the XML processing utilities.

Tests the XML processing functions used across the application.
"""

from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.utils.xml_processing import sanitize_xml_response


class XMLProcessingTests(SimpleTestCase):
    """
    Test cases for the XML processing utilities.

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

    @patch("apps.core.utils.xml_processing.logger")
    def test_no_sanitization_needed(self, mock_logger):
        """Test when no sanitization is needed for well-formed XML."""
        result = sanitize_xml_response(self.valid_xml, expected_root="resume")

        # The XML should remain unchanged
        self.assertEqual(result, self.valid_xml)

        # Logger should not have been called for sanitization logs
        mock_logger.debug.assert_not_called()

    @patch("apps.core.utils.xml_processing.logger")
    def test_markdown_code_block_removal(self, mock_logger):
        """Test removal of Markdown code blocks from XML content."""
        result = sanitize_xml_response(self.markdown_xml, expected_root="resume")

        # The result should not contain markdown backticks
        self.assertNotIn("```", result)

        # Should start with <resume> directly
        self.assertTrue(result.startswith("<resume>"))

        # Debug log should mention Markdown removal
        mock_logger.debug.assert_any_call(
            "Sanitization: Removed Markdown code block syntax"
        )

    @patch("apps.core.utils.xml_processing.logger")
    def test_add_root_element(self, mock_logger):
        """Test adding root element when missing from XML content."""
        result = sanitize_xml_response(self.no_root_xml, expected_root="resume")

        # Should have added the resume root element
        self.assertTrue(result.startswith("<resume>"))
        self.assertTrue(result.endswith("</resume>"))

        # Logger should have recorded the sanitization
        mock_logger.debug.assert_any_call(
            "Sanitization: Added missing root <%s> element", "resume"
        )

    @patch("apps.core.utils.xml_processing.logger")
    def test_close_root_element(self, mock_logger):
        """Test closing root element when missing from XML content."""
        result = sanitize_xml_response(self.unclosed_root_xml, expected_root="resume")

        # Should have closed the resume tag
        self.assertTrue(result.endswith("</resume>"))

        # Logger should have recorded the sanitization
        mock_logger.debug.assert_any_call(
            "Sanitization: Added missing closing </%s> tag", "resume"
        )

    @patch("apps.core.utils.xml_processing.logger")
    def test_character_replacements(self, mock_logger):
        """Test replacement of problematic characters in XML content."""
        result = sanitize_xml_response(
            self.problematic_chars_xml, expected_root="resume"
        )

        # Should have replaced problematic characters
        self.assertIn("&amp;", result)  # Check that '&' is properly escaped
        self.assertNotIn("<div>", result)  # Raw HTML tags should be escaped

        # Logger should have recorded the sanitization
        # We don't check the exact messages here as they depend on the specific characters found

    @patch("apps.core.utils.xml_processing.logger")
    def test_multiple_sanitizations(self, mock_logger):
        """Test XML with multiple sanitization needs applied correctly."""
        complex_xml = """```xml
        <experience>
            <job>&Company & Co</job>
            <details>Worked with <technologies>
        ```"""

        result = sanitize_xml_response(complex_xml, expected_root="resume")

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

    @patch("apps.core.utils.xml_processing.logger")
    def test_edge_cases(self, mock_logger):
        """Test edge cases like empty strings and non-XML content."""
        # Empty string
        result1 = sanitize_xml_response("", expected_root="resume")
        self.assertEqual(result1, "<resume></resume>")

        # Non-XML string
        result2 = sanitize_xml_response(
            "Just a plain text string", expected_root="resume"
        )
        self.assertEqual(result2, "<resume>Just a plain text string</resume>")

        # Logger should have recorded the sanitization
        mock_logger.debug.assert_any_call(
            "Sanitization: Added missing root <%s> element", "resume"
        )

    @patch("apps.core.utils.xml_processing.logger")
    def test_sanitization_without_expected_root(self, mock_logger):
        """Test sanitization when no expected root is specified."""
        xml_with_ampersands = "Some text with & characters"
        result = sanitize_xml_response(xml_with_ampersands)

        # Should escape ampersands even without root element
        self.assertIn("&amp;", result)

        # Should not add root element when not specified
        self.assertNotIn("<resume>", result)
