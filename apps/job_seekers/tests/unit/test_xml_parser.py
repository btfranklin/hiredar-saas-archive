"""Tests for the XML parsing helpers in job_seekers.services.recommendation."""

from django.test import SimpleTestCase

from apps.job_seekers.services.recommendation.xml_parser import (
    parse_role_recommendations_xml,
    parse_talent_sheet_xml,
)


class RoleRecommendationXMLParserTests(SimpleTestCase):
    """Pure function tests – no database interaction required."""

    def setUp(self):
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

    def test_parse_valid_xml(self):
        recommendations = parse_role_recommendations_xml(self.valid_xml)
        self.assertEqual(len(recommendations), 2)
        self.assertEqual(recommendations[0].role_title, "Software Engineer")
        self.assertEqual(recommendations[1].description, "Manage infrastructure")

    def test_missing_tags_raise_error(self):
        with self.assertRaises(ValueError):
            parse_role_recommendations_xml("<nope></nope>")


class TalentSheetXMLParserTests(SimpleTestCase):
    """Tests for talent sheet XML parsing."""

    def test_parse_valid_xml(self):
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

    def test_missing_required_fields_raise(self):
        # No promotional_blurb
        xml = (
            "<talent_sheet>"
            "<experience_overview>Python</experience_overview>"
            "</talent_sheet>"
        )
        with self.assertRaises(ValueError):
            parse_talent_sheet_xml(xml)

    def test_missing_xml_envelope_raises(self):
        with self.assertRaises(ValueError):
            parse_talent_sheet_xml("<foo></foo>")
