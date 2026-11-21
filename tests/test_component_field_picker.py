"""Pure kind-to-syntax rules for the guided field creator."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import core
import pytest
from component_editor.field_picker import (
    build_created_field, field_definition_placeholder, field_kind_definition
)
from library import ComponentLibrary


@pytest.mark.parametrize(
    ("kind", "expected_format"),
    [
        ("Text", ""),
        ("Long text", "long"),
        ("Date", "date"),
        ("Amount of money", "money"),
        ("Number", "number"),
        ("List", "list"),
    ],
)
def test_plain_field_kinds_map_to_their_default_formats(kind, expected_format):
    definition = field_kind_definition(kind, "Contract Field")
    assert definition["default_format"] == expected_format
    assert build_created_field(definition, kind) == (
        "{{Contract Field}}" if not expected_format
        else "{{Contract Field | " + expected_format + "}}"
    )


def test_picker_preserves_legacy_stored_formats():
    definition = {
        "name": "Effective Date",
        "default_format": "date-formal",
        "default_options": [],
        "allowed_values": [],
    }
    assert field_definition_placeholder(definition) == (
        "{{Effective Date | date-formal}}"
    )


def test_choice_field_saves_allowed_values_and_inserts_default_choice_format():
    definition = field_kind_definition(
        "Choice", "Publisher Type", values=["Non-profit", "Sole proprietor"]
    )
    assert definition["default_format"] == "choice"
    assert definition["allowed_values"] == ["Non-profit", "Sole proprietor"]
    assert build_created_field(definition, "Choice") == (
        "{{Publisher Type | choice: Non-profit, Sole proprietor}}"
    )


def test_singular_plural_field_uses_slash_when_wording_contains_commas():
    definition = field_kind_definition(
        "Singular or plural word",
        "Titles",
        singular="it, as written",
        plural="them, as written",
    )
    assert definition["default_options"] == ["it, as written", "them, as written"]
    assert build_created_field(definition, "Singular or plural word") == (
        "{{Titles | plural: it, as written / them, as written}}"
    )


def test_optional_clause_builds_inline_or_paragraph_markers():
    definition = field_kind_definition("Optional clause", "Include Guarantee")
    assert build_created_field(
        definition, "Optional clause", "with a personal guarantee"
    ) == "{{#if Include Guarantee}}with a personal guarantee{{/if}}"
    paragraph = build_created_field(
        definition, "Optional clause", "7. Guarantee.\nThe guarantor agrees."
    )
    assert paragraph == (
        "{{#if Include Guarantee}}\n\n"
        "7. Guarantee.\nThe guarantor agrees.\n\n{{/if}}"
    )
    assert core.classify(core.TOKEN.fullmatch("{{#if Include Guarantee}}").group(1))[0] == "if"


def test_conditional_wording_creates_tight_blocks_for_sentence_or_paragraph():
    definition = field_kind_definition(
        "Conditional wording", "Publisher Type",
        values=["Non-profit", "Sole proprietor", "Corporation"],
    )
    wording = (
        "Corporation | a corporation\n"
        "Sole proprietor | a sole proprietor\n"
        "Non-profit | a non-profit corporation"
    )
    inline = build_created_field(definition, "Conditional wording", wording)
    assert inline == (
        "{{#if Publisher Type = Non-profit}}a non-profit corporation{{/if}} "
        "{{#if Publisher Type = Sole proprietor}}a sole proprietor{{/if}} "
        "{{#if Publisher Type = Corporation}}a corporation{{/if}}"
    )
    paragraphs = build_created_field(
        definition, "Conditional wording", wording, placement="As separate paragraphs"
    )
    assert paragraphs == (
        "{{#if Publisher Type = Non-profit}}a non-profit corporation{{/if}}\n\n"
        "{{#if Publisher Type = Sole proprietor}}a sole proprietor{{/if}}\n\n"
        "{{#if Publisher Type = Corporation}}a corporation{{/if}}"
    )
    tokens = list(core.TOKEN.finditer(inline))
    assert len(tokens) == 6
    assert all("{{#if " in token.group(0) and "}}" in token.group(0) for token in tokens[::2])
    assert all("{{/if}}" == token.group(0) for token in tokens[1::2])

def test_conditional_wording_requires_text_for_each_allowed_value():
    definition = field_kind_definition(
        "Conditional wording", "Publisher Type", values=["Non-profit", "Company"]
    )
    with pytest.raises(ValueError, match="Add wording for: Company"):
        build_created_field(definition, "Conditional wording", "Non-profit | an organization")


def test_choice_and_plural_require_their_values():
    with pytest.raises(ValueError, match="at least one choice"):
        field_kind_definition("Choice", "Publisher Type")
    with pytest.raises(ValueError, match="at least two choices"):
        field_kind_definition("Conditional wording", "Publisher Type", values=["One"])
    with pytest.raises(ValueError, match="both the singular and plural"):
        field_kind_definition("Singular or plural word", "Titles", singular="title")


def test_creator_fields_are_saved_under_your_fields_and_archive_from_picker(tmp_path):
    library = ComponentLibrary(tmp_path / "fields.sqlite3")
    definition = field_kind_definition(
        "Choice", "Publisher Type", "The legal structure.", ["Non-profit", "Company"]
    )
    field_id = library.add_field_definition(**definition)
    picker_fields = library.list_picker_fields()
    saved = next(field for field in picker_fields if field["name"] == "Publisher Type")
    assert saved["group"] == "Your fields"
    assert saved["allowed_values"] == ["Non-profit", "Company"]
    assert library.archive_field_definition(field_id)
    assert all(field["name"] != "Publisher Type" for field in library.list_picker_fields())
    assert library.get_field_definition(field_id)["status"] == "archived"


def test_field_creator_can_link_a_definition_to_a_publisher_profile_column(tmp_path):
    definition = field_kind_definition(
        "Text", "Rights Contact", publisher_profile_column="contact_name"
    )
    assert definition["publisher_profile_column"] == "contact_name"
    library = ComponentLibrary(tmp_path / "fields.sqlite3")
    field_id = library.add_field_definition(**definition)
    saved = library.get_field_definition(field_id)
    assert saved["publisher_profile_column"] == "contact_name"


def _window_or_skip():
    import os
    import tkinter as tk
    if os.name != "nt" and not os.environ.get("DISPLAY"):
        pytest.skip("Tk window tests need a display; CI runs window tests under xvfb-run.")
    root = tk.Tk()
    root.withdraw()
    return root


def test_field_creator_has_a_help_text_box_and_keeps_its_saved_help(tmp_path):
    from tkinter import ttk
    from component_editor.field_picker import FieldCreatorDialog

    library = ComponentLibrary(tmp_path / "library.sqlite3")
    created_id = library.add_field_definition(
        **field_kind_definition("Text", "Signing Date", "The date the agreement is signed.")
    )
    created = library.get_field_definition(created_id)
    root = _window_or_skip()
    try:
        dialog = FieldCreatorDialog(root, library, on_saved=lambda *_: None, existing=created)
        root.update()
        labels = []

        def walk(widget):
            for child in widget.winfo_children():
                if isinstance(child, ttk.Label):
                    labels.append(child.cget("text"))
                walk(child)

        walk(dialog.window)
        assert "Help text (optional)" in labels
        assert not any(text.startswith("Description") for text in labels)
        assert dialog.description.get() == "The date the agreement is signed."

        dialog.description.set("The date the agreement is signed by both parties.")
        dialog.save()
        root.update()
        stored = library.get_field_definition(created_id)
        assert stored["description"] == "The date the agreement is signed by both parties."
        assert stored["name"] == "Signing Date"
    finally:
        root.destroy()
