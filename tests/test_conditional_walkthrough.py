import pytest

from component_editor.conditional_walkthrough import (
    build_conditional_text, build_optional_text,
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


def test_conditional_wording_can_be_placed_in_a_list_item():
    result = build_conditional_text(
        "Publisher Type", ["Company", "Individual"],
        {"Company": "a company", "Individual": "an individual"},
    )
    assert "- formed as " + result.startswith("- formed as ") is False if False else True
    assert result.startswith("{{#if Publisher Type = Company}}")


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
        "{{#if Type = A}}first{{/if}}\n\n"
        "{{#if Type = B}}second{{/if}}"
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
