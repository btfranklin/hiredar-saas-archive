"""Tests for the XML parsing helpers in job_seekers.services.recommendation."""

from django.test import SimpleTestCase

from apps.job_seekers.services.recommendation.xml_parser import (
    parse_role_recommendations_xml,
    parse_talent_sheet_xml,
)


class RoleRecommendationXMLParserTests(SimpleTestCase):
    """Pure function tests – no database interaction required."""

    def setUp(self) -> None:
        """Provide a canonical XML payload for role recommendations."""
        self.valid_xml = (
            "<role_recommendations>"
            "<role_recommendation>"
            "<title>Software Engineer</title>"
            "<description>Build backend APIs</description>"
            "</role_recommendation>"
            "<role_recommendation>"
            "<title>DevOps Engineer</title>"
            "<description>Manage infrastructure</description>"
            "</role_recommendation>"
            "</role_recommendations>"
        )

    def test_parse_valid_xml(self) -> None:
        """Return parsed role recommendations when XML is valid."""
        recommendations = parse_role_recommendations_xml(self.valid_xml)
        self.assertEqual(len(recommendations), 2)
        self.assertEqual(recommendations[0].role_title, "Software Engineer")
        self.assertEqual(recommendations[1].description, "Manage infrastructure")

    def test_missing_tags_raise_error(self) -> None:
        """Raise ValueError when expected tags are missing."""
        with self.assertRaises(ValueError):
            parse_role_recommendations_xml("<nope></nope>")

    def test_control_chars_and_ampersands_are_handled(self) -> None:
        """Sanitise control characters and preserve escaped ampersands."""
        # Control chars should be stripped and ampersands escaped, preserving text
        xml = (
            "<role_recommendations>"
            "<role_recommendation>"
            "<title>AT&T\x07Example</title>"
            "<description>Test & More</description>"
            "</role_recommendation>"
            "</role_recommendations>"
        )
        recommendations = parse_role_recommendations_xml(xml)
        self.assertEqual(len(recommendations), 1)
        self.assertEqual(recommendations[0].role_title, "AT&TExample")
        self.assertEqual(recommendations[0].description, "Test & More")

    def test_malformed_xml_returns_empty_list(self) -> None:
        """Return an empty list when the payload cannot be parsed."""
        # Missing closing envelope should not raise, but return empty list
        xml = (
            "<role_recommendations>"
            "<role_recommendation>"
            "<title>Foo</title>"
            "<description>Bar</description>"
            "</role_recommendation>"
            # no closing </role_recommendations>
        )
        recommendations = parse_role_recommendations_xml(xml)
        self.assertEqual(recommendations, [])


class TalentSheetXMLParserTests(SimpleTestCase):
    """Tests for talent sheet XML parsing."""

    def test_parse_valid_xml(self) -> None:
        """Parse a valid talent sheet payload into an object."""
        xml = (
            "<talent_sheet>"
            "<promotional_blurb>Amazing candidate</promotional_blurb>"
            "<experience_overview>Chief Researcher (2015-2017): Discovered six new biological compounds and managed five direct reports.</experience_overview>"
            "<ideal_roles>Backend Dev, API Engineer</ideal_roles>"
            "<salary_min>95000</salary_min>"
            "</talent_sheet>"
        )

        sheet = parse_talent_sheet_xml(xml)

        self.assertEqual(sheet.promotional_blurb, "Amazing candidate")
        self.assertEqual(
            sheet.experience_overview,
            "Chief Researcher (2015-2017): Discovered six new biological compounds and managed five direct reports.",
        )
        self.assertEqual(sheet.ideal_roles, "Backend Dev, API Engineer")
        # salary_min is stored as a float by the parser; assert approximate equality
        self.assertAlmostEqual(float(sheet.salary_min), 95000.0)

    def test_missing_required_fields_raise(self) -> None:
        """Raise when required fields such as promotional_blurb are absent."""
        # No promotional_blurb
        xml = (
            "<talent_sheet>"
            "<experience_overview>Python</experience_overview>"
            "</talent_sheet>"
        )
        with self.assertRaises(ValueError):
            parse_talent_sheet_xml(xml)

    def test_missing_xml_envelope_raises(self) -> None:
        """Raise when the talent sheet root element is missing."""
        with self.assertRaises(ValueError):
            parse_talent_sheet_xml("<foo></foo>")
