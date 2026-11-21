import pytest
from docx import Document

import core

from component_editor.conditional_walkthrough import (
    build_conditional_text, build_optional_text, parse_conditional_text,
)


def test_beaux_publisher_example_lists_each_choice_and_keeps_spacing():
    text = build_conditional_text(
        "Publisher Type",
        ["Non-profit", "Sole proprietor"],
        {
            "Non-profit": "a non-profit corporation",
            "Sole proprietor": "a sole proprietor",
        },
    )
    assert text == (
        "{{#if Publisher Type = Non-profit}}a non-profit corporation{{/if}} "
        "{{#if Publisher Type = Sole proprietor}}a sole proprietor{{/if}}"
    )
    assert " else " not in text
    assert "{{#if Publisher Type =" in text


@pytest.mark.parametrize("values", [
    ["A", "B"],
    ["A", "B", "C"],
    ["A", "B", "C", "D"],
])
def test_two_three_and_four_choice_values(values):
    result = build_conditional_text(
        "Type", values, {value: "wording for " + value for value in values}
    )
    assert result.count("{{#if Type = ") == len(values)
    assert result.count("{{/if}}") == len(values)


def test_conditional_wording_can_be_placed_in_a_list_item(tmp_path):
    result = build_conditional_text(
        "Publisher Type", ["Company", "Individual"],
        {"Company": "a company", "Individual": "an individual"},
    )
    source = tmp_path / "list.docx"
    document = Document()
    document.add_paragraph("formed as " + result, style="List Bullet")
    document.save(source)
    template = core.Template(source)
    assert template.problems == []
    assert "Publisher Type" in template.fields


def test_same_field_can_be_used_in_more_than_one_component():
    one = build_conditional_text("Publisher Type", ["Company", "Individual"],
        {"Company": "a company", "Individual": "an individual"})
    two = build_conditional_text("Publisher Type", ["Company", "Individual"],
        {"Company": "the company", "Individual": "the individual"})
    assert "Publisher Type" in one and "Publisher Type" in two


@pytest.mark.parametrize("value, expected", [
    ("Company", "a company"),
    ("Individual", "an individual"),
])
def test_each_choice_has_its_own_wording(value, expected):
    result = build_conditional_text("Type", ["Company", "Individual"],
        {"Company": "a company", "Individual": "an individual"})
    assert "{{#if Type = " + value + "}}" + expected + "{{/if}}" in result


def test_separate_paragraph_markers_are_on_their_own_lines():
    result = build_conditional_text("Type", ["A", "B"], {"A": "first", "B": "second"},
                                    "As separate paragraphs")
    assert result == (
        "{{#if Type = A}}\nfirst\n{{/if}}\n\n"
        "{{#if Type = B}}\nsecond\n{{/if}}"
    )


def test_optional_and_only_if_blank_variants():
    optional = build_optional_text("Include Rider", "The rider applies.")
    blank = build_optional_text("Guarantor", "No guarantor is named.",
                                only_if_blank=True)
    assert optional == "{{#if Include Rider}}\n\nThe rider applies.\n\n{{/if}}"
    assert blank == "{{#if not Guarantor}}\n\nNo guarantor is named.\n\n{{/if}}"


def test_rejects_missing_or_duplicate_values():
    with pytest.raises(ValueError, match="at least two"):
        build_conditional_text("Type", ["A"], {"A": "one"})
    with pytest.raises(ValueError, match="unique"):
        build_conditional_text("Type", ["A", "a"], {"A": "one", "a": "two"})
    with pytest.raises(ValueError, match="Add wording"):
        build_conditional_text("Type", ["A", "B"], {"A": "one"})


@pytest.mark.parametrize("choice, expected", [
    ("Non-profit", "of Acme, a non-profit corporation organized"),
    ("Sole proprietor", "of Acme, a sole proprietor organized"),
])
def test_each_choice_renders_with_single_spaces(tmp_path, choice, expected):
    wording = build_conditional_text(
        "Publisher Type",
        ["Non-profit", "Sole proprietor"],
        {"Non-profit": "a non-profit corporation", "Sole proprietor": "a sole proprietor"},
    )
    source = tmp_path / "template.docx"
    document = Document()
    document.add_paragraph("of Acme, " + wording + " organized")
    document.save(source)
    template = core.Template(source)
    assert template.problems == []
    output = tmp_path / "filled.docx"
    core.build_contract(template, {"Publisher Type": choice}, output)
    assert Document(output).paragraphs[0].text == expected


def test_existing_explicit_blocks_can_be_reopened():
    source = (
        "{{#if Publisher Type = Non-profit}}a non-profit corporation{{/if}} "
        "{{#if Publisher Type = Sole proprietor}}a sole proprietor{{/if}}"
    )
    assert parse_conditional_text(source) == (
        "Publisher Type",
        ["Non-profit", "Sole proprietor"],
        ["a non-profit corporation", "a sole proprietor"],
    )


def test_hand_typed_else_block_is_not_rewritten_as_a_choice_set():
    source = "{{#if Publisher Type = Non-profit}}a corporation{{else}}a person{{/if}}"
    with pytest.raises(ValueError, match="complete choice-wording block"):
        parse_conditional_text(source)
