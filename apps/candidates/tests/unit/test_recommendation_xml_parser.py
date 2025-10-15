"""Tests for the candidate recommendation XML parsers."""

from django.test import SimpleTestCase

from apps.candidates.services.recommendation.xml_parser import (
    CandidateProfileEnrichment,
    parse_profile_enrichment_xml,
    parse_role_recommendations_xml,
)


class CandidateRoleRecommendationXMLParserTests(SimpleTestCase):
    """Validate XML parsing for role recommendations."""

    def setUp(self) -> None:
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
        recommendations = parse_role_recommendations_xml(self.valid_xml)
        self.assertEqual(len(recommendations), 2)
        self.assertEqual(recommendations[0].role_title, "Software Engineer")
        self.assertEqual(recommendations[1].description, "Manage infrastructure")

    def test_missing_tags_raise_error(self) -> None:
        with self.assertRaises(ValueError):
            parse_role_recommendations_xml("<nope></nope>")

    def test_malformed_xml_returns_empty_list(self) -> None:
        xml = (
            "<role_recommendations>"
            "<role_recommendation>"
            "<title>Foo</title>"
            "<description>Bar</description>"
            "</role_recommendation>"
        )
        recommendations = parse_role_recommendations_xml(xml)
        self.assertEqual(recommendations, [])


class CandidateProfileEnrichmentXMLParserTests(SimpleTestCase):
    """Validate parsing for talent-sheet style enrichment responses."""

    def test_parse_valid_xml(self) -> None:
        xml = (
            "<talent_sheet>"
            "<promotional_blurb>Amazing candidate</promotional_blurb>"
            "<experience_overview>"
            "<experience>"
            "<position>Engineer</position>"
            "<dates>2021-2023</dates>"
            "<impact>Improved build times</impact>"
            "</experience>"
            "</experience_overview>"
            "<ideal_roles>Backend Dev, API Engineer</ideal_roles>"
            "</talent_sheet>"
        )

        enrichment = parse_profile_enrichment_xml(xml)
        self.assertIsInstance(enrichment, CandidateProfileEnrichment)
        self.assertEqual(enrichment.promotional_blurb, "Amazing candidate")
        self.assertIn("Engineer", enrichment.experience_overview)
        self.assertEqual(enrichment.ideal_roles, "Backend Dev, API Engineer")

    def test_missing_required_fields_raise(self) -> None:
        xml = (
            "<talent_sheet>"
            "<experience_overview>Experience</experience_overview>"
            "</talent_sheet>"
        )
        with self.assertRaises(ValueError):
            parse_profile_enrichment_xml(xml)

    def test_missing_envelope_raises(self) -> None:
        with self.assertRaises(ValueError):
            parse_profile_enrichment_xml("<foo></foo>")
