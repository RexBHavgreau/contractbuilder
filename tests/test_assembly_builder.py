"""Tests for assembly previews and reproducible saved Markdown sources."""
from collections import Counter
from io import BytesIO
import pathlib
import sys

from docx import Document
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import core  # noqa: E402
from assembly_builder import (  # noqa: E402
    compose_assembly_template,
    included_component_markdown,
    preview_segments_for_components,
    shell_file_sha256,
    update_component_items,
    version_diff_lines,
)
from library import ComponentLibrary  # noqa: E402


def test_saved_revision_reopens_exact_included_markdown_in_saved_order(tmp_path):
    library = ComponentLibrary(tmp_path / "publisher_profiles.sqlite3")
    first_id = library.create_component("Opening", "Opening wording.\n")
    first_v1 = library.list_component_versions(first_id)[0]
    second_id = library.create_component("Optional", "{{Optional Clause}}")
    second_v1 = library.list_component_versions(second_id)[0]
    repeated_id = library.create_component("Closing", "Closing wording  ")
    repeated_v1 = library.list_component_versions(repeated_id)[0]

    assembly_id = library.create_assembly("Sample assembly")
    saved = library.save_assembly_revision(
        assembly_id,
        str(tmp_path / "shell.docx"),
        "a" * 64,
        [
            {"component_version_id": first_v1["id"], "included": True},
            {"component_version_id": second_v1["id"], "included": False},
            {"component_version_id": repeated_v1["id"], "included": True},
            {"component_version_id": first_v1["id"], "included": True},
        ],
    )
    reopened = library.get_assembly_revision(saved["id"])

    assert reopened["number"] == 1
    assert [
        (item["component_version_id"], item["included"])
        for item in reopened["components"]
    ] == [
        (first_v1["id"], True),
        (second_v1["id"], False),
        (repeated_v1["id"], True),
        (first_v1["id"], True),
    ]
    assert included_component_markdown(reopened) == [
        "Opening wording.\n",
        "Closing wording  ",
        "Opening wording.\n",
    ]


def test_assembly_preview_keeps_field_highlighting_and_component_boundaries():
    segments = preview_segments_for_components(
        [
            {
                "component_name": "Opening",
                "component_version_number": 1,
                "markdown": "{{Client Name}} and {{Unfinished",
                "included": True,
            },
            {
                "component_name": "Omitted",
                "component_version_number": 1,
                "markdown": "This should not appear.",
                "included": False,
            },
            {
                "component_name": "Closing",
                "component_version_number": 2,
                "markdown": "brace text}} and {{Fee | money-words}}",
                "included": True,
            },
        ]
    )
    visible_text = "".join(text for text, _tags in segments)
    highlighted = [
        text for text, tags in segments if "field" in tags
    ]

    assert "Opening · version 1" in visible_text
    assert "Closing · version 2" in visible_text
    assert "This should not appear." not in visible_text
    assert "{{Unfinished\n" in visible_text
    assert "brace text}}" in visible_text
    assert highlighted == ["{{Client Name}}", "{{Fee | money-words}}"]


def test_shell_digest_changes_when_shell_bytes_change(tmp_path):
    shell = tmp_path / "shell.docx"
    shell.write_bytes(b"first shell bytes")
    first = shell_file_sha256(shell)
    shell.write_bytes(b"changed shell bytes")
    second = shell_file_sha256(shell)

    assert first != second
    assert len(second) == 64


def test_included_markdown_rejects_invalid_component_collection():
    with pytest.raises(TypeError, match="ordered component list"):
        included_component_markdown({"components": "not a component list"})


def test_version_diff_marks_added_and_removed_wording():
    lines = version_diff_lines(
        "First clause.\nRetained sentence.",
        "Replacement clause.\nRetained sentence.",
    )
    assert any(line.startswith("-First clause.") for line in lines)
    assert any(line.startswith("+Replacement clause.") for line in lines)
    assert any(line == " Retained sentence." for line in lines)


def test_update_choices_change_only_explicitly_selected_items():
    items = [
        {
            "key": 1, "component_id": 10, "component_version_id": 100,
            "component_version_number": 1, "component_name": "Opening",
            "markdown": "Original opening.", "included": True,
        },
        {
            "key": 2, "component_id": 20, "component_version_id": 200,
            "component_version_number": 1, "component_name": "Closing",
            "markdown": "Original closing.", "included": False,
        },
    ]
    proposed = {
        "id": 102, "number": 3, "markdown": "Revised opening.",
        "component_id": 10,
    }
    updated = update_component_items(items, {1: proposed})

    assert updated[0]["component_version_id"] == 102
    assert updated[0]["component_version_number"] == 3
    assert updated[0]["markdown"] == "Revised opening."
    assert updated[1] == items[1]
    assert items[0]["markdown"] == "Original opening."


def test_update_choices_reject_an_older_or_unrelated_version():
    item = {
        "key": 1, "component_id": 10, "component_version_id": 100,
        "component_version_number": 2, "component_name": "Opening",
        "markdown": "Pinned.", "included": True,
    }
    with pytest.raises(ValueError, match="different component"):
        update_component_items(
            [item],
            {1: {"id": 201, "number": 3, "markdown": "Other.", "component_id": 20}},
        )
    with pytest.raises(ValueError, match="newer than"):
        update_component_items(
            [item],
            {1: {"id": 101, "number": 1, "markdown": "Old."}},
        )


def _make_assembly_shell(path):
    document = Document()
    document.sections[0].header.paragraphs[0].text = "Assembly header"
    document.sections[0].footer.paragraphs[0].text = "Assembly footer"
    document.add_paragraph("This shell wording is replaced.")
    document.save(path)
    return path


def _render_revision(revision, shell, tmp_path, name):
    template, _composition = compose_assembly_template(
        shell,
        included_component_markdown(revision),
        tmp_path / f"{name}.docx",
    )
    values = {"Client Name": "Example Client"}
    data, report = core.render(template, values)
    assert report.blanks == []
    return Document(BytesIO(data))


def test_assembly_generation_discovers_each_unique_field_once_across_components(tmp_path):
    shell = _make_assembly_shell(tmp_path / "shell.docx")
    template, composition = compose_assembly_template(
        shell,
        [
            "Opening for {{Client Name}}.",
            "Payment from {{Client Name}} is {{Fee | money-words}}.",
        ],
        tmp_path / "assembled.docx",
    )

    assert Counter(field.name for field in template.field_list()) == Counter({
        "Client Name": 1,
        "Fee": 1,
    })
    assert template.places == 3
    # A shell without the decimal outline is not a problem any more: the new
    # document gets the numbering added (T-060-A).
    assert [warning.code for warning in composition.warnings] == []

    filled, report = core.render(template, {
        "Client Name": "Example Client",
        "Fee": "250",
    })
    document = Document(BytesIO(filled))
    text = "\\n".join(paragraph.text for paragraph in document.paragraphs)
    assert text.count("Example Client") == 2
    assert "Two Hundred Fifty Dollars ($250.00)" in text
    assert "{{" not in text
    assert report.blanks == []


def test_revisions_remain_reproducible_after_two_component_edits(tmp_path):
    shell = _make_assembly_shell(tmp_path / "shell.docx")
    library = ComponentLibrary(tmp_path / "publisher_profiles.sqlite3")

    clause_id = library.create_component(
        "Payment clause", "Payment for {{Client Name}} is due in thirty days."
    )
    clause_v1 = library.list_component_versions(clause_id)[0]
    closing_id = library.create_component("Closing clause", "Signed by {{Client Name}}.")
    closing_v1 = library.list_component_versions(closing_id)[0]

    assembly_id = library.create_assembly("Revision history example")
    first = library.save_assembly_revision(
        assembly_id,
        str(shell),
        shell_file_sha256(shell),
        [clause_v1["id"], closing_v1["id"]],
    )

    clause_v2 = library.save_component_version(
        clause_id, "Payment for {{Client Name}} is due in fifteen days."
    )
    clause_v3 = library.save_component_version(
        clause_id, "Payment for {{Client Name}} is due in ten days."
    )
    closing_v2 = library.save_component_version(
        closing_id, "Signed and accepted by {{Client Name}}."
    )

    newer = library.list_newer_versions_for_revision(first["id"])
    assert [item["number"] for item in newer[0]["newer_versions"]] == [2, 3]
    assert [item["number"] for item in newer[1]["newer_versions"]] == [2]

    working_items = [
        {
            "key": 1, "component_id": clause_id,
            "component_version_id": clause_v1["id"],
            "component_version_number": clause_v1["number"],
            "component_name": "Payment clause", "markdown": clause_v1["markdown"],
            "included": True,
        },
        {
            "key": 2, "component_id": closing_id,
            "component_version_id": closing_v1["id"],
            "component_version_number": closing_v1["number"],
            "component_name": "Closing clause", "markdown": closing_v1["markdown"],
            "included": True,
        },
    ]
    # Choose the third payment version but leave the closing clause pinned.
    updated_items = update_component_items(
        working_items,
        {1: dict(clause_v3, component_id=clause_id)},
    )
    second = library.save_assembly_revision(
        assembly_id,
        str(shell),
        shell_file_sha256(shell),
        [
            {"component_version_id": item["component_version_id"],
             "included": item["included"]}
            for item in updated_items
        ],
        note="Updated payment wording only",
    )

    # The first revision still renders its original wording after two edits.
    original_document = _render_revision(first, shell, tmp_path, "original")
    original_text = "\\n".join(
        paragraph.text for paragraph in original_document.paragraphs
    )
    assert "due in thirty days" in original_text
    assert "due in ten days" not in original_text
    assert "due in fifteen days" not in original_text

    # The new revision uses the explicitly selected v3; the unselected closing
    # component stays at v1 even though v2 is available.
    updated_document = _render_revision(second, shell, tmp_path, "updated")
    updated_text = "\\n".join(
        paragraph.text for paragraph in updated_document.paragraphs
    )
    assert "due in ten days" in updated_text
    assert "due in thirty days" not in updated_text
    assert "Signed by Example Client" in updated_text
    assert "Signed and accepted" not in updated_text
    assert second["number"] == 2
    assert library.get_assembly_revision(first["id"])["components"][0]["markdown"] == (
        clause_v1["markdown"]
    )
    assert clause_v2["number"] == 2
    assert closing_v2["number"] == 2

def test_assembly_preview_can_show_a_selected_conditional_alternative():
    components = [
        {
            "component_name": "Fee clause",
            "component_version_number": 1,
            "markdown": (
                "The fee is {{#if Publisher Type = Non-profit}}waived"
                "{{else}}due{{/if}}."
            ),
            "included": True,
        },
        {
            "component_name": "Omitted clause",
            "markdown": "{{#if Publisher Type = Non-profit}}hidden{{/if}}",
            "included": False,
        },
    ]
    all_segments = preview_segments_for_components(components)
    all_text = "".join(value for value, _tags in all_segments)
    assert "Otherwise" in all_text
    assert "End of choice" in all_text
    assert "Omitted clause" not in all_text

    selected_segments = preview_segments_for_components(
        components, preview_values={"Publisher Type": "Non-profit"}
    )
    selected_text = "".join(value for value, _tags in selected_segments)
    assert "waived" in selected_text
    assert "due" not in selected_text
    assert "Otherwise" not in selected_text
    assert "End of choice" not in selected_text

