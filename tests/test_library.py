"""Tests for the non-UI component library storage API."""
import pathlib
import sqlite3
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from library import ComponentLibrary  # noqa: E402


def test_create_and_edit_component_always_create_immutable_versions(tmp_path):
    database = tmp_path / "publisher_profiles.sqlite3"
    library = ComponentLibrary(database)
    component_id = library.create_component(
        "Payment schedule",
        "Payment is due within {{Payment Period}}.",
        description="Timing and instalments",
        category="A user-created category",
        tags=["custom tag", "International", "CUSTOM TAG"],
        note="Initial text",
    )

    component = library.get_component(component_id)
    assert component["name"] == "Payment schedule"
    assert component["description"] == "Timing and instalments"
    assert component["category"] == "A user-created category"
    assert component["tags"] == ["custom tag", "International"]
    assert component["status"] == "active"

    first = library.list_component_versions(component_id)[0]
    assert first["number"] == 1
    assert first["markdown"] == "Payment is due within {{Payment Period}}."
    assert first["note"] == "Initial text"
    assert first["created"].endswith("+00:00")

    second = library.save_component_version(
        component_id,
        "Payment is due within {{Due Date}}.",
        note="Clarified the deadline",
    )
    assert second["number"] == 2
    assert second["markdown"] == "Payment is due within {{Due Date}}."
    assert [version["number"] for version in library.list_component_versions(component_id)] == [2, 1]
    assert library.get_component_version(first["id"])["markdown"] == first["markdown"]

    with sqlite3.connect(database) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute(
                "UPDATE component_versions SET markdown = 'Changed in place' WHERE id = ?",
                (first["id"],),
            )


def test_component_list_filters_free_text_and_searches_wording_history(tmp_path):
    library = ComponentLibrary(tmp_path / "publisher_profiles.sqlite3")
    first_id = library.create_component(
        "Termination",
        "Either party may terminate on thirty days' notice.",
        category="Operations - custom",
        tags=["notice", "contract term"],
    )
    library.save_component_version(first_id, "Either party may terminate on sixty days' notice.")
    second_id = library.create_component(
        "Confidentiality",
        "Keep confidential information secure.",
        category="Other",
        tags=["privacy"],
    )

    assert [item["id"] for item in library.list_components(category="operations - CUSTOM")] == [first_id]
    assert [item["id"] for item in library.list_components(tag="NOTICE")] == [first_id]
    assert [item["id"] for item in library.search_components("confidential information")] == [second_id]
    # Search includes earlier immutable versions as well as the latest wording.
    assert [item["id"] for item in library.search_components("thirty days")] == [first_id]


def test_component_creation_and_version_saving_validate_inputs(tmp_path):
    library = ComponentLibrary(tmp_path / "publisher_profiles.sqlite3")

    with pytest.raises(ValueError, match="component name"):
        library.create_component("  ")
    with pytest.raises(TypeError, match="wording must be text"):
        library.create_component("Valid name", markdown=None)
    with pytest.raises(ValueError, match="no longer exists"):
        library.save_component_version(999999, "Some wording")
