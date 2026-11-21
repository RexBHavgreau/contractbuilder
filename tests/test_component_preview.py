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

def test_preview_highlights_fields_inside_inline_code_and_emphasis():
    text, segments = _rendered(
        "Use `{{Payment Period | number}}` and **{{Governing Law}}**."
    )
    assert "{{Payment Period | number}}" in text
    assert "{{Governing Law}}" in text
    assert any(
        "field" in tags and "code" in tags
        for value, tags in segments
        if "{{Payment Period | number}}" in value
    )
    assert any(
        "field" in tags and "bold" in tags
        for value, tags in segments
        if "{{Governing Law}}" in value
    )


 
def test_nested_numbered_preview_uses_computed_decimal_outline():
    text, _segments = _rendered(
        "1. Parent\n"
        "    1. Child\n"
        "        1. Grandchild\n"
        "    1. Next child\n"
        "2. Next parent"
    )
    assert "1. Parent" in text
    assert "1.1. Child" in text
    assert "1.1.1. Grandchild" in text
    assert "1.2. Next child" in text
    assert "2. Next parent" in text


def test_conditional_markers_show_plain_words_not_field_syntax():
    text, segments = _rendered(
        "Fees are {{#if Publisher Type = Non-profit}}waived{{else}}due{{/if}} here."
    )
    assert "{{" not in text and "}}" not in text
    assert "If Publisher Type is Non-profit" in text
    assert "Otherwise" in text
    assert "End of choice" in text
    marker_tags = {tag for _value, tags in segments for tag in tags if tag.startswith("marker")}
    assert {"marker", "marker_if", "marker_else", "marker_end"} <= marker_tags
    assert "field" not in {tag for _value, tags in segments for tag in tags if _value.startswith("If")}


def test_negated_and_filled_in_conditions_have_plain_wording():
    text, _segments = _rendered(
        "{{#if not Governing State = Texas}}A{{/if}} {{#if Client Name}}B{{/if}}"
    )
    assert "If Governing State is not Texas" in text
    assert "If Client Name is filled in" in text


def test_block_form_marker_is_a_marker_on_its_own_line():
    text, segments = _rendered(
        "Intro.\n\n{{#if Include Schedule}}\n\nSchedule text.\n\n{{/if}}\n\nEnd."
    )
    assert "If Include Schedule is filled in" in text
    assert "End of choice" in text
    assert "Schedule text." in text
    assert "{{#if" not in text


def test_field_inside_conditional_text_stays_a_field():
    text, segments = _rendered(
        "{{#if Publisher Type = Non-profit}}Pay {{Fee | money-words}}.{{/if}}"
    )
    field_text = [value for value, tags in segments if "field" in tags]
    assert field_text == ["{{Fee | money-words}}"]
    marker_text = [value.strip("\u2009") for value, tags in segments if "marker" in tags]
    assert marker_text == ["If Publisher Type is Non-profit", "End of choice"]


def test_optional_clause_in_a_table_cell_is_labelled():
    text, _segments = _rendered(
        "| Item | Note |\n| --- | --- |\n| Fee | {{#if Rush}}Rush fee{{/if}} |"
    )
    assert "If Rush is filled in" in text
    assert "{{#if" not in text


def test_fields_are_still_highlighted_and_unchanged():
    text, segments = _rendered("Pay {{Applicable Law}} now.")
    assert ("{{Applicable Law}}", ("field",)) in segments
    assert "{{Applicable Law}}" in text


def test_preview_key_explains_both_styles():
    from component_preview import PREVIEW_KEY
    assert "Highlighted" in PREVIEW_KEY and "Grey tags" in PREVIEW_KEY
    assert "not printed" in PREVIEW_KEY



def test_preview_distinguishes_safe_hyperlinks_from_unsupported_targets():
    text, segments = _rendered(
        "[Official site](https://example.com/terms) and "
        "[legacy link](ftp://example.com/file)."
    )
    assert "Official site" in text
    assert "legacy link" in text
    assert any(value == "Official site" and "link" in tags for value, tags in segments)
    assert any(
        value == "legacy link" and "link_warning" in tags
        for value, tags in segments
    )
