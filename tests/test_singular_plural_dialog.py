"""Tests for singular/plural wording tied to a reusable List field."""
from io import BytesIO

from docx import Document
import pytest

import core
from component_editor.singular_plural_dialog import build_singular_plural_placeholder


def test_plural_placeholder_uses_existing_list_field_and_plain_separator():
    assert build_singular_plural_placeholder("Works", "work", "works") == (
        "{{Works | plural: work, works}}"
    )


def test_plural_placeholder_uses_slash_when_either_word_contains_a_comma():
    assert build_singular_plural_placeholder(
        "Works", "work, as described", "works, as described"
    ) == "{{Works | plural: work, as described / works, as described}}"
    assert build_singular_plural_placeholder(
        "Works", "work", "works, collectively"
    ) == "{{Works | plural: work / works, collectively}}"


def test_plural_placeholder_preserves_capitalization():
    assert build_singular_plural_placeholder(
        "Published Works", "Volume", "Volumes"
    ) == "{{Published Works | plural: Volume, Volumes}}"


@pytest.mark.parametrize(
    ("field_name", "singular", "plural", "message"),
    [
        ("", "work", "works", "Choose a List field"),
        ("Works", "", "works", "both the singular and plural"),
        ("Works", "work", "", "both the singular and plural"),
        ("Bad{{Field}}", "work", "works", "valid List field name"),
        ("Works", "work and\nmore", "works", "single line"),
    ],
)
def test_plural_placeholder_rejects_incomplete_or_unsafe_values(
    field_name, singular, plural, message
):
    with pytest.raises(ValueError, match=message):
        build_singular_plural_placeholder(field_name, singular, plural)


def test_same_list_field_can_be_printed_and_counted_in_one_component(tmp_path):
    source = tmp_path / "works.docx"
    document = Document()
    document.add_paragraph(
        "The {{Works | list}} include {{Works | plural: work, works}}."
    )
    document.save(source)

    template = core.Template(source)
    assert template.problems == []
    field = template.field_list()[0]
    assert field.name == "Works"
    assert field.formats == ["list", "plural"]

    rendered, report = core.render(template, {"Works": "First volume\nSecond volume"})
    assert report.blanks == []
    assert Document(BytesIO(rendered)).paragraphs[0].text == (
        "The First volume and Second volume include works."
    )
