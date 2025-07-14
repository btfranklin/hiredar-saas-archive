"""Unit tests for hiredar.llm.xml_utils.sanitize_xml_response"""

from hiredar.llm.xml_utils import sanitize_xml_response


def test_add_root_and_escape_ampersand() -> None:
    xml_without_root = "<name>John & Jane</name>"
    cleaned = sanitize_xml_response(xml_without_root, expected_root="resume")

    assert cleaned.startswith("<resume>")
    assert cleaned.endswith("</resume>")
    # ampersand should be escaped
    assert "&amp;" in cleaned


def test_remove_markdown_code_block() -> None:
    markdown_xml = """```xml\n<resume><summary>Hi</summary></resume>\n```"""
    cleaned = sanitize_xml_response(markdown_xml, expected_root="resume")

    assert "```" not in cleaned
    assert cleaned.startswith("<resume>")
