"""Pure text-to-Markdown and database-save tests for the component editor."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from component_editor import markdown_to_plain_text, plain_text_to_markdown  # noqa: E402


def test_plain_text_round_trips_without_interpreting_markdown_punctuation():
    plain = (
        "# A heading-like line with *literal emphasis* and [brackets].\n"
        "A list-like 1. entry, a | pipe, and {{Fee | money-words}}.\n\n"
        "Literal {braces}, a backslash \\, and a code span marker "
        + chr(96) + "literal text" + chr(96) + "."
    )
    markdown = plain_text_to_markdown(plain)
    assert r"\# A heading-like line with \*literal emphasis\* and \[brackets]." in markdown
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
