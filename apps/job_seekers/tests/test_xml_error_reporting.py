"""
Unit tests for the XML error reporting utilities.

Tests the XML error reporting functions used to diagnose and format XML parsing errors.
"""

import os
import tempfile
import xml.etree.ElementTree as ET
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.job_seekers.utils.resume_processing.xml_error_reporting import (
    create_marked_xml,
    format_error_for_console,
    get_error_context,
    get_error_position,
    log_xml_error,
    save_diagnostic_xml,
)


class MockParseError(ET.ParseError):
    """Mock ParseError class for testing that allows setting position directly."""

    def __init__(self, msg: str, position: tuple[int, int] | None = None):
        super().__init__(msg)
        # We need to set position as it would be in a real ET.ParseError
        self._position = position

    @property
    def position(self) -> tuple[int, int] | None:
        """Get the error position."""
        return self._position


class XMLErrorReportingTests(SimpleTestCase):
    """
    Test cases for the XML error reporting utilities.

    Tests various functions used to handle, format, and report XML parsing errors:
    - Position extraction from parse errors
    - Context gathering around error locations
    - Formatting of errors for console output
    - Logging of XML errors
    - Creation of marked XML with error indicators
    - Saving diagnostic XML files
    """

    def setUp(self):
        """Set up test data for each test method."""
        self.test_xml = """<resume>
  <personal>
    <name>John Doe</name>
    <email>john.doe@example.com</email>
    <phone>123-456-7890</phone>
  </personal>
  <summary>A skilled software engineer with experience in Python and Django</summary>
  <skills>
    <skill>Python</skill>
    <skill>Django</skil>  <!-- Missing closing tag -->
    <skill>JavaScript</skill>
  </skills>
</resume>"""
        self.error = MockParseError("mismatched tag: line 9, column 12", (9, 12))

    def test_get_error_position(self):
        """Test extracting line and column position from parse error."""
        # Test with error that has position
        self.assertEqual(get_error_position(self.error), (9, 12))

        # Test with error that doesn't have position
        error_no_pos = MockParseError("generic error")
        self.assertIsNone(get_error_position(error_no_pos))

    def test_get_error_context(self):
        """Test getting context lines around an error position in XML."""
        context = get_error_context(self.test_xml, 10, 12, context_lines=1)

        # Check result has expected structure
        self.assertEqual(context["error_line_no"], 10)
        self.assertEqual(context["error_col_no"], 12)
        self.assertEqual(
            context["error_line"],
            "    <skill>Django</skil>  <!-- Missing closing tag -->",
        )

        # Check context lines
        self.assertEqual(len(context["context_lines"]), 3)
        self.assertEqual(context["context_lines"][1]["line_no"], 10)
        self.assertTrue(context["context_lines"][1]["is_error_line"])

    def test_format_error_for_console(self):
        """Test formatting XML errors for console display with visual indicators."""
        lines = format_error_for_console(self.error, self.test_xml)

        # Check that output contains expected information
        self.assertTrue(any("XML Error: mismatched tag" in line for line in lines))
        self.assertTrue(any("Error at line 9, column 12" in line for line in lines))
        self.assertTrue(any("HERE" in line for line in lines))

        # Test with error that doesn't have position
        error_no_pos = MockParseError("generic error")
        lines_no_pos = format_error_for_console(error_no_pos, self.test_xml)
        self.assertTrue(
            any("Error position not available" in line for line in lines_no_pos)
        )

    @patch("apps.job_seekers.utils.resume_processing.xml_error_reporting.logger")
    def test_log_xml_error(self, mock_logger):
        """Test logging of XML errors with proper formatting."""
        log_xml_error(self.error, self.test_xml)

        # Check that logger was called with expected messages
        self.assertTrue(mock_logger.error.called)
        # First call should contain error message
        self.assertIn("XML Error", mock_logger.error.call_args_list[0][0][0])

    def test_create_marked_xml(self):
        """Test creation of XML with visual error markers for diagnostics."""
        marked_xml = create_marked_xml(self.error, self.test_xml)

        # Check that output contains error markers
        self.assertIn("<!-- XML PARSING ERROR:", marked_xml)
        self.assertIn("❌", marked_xml)

        # Test with error that doesn't have position
        error_no_pos = MockParseError("generic error")
        marked_xml_no_pos = create_marked_xml(error_no_pos, self.test_xml)
        self.assertIn(
            "<!-- XML ERROR: generic error (position unknown) -->", marked_xml_no_pos
        )

    def test_save_diagnostic_xml(self):
        """Test saving diagnostic XML to file with error annotations."""
        # Create a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test_resume.pdf")
            # Touch the file to make sure it exists
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("Test file")

            # Save diagnostic XML
            diagnostic_path = save_diagnostic_xml(
                self.error, self.test_xml, test_file, "test"
            )

            # Check that file was created and contains expected content
            self.assertIsNotNone(diagnostic_path)
            if diagnostic_path:  # Type narrowing for the linter
                self.assertTrue(os.path.exists(diagnostic_path))

                with open(diagnostic_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    self.assertIn("<!-- XML PARSING ERROR:", content)
                    self.assertIn("❌", content)
