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
        with pytest.raises(sqlite3.IntegrityError, match="cannot be deleted"):
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



def test_save_component_updates_metadata_and_adds_a_version_atomically(tmp_path):
    library = ComponentLibrary(tmp_path / "publisher_profiles.sqlite3")
    first = library.save_component(
        None,
        "Payment terms",
        "Payment is due within thirty days.",
        description="Payment timing",
        category="Commercial",
        tags=["billing", "initial"],
        note="First version",
    )
    component_id = first["component_id"]
    assert first["is_new"] is True
    assert first["version"]["number"] == 1

    second = library.save_component(
        component_id,
        "Payment and late fees",
        "Payment is due within fifteen days.",
        description="Updated payment timing",
        category="Commercial terms",
        tags=["billing", "late payment"],
        note="Shortened the deadline",
    )
    assert second["is_new"] is False
    assert second["version"]["number"] == 2
    component = library.get_component(component_id)
    assert component["name"] == "Payment and late fees"
    assert component["description"] == "Updated payment timing"
    assert component["category"] == "Commercial terms"
    assert component["tags"] == ["billing", "late payment"]
    versions = library.list_component_versions(component_id)
    assert [item["number"] for item in versions] == [2, 1]
    assert versions[1]["markdown"] == "Payment is due within thirty days."

    with pytest.raises(TypeError, match="wording must be text"):
        library.save_component(
            component_id, "Should not persist", None, category="Changed"
        )
    assert library.get_component(component_id)["name"] == "Payment and late fees"
    assert [item["number"] for item in library.list_component_versions(component_id)] == [2, 1]


def test_component_creation_and_version_saving_validate_inputs(tmp_path):
    library = ComponentLibrary(tmp_path / "publisher_profiles.sqlite3")

    with pytest.raises(ValueError, match="component name"):
        library.create_component("  ")
    with pytest.raises(TypeError, match="wording must be text"):
        library.create_component("Valid name", markdown=None)
    with pytest.raises(ValueError, match="no longer exists"):
        library.save_component_version(999999, "Some wording")

def test_assembly_revision_pins_ordered_versions_and_shell_identity(tmp_path):
    library = ComponentLibrary(tmp_path / "publisher_profiles.sqlite3")
    payment_id = library.create_component("Payment", "Due within thirty days.")
    payment_v1 = library.list_component_versions(payment_id)[0]
    payment_v2 = library.save_component_version(payment_id, "Due within fifteen days.")
    governing_id = library.create_component("Governing law", "Texas law applies.")
    governing_v1 = library.list_component_versions(governing_id)[0]

    assembly_id = library.create_assembly(
        "Consulting agreement", description="Base form for consulting work"
    )
    revision = library.save_assembly_revision(
        assembly_id,
        "C:/Contracts/Consulting Shell.docx",
        "A" * 64,
        [
            {"component_version_id": payment_v1["id"], "included": True},
            {"component_version_id": governing_v1["id"], "included": False},
        ],
        note="Initial assembly",
    )

    assert revision["number"] == 1
    assert revision["finalized"] is True
    assert revision["shell_path"] == "C:/Contracts/Consulting Shell.docx"
    assert revision["shell_sha256"] == "a" * 64
    assert revision["assembly_name"] == "Consulting agreement"
    assert revision["note"] == "Initial assembly"
    assert [
        (
            item["position"],
            item["component_version_id"],
            item["component_version_number"],
            item["included"],
            item["markdown"],
        )
        for item in revision["components"]
    ] == [
        (0, payment_v1["id"], 1, True, "Due within thirty days."),
        (1, governing_v1["id"], 1, False, "Texas law applies."),
    ]
    assert library.get_assembly_revision(revision["id"]) == revision
    assert library.get_assembly(assembly_id)["description"] == "Base form for consulting work"
    assert library.list_assemblies() == [library.get_assembly(assembly_id)]
    assert library.list_assembly_revisions(assembly_id)[0]["id"] == revision["id"]

    # A new component version is not retroactively substituted into a saved
    # assembly revision; the saved membership still points at v1.
    assert payment_v2["number"] == 2
    reread = library.get_assembly_revision(revision["id"])
    assert reread["components"][0]["component_version_id"] == payment_v1["id"]
    assert reread["components"][0]["markdown"] == "Due within thirty days."


def test_assembly_revision_lists_newer_versions_without_applying_them(tmp_path):
    library = ComponentLibrary(tmp_path / "publisher_profiles.sqlite3")
    component_id = library.create_component("Termination", "Thirty days' notice.")
    pinned = library.list_component_versions(component_id)[0]
    assembly_id = library.create_assembly("Notice agreement")
    revision = library.save_assembly_revision(
        assembly_id,
        "/contracts/notice.docx",
        "c" * 64,
        [pinned["id"]],
    )

    second = library.save_component_version(component_id, "Forty-five days' notice.")
    third = library.save_component_version(component_id, "Sixty days' notice.")
    newer = library.list_newer_versions_for_revision(revision["id"])

    assert len(newer) == 1
    assert newer[0]["component_version_id"] == pinned["id"]
    assert newer[0]["pinned_number"] == 1
    assert newer[0]["component_name"] == "Termination"
    assert [item["number"] for item in newer[0]["newer_versions"]] == [2, 3]
    assert [item["markdown"] for item in newer[0]["newer_versions"]] == [
        "Forty-five days' notice.",
        "Sixty days' notice.",
    ]
    assert library.get_assembly_revision(revision["id"])["components"][0]["markdown"] == (
        "Thirty days' notice."
    )
    assert second["number"] == 2 and third["number"] == 3


def test_assembly_revision_validation_is_atomic_and_respects_archive_state(tmp_path):
    library = ComponentLibrary(tmp_path / "publisher_profiles.sqlite3")
    component_id = library.create_component("Payment", "Payment is due.")
    version_id = library.list_component_versions(component_id)[0]["id"]
    assembly_id = library.create_assembly("Payment agreement")

    with pytest.raises(ValueError, match="assembly name"):
        library.create_assembly(" ")
    with pytest.raises(ValueError, match="SHA-256"):
        library.save_assembly_revision(assembly_id, "shell.docx", "not-a-hash", [version_id])
    with pytest.raises(ValueError, match="at least one component"):
        library.save_assembly_revision(assembly_id, "shell.docx", "d" * 64, [])
    with pytest.raises(ValueError, match="Include at least one"):
        library.save_assembly_revision(
            assembly_id,
            "shell.docx",
            "d" * 64,
            [{"component_version_id": version_id, "included": False}],
        )
    with pytest.raises(ValueError, match="no longer exists"):
        library.save_assembly_revision(404, "shell.docx", "d" * 64, [version_id])
    with pytest.raises(ValueError, match="no longer exists"):
        library.save_assembly_revision(assembly_id, "shell.docx", "d" * 64, [999999])

    assert library.archive_component(component_id)
    with pytest.raises(ValueError, match="archived component"):
        library.save_assembly_revision(assembly_id, "shell.docx", "d" * 64, [version_id])
    assert library.restore_component(component_id)

    assert library.archive_assembly(assembly_id)
    with pytest.raises(ValueError, match="archived assembly"):
        library.save_assembly_revision(assembly_id, "shell.docx", "d" * 64, [version_id])
    assert library.restore_assembly(assembly_id)

    # Failed attempts did not leave partial or unfinalized revision records.
    assert library.list_assembly_revisions(assembly_id) == []
    assert library.get_assembly_revision(999999) is None
    with pytest.raises(ValueError, match="revision no longer exists"):
        library.list_newer_versions_for_revision(999999)

