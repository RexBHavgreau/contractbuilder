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



def test_archiving_preserves_pinned_component_wording_and_prevents_deletion(tmp_path):
    database = tmp_path / "publisher_profiles.sqlite3"
    library = ComponentLibrary(database)
    component_id = library.create_component(
        "Payment timing", "The fee is payable within thirty days."
    )
    version_id = library.list_component_versions(component_id)[0]["id"]

    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        assembly_id = connection.execute(
            "INSERT INTO assemblies (name, description, created) VALUES (?, ?, ?)",
            ("Services agreement", "", "2026-11-20T16:40:00+00:00"),
        ).lastrowid
        revision_id = connection.execute(
            "INSERT INTO assembly_versions "
            "(assembly_id, number, shell_path, shell_sha256, created) "
            "VALUES (?, 1, ?, ?, ?)",
            (
                assembly_id,
                "C:/Contracts/Services.docx",
                "b" * 64,
                "2026-11-20T16:41:00+00:00",
            ),
        ).lastrowid
        connection.execute(
            "INSERT INTO assembly_components "
            "(assembly_version_id, component_version_id, position, included) "
            "VALUES (?, ?, 0, 1)",
            (revision_id, version_id),
        )
        connection.execute(
            "UPDATE assembly_versions SET finalized = 1 WHERE id = ?",
            (revision_id,),
        )

    assert library.archive_component(component_id) is True
    assert library.get_component(component_id)["status"] == "archived"
    assert component_id not in {item["id"] for item in library.list_components()}
    assert component_id in {
        item["id"] for item in library.list_components(include_archived=True)
    }
    with pytest.raises(ValueError, match="archived"):
        library.save_component_version(component_id, "New wording.")

    # Rendering an assembly reads the exact pinned version row. Archiving the
    # parent component does not change or remove that historical Markdown.
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        pinned = connection.execute(
            """
            SELECT components.status, component_versions.markdown
            FROM assembly_components
            JOIN component_versions
              ON component_versions.id = assembly_components.component_version_id
            JOIN components
              ON components.id = component_versions.component_id
            WHERE assembly_components.assembly_version_id = ?
            """,
            (revision_id,),
        ).fetchone()
        assert pinned == ("archived", "The fee is payable within thirty days.")

        # Foreign keys and immutable-history triggers prevent deletion of
        # records or wording still needed by the assembly revision.
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("DELETE FROM components WHERE id = ?", (component_id,))
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute(
                "DELETE FROM component_versions WHERE id = ?", (version_id,)
            )

    assert library.archive_assembly(assembly_id) is True
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT status FROM assemblies WHERE id = ?", (assembly_id,)
        ).fetchone() == ("archived",)
        # SQLite foreign-key enforcement is connection-local and defaults
        # off. The explicit guard triggers must still preserve the history.
        assert connection.execute("PRAGMA foreign_keys").fetchone() == (0,)
        with pytest.raises(sqlite3.IntegrityError, match="cannot be deleted"):
            connection.execute("DELETE FROM assemblies WHERE id = ?", (assembly_id,))
        with pytest.raises(sqlite3.IntegrityError, match="cannot be deleted"):
            connection.execute("DELETE FROM components WHERE id = ?", (component_id,))

    assert library.restore_component(component_id) is True
    assert library.get_component(component_id)["status"] == "active"
    assert library.save_component_version(component_id, "New wording.")["number"] == 2
    assert library.restore_assembly(assembly_id) is True
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT status FROM assemblies WHERE id = ?", (assembly_id,)
        ).fetchone() == ("active",)


def test_archive_and_restore_return_false_for_missing_records(tmp_path):
    library = ComponentLibrary(tmp_path / "publisher_profiles.sqlite3")
    assert library.archive_component(404) is False
    assert library.restore_component(404) is False
    assert library.archive_assembly(404) is False
    assert library.restore_assembly(404) is False

def test_component_creation_and_version_saving_validate_inputs(tmp_path):
    library = ComponentLibrary(tmp_path / "publisher_profiles.sqlite3")

    with pytest.raises(ValueError, match="component name"):
        library.create_component("  ")
    with pytest.raises(TypeError, match="wording must be text"):
        library.create_component("Valid name", markdown=None)
    with pytest.raises(ValueError, match="no longer exists"):
        library.save_component_version(999999, "Some wording")
