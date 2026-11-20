"""Tests for assembly previews and reproducible saved Markdown sources."""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from assembly_builder import (  # noqa: E402
    included_component_markdown,
    preview_segments_for_components,
    shell_file_sha256,
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
