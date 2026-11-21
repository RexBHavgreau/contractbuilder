"""Copying out of the editor gives the text as shown (T-051-A). Invented wording only."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from component_editor.copy_text import visible_text  # noqa: E402
from component_editor.text_rules import plain_text_to_markdown  # noqa: E402


def test_escaped_punctuation_is_shown_without_backslashes():
    assert visible_text(r"\(hereinafter the proprietor\)") == "(hereinafter the proprietor)"


def test_bold_next_to_an_escaped_bracket_keeps_its_text_intact():
    # The case reported on 2026-11-20: a marker must never leave a stray backslash.
    assert visible_text(r"\(hereinafter the **proprietor**\)") == "(hereinafter the proprietor)"
    assert visible_text(r"\(hereinafter the **proprietor\)**") == "(hereinafter the proprietor)"


def test_emphasis_markers_are_removed():
    assert visible_text("The **Provider** agrees _reasonably_ and *promptly*.") == (
        "The Provider agrees reasonably and promptly."
    )


def test_fields_and_conditional_markers_are_kept_as_written():
    source = "Pay {{Fee | money-words}} {{#if Publisher Type = Non-profit}}waived{{else}}due{{/if}}."
    assert visible_text(source) == source


def test_a_field_inside_bold_keeps_its_exact_spelling():
    assert visible_text("Pay **{{Fee | money-words}}** now.") == "Pay {{Fee | money-words}} now."


def test_headings_lose_their_markers():
    assert visible_text("# Title\n\nBody text.") == "Title\n\nBody text."


def test_bullet_and_numbered_lists_keep_visible_labels():
    assert visible_text("- First\n- Second") == "• First\n• Second"
    assert visible_text("1. Alpha\n2. Beta") == "1. Alpha\n2. Beta"


def test_nested_list_is_indented():
    assert visible_text("- Outer\n  - Inner") == "• Outer\n  • Inner"


def test_hard_line_break_becomes_a_newline():
    assert visible_text("Line one  \nLine two") == "Line one\nLine two"


def test_table_cells_are_tab_separated_rows():
    source = "| Item | Amount |\n| --- | --- |\n| Rent | {{Fee}} |"
    assert visible_text(source) == "Item\tAmount\nRent\t{{Fee}}"


def test_escaped_literal_markup_is_shown_as_typed():
    assert visible_text(r"Literal \*stars\* and 1\. not a list") == "Literal *stars* and 1. not a list"


def test_plain_text_survives_a_round_trip_through_the_stored_form():
    plain = (
        "Fees (as agreed) are 5 * 3 = 15 [see note] | pipe {braces}.\n\n"
        "# Not a heading and _not emphasis_."
    )
    assert visible_text(plain_text_to_markdown(plain)) == plain


def test_non_text_is_refused():
    import pytest
    with pytest.raises(TypeError):
        visible_text(None)
