"""Tests for the component editor's lightweight Markdown preview."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from component_preview import render_markdown_preview  # noqa: E402


def _rendered(markdown):
    segments = render_markdown_preview(markdown)
    return "".join(text for text, _tags in segments), segments


def test_preview_styles_headings_emphasis_lists_and_fields():
    markdown = (
        "# Services Agreement\n\n"
        "The **Provider** agrees to act *reasonably* under {{Applicable Law}}.\n\n"
        "- First obligation\n"
        "- Second obligation\n\n"
        "1. Initial notice\n"
        "2. Final notice"
    )
    text, segments = _rendered(markdown)
    styles = {tag for _value, tags in segments for tag in tags}

    assert "Services Agreement" in text
    assert "Provider" in text
    assert "reasonably" in text
    assert "• First obligation" in text
    assert "• Second obligation" in text
    assert "1. Initial notice" in text
    assert "2. Final notice" in text
    assert "{{Applicable Law}}" in text
    assert "heading_1" in styles
    assert "bold" in styles
    assert "italic" in styles
    assert "list_marker" in styles
    assert "field" in styles


def test_preview_renders_tables_as_aligned_text_and_protects_field_pipes():
    markdown = (
        "| Term | Example |\n"
        "| --- | --- |\n"
        "| Payment | {{Payment Period | number}} days |\n"
        "| Governing law | Texas |"
    )
    text, segments = _rendered(markdown)
    styles = {tag for _value, tags in segments for tag in tags}

    assert "| Term" in text
    assert "Payment" in text
    assert "{{Payment Period | number}}" in text
    assert "Governing law" in text
    assert "Texas" in text
    assert "table_header" in styles
    assert "table_cell" in styles
    assert "table_border" in styles
    assert "field" in styles


def test_preview_uses_safe_plain_text_for_untrusted_html_and_code():
    markdown = (
        "Contract wording remains ordinary text.\n\n"
        "<script>alert('not executable')</script>\n\n"
        "    {{Field}}\n"
    )
    text, segments = _rendered(markdown)
    assert "Contract wording remains ordinary text." in text
    assert "{{Field}}" in text
    assert "<script>alert('not executable')</script>" in text
    assert any("code_block" in tags for _value, tags in segments)
    assert any("field" in tags for _value, tags in segments if "{{Field}}" in _value)
