"""Pure text-to-Markdown and database-save tests for the component editor."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from component_editor import (  # noqa: E402
    markdown_to_plain_text,
    plain_text_to_markdown,
    save_feedback_text,
)


def test_plain_text_round_trips_without_interpreting_markdown_punctuation():
    plain = (
        "# A heading-like line with *literal emphasis* and [brackets].\n"
        "A list-like 1. entry, a | pipe, and {{Fee | money-words}}.\n\n"
        "Literal {braces}, a backslash \\, and a code span marker "
        + chr(96) + "literal text" + chr(96) + "."
    )
    markdown = plain_text_to_markdown(plain)
    assert r"\# A heading-like line with \*literal emphasis\* and \[brackets\]." in markdown
    assert "{{Fee | money-words}}" in markdown
    assert r"\|" in markdown
    assert markdown_to_plain_text(markdown) == plain


def test_plain_text_converter_preserves_paragraphs_and_line_breaks():
    plain = "First line\nsecond line\n\nA second paragraph."
    markdown = plain_text_to_markdown(plain)
    assert markdown == "First line  \nsecond line\n\nA second paragraph."
    assert markdown_to_plain_text(markdown) == plain

def test_plain_text_converter_escapes_list_markers_but_not_ordinary_punctuation():
    plain = (
        "- A literal bullet\n"
        "1. A literal numbered item\n"
        "+ A literal plus item\n"
        "* A literal star item\n"
        "---\n"
        "Ordinary hyphens - and periods 1.2 stay readable."
    )
    markdown = plain_text_to_markdown(plain)
    assert markdown.startswith(
        "\\- A literal bullet  \n"
        "1\\. A literal numbered item  \n"
    )
    assert r"\+ A literal plus item" in markdown
    assert r"\* A literal star item" in markdown
    assert r"\---" in markdown
    assert "Ordinary hyphens - and periods 1.2 stay readable." in markdown
    assert markdown_to_plain_text(markdown) == plain


def test_table_grid_round_trips_literal_and_field_pipes():
    from component_editor import build_markdown_table, find_markdown_table

    rows = [
        ["Term", "Value"],
        ["A | B", "{{Fee | money-words}}"],
    ]
    markdown = build_markdown_table(rows)
    assert r"A \| B" in markdown
    assert "{{Fee | money-words}}" in markdown
    found = find_markdown_table(markdown, markdown.index("Fee"))
    assert found is not None
    assert found["rows"] == rows
    assert build_markdown_table(found["rows"], alignments=found["alignments"]) == markdown


def test_field_placeholder_builder_uses_the_core_format_parser():
    from component_editor import make_field_placeholder
    import pytest

    assert make_field_placeholder("Client Name") == "{{Client Name}}"
    assert make_field_placeholder("Fee", "money-words") == "{{Fee | money-words}}"
    assert make_field_placeholder("Service", "choice", "repair, consulting") == (
        "{{Service | choice: repair, consulting}}"
    )
    assert make_field_placeholder("Book", "plural", "work, works") == (
        "{{Book | plural: work, works}}"
    )
    with pytest.raises(ValueError, match="two wordings"):
        make_field_placeholder("Book", "plural", "works")
    with pytest.raises(ValueError, match="at least one option"):
        make_field_placeholder("Service", "choice", "")


def test_malformed_field_marker_is_reported_with_line_number():
    from component_editor import malformed_field_message

    assert malformed_field_message("Normal text\n{{Broken field") == (
        "Check the field placeholder on line 2: its double braces do not match. "
        "A field should look like {{Field Name}}."
    )
    assert malformed_field_message("{{Fee | money}} and {{#if Include}}") is None


def test_toolbar_formats_lists_and_decimal_outline_levels():
    from component_editor import format_markdown_block

    assert format_markdown_block("Clause", "heading", 2) == "## Clause"
    assert format_markdown_block("Clause", "bullet") == "- Clause"
    assert format_markdown_block("Clause", "numbered") == "1. Clause"
    assert format_markdown_block(
        "1. Child", "indent", previous_text="1. Parent"
    ) == "    1. Child"
    assert format_markdown_block("1. First item", "indent") == "1. First item"
    assert format_markdown_block("    1. Child", "outdent") == "1. Child"


def test_save_feedback_says_what_was_saved():
    assert save_feedback_text("saved", name="Invented Clause", version=3) == (
        "Saved Invented Clause · version 3."
    )


def test_save_feedback_includes_the_version_note():
    text = save_feedback_text("saved", name="Invented Clause", version=4, note="  Tidied wording ")
    assert text == "Saved Invented Clause · version 4. Version note: Tidied wording"


def test_save_feedback_for_nothing_to_save_names_the_current_version():
    assert save_feedback_text("unchanged", name="Invented Clause", version=2) == (
        "Nothing to save. Invented Clause is already saved as version 2."
    )


def test_save_feedback_for_a_failed_save_gives_the_reason_or_a_default():
    assert save_feedback_text("failed", error="Enter a component name.") == (
        "Not saved. Enter a component name."
    )
    assert save_feedback_text("failed", error="   ") == (
        "Not saved. Something went wrong. Try again."
    )


def test_save_feedback_rejects_an_unknown_outcome():
    import pytest
    with pytest.raises(ValueError):
        save_feedback_text("maybe")
