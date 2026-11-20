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


def test_toolbar_wrap_keeps_related_controls_together_when_they_fit():
    from component_editor import wrap_toolbar_groups

    groups = [
        [("bold", 24), ("italic", 28), ("heading", 52)],
        [("bullets", 48), ("numbering", 62), ("indent", 74)],
        [("table", 38), ("field", 38)],
    ]
    rows = wrap_toolbar_groups(groups, available_width=120, gap=4)
    flattened = [name for row in rows for name, _width in row]
    assert flattened == [
        "bold", "italic", "heading", "bullets", "numbering", "indent", "table", "field"
    ]
    assert [name for name, _width in rows[0]] == ["bold", "italic", "heading"]
    assert [name for name, _width in rows[-1]] == ["table", "field"]

    narrow = wrap_toolbar_groups(
        [[("small", 12), ("too-wide", 36), ("next", 14)]],
        available_width=20,
        gap=2,
    )
    assert narrow == [[("small", 12)], [("too-wide", 36)], [("next", 14)]]


def test_inline_format_toggles_and_preserves_the_other_emphasis():
    from component_editor import inline_format_active, toggle_inline_format

    source = "agreement"
    bold, start, end = toggle_inline_format(source, 0, len(source), "bold")
    assert bold == "**agreement**"
    assert bold[start:end] == "agreement"
    assert inline_format_active(bold, start, end, "bold")

    plain, start, end = toggle_inline_format(bold, start, end, "bold")
    assert plain == "agreement"
    assert plain[start:end] == "agreement"
    assert not inline_format_active(plain, start, end, "bold")

    combined, start, end = toggle_inline_format("**term**", 2, 6, "italic")
    assert combined == "***term***"
    assert inline_format_active(combined, start, end, "bold")
    assert inline_format_active(combined, start, end, "italic")

    bold_only, start, end = toggle_inline_format(combined, start, end, "italic")
    assert bold_only == "**term**"
    assert bold_only[start:end] == "term"

    raw_selection, start, end = toggle_inline_format(
        "**term**", 0, len("**term**"), "bold"
    )
    assert raw_selection == "term"
    assert raw_selection[start:end] == "term"

    raw_italic, start, end = toggle_inline_format(
        "**term**", 0, len("**term**"), "italic"
    )
    assert raw_italic == "***term***"
    assert raw_italic[start:end] == "term"
    bold_only, start, end = toggle_inline_format(
        raw_italic, start, end, "italic"
    )
    assert bold_only == "**term**"
    assert bold_only[start:end] == "term"

    mixed = "**already bold** and plain"
    normalized, start, end = toggle_inline_format(mixed, 0, len(mixed), "bold")
    assert normalized == "**already bold and plain**"
    assert normalized[start:end] == "already bold and plain"


def test_inline_format_does_not_rewrite_fields_or_escaped_markers():
    from component_editor import toggle_inline_format

    field = "{{Client Name}}"
    unchanged, start, end = toggle_inline_format(field, 0, len(field), "bold")
    assert unchanged == field
    assert (start, end) == (0, len(field))

    escaped_marker = r"\*"
    unchanged, start, end = toggle_inline_format(
        escaped_marker, 0, len(escaped_marker), "italic"
    )
    assert unchanged == escaped_marker
    assert (start, end) == (0, len(escaped_marker))

    escaped_text = r"\*literal\*"
    wrapped, start, end = toggle_inline_format(
        escaped_text, 0, len(escaped_text), "italic"
    )
    assert wrapped == r"*\*literal\**"
    assert r"\*literal\*" in wrapped
    assert wrapped[start:end] == escaped_text


def test_heading_and_list_controls_toggle_off_or_switch_type():
    from component_editor import format_markdown_block, markdown_block_state, toggle_markdown_block

    assert format_markdown_block("## Heading", "heading", 2) == "Heading"
    assert format_markdown_block("## Heading", "heading", 1) == "# Heading"
    assert format_markdown_block("## Heading", "normal") == "Heading"
    assert format_markdown_block("- Clause", "bullet") == "Clause"
    assert format_markdown_block("- Clause", "numbered") == "1. Clause"
    assert format_markdown_block("1. Clause", "numbered") == "Clause"

    source = "First clause\nSecond clause"
    bulleted, start, end = toggle_markdown_block(source, 0, len(source), "bullet")
    assert bulleted == "- First clause\n- Second clause"
    assert bulleted[start:end] == bulleted
    assert markdown_block_state(bulleted, start, end)["bullet"]

    numbered, start, end = toggle_markdown_block(
        bulleted, start, end, "numbered"
    )
    assert numbered == "1. First clause\n1. Second clause"
    assert markdown_block_state(numbered, start, end)["numbered"]

    plain, start, end = toggle_markdown_block(
        numbered, start, end, "numbered"
    )
    assert plain == source
    assert plain[start:end] == source


def test_pure_editor_modules_load_without_tkinter():
    """T-052: the text, table, field, toolbar-layout and save-feedback rules need no display."""
    import subprocess
    import textwrap

    script = textwrap.dedent(
        """
        import importlib.util, sys, types
        root = sys.argv[1]
        sys.path.insert(0, root)

        class NoTk:
            def find_spec(self, name, path=None, target=None):
                if name == "tkinter" or name.startswith("tkinter."):
                    raise ImportError("tkinter is blocked in this test")
                return None

        sys.meta_path.insert(0, NoTk())
        # Load submodules without running the package __init__, which builds the window.
        package = types.ModuleType("component_editor")
        package.__path__ = [root + "/component_editor"]
        sys.modules["component_editor"] = package
        for name in ("text_rules", "toolbar_layout", "tables", "fields", "save_feedback", "styling"):
            importlib.import_module("component_editor." + name)
        assert "tkinter" not in sys.modules
        print("ok")
        """
    )
    root = pathlib.Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-c", script, str(root)], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"
