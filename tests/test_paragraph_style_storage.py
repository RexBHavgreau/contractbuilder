"""Per-paragraph styles stored with component versions (T-061, schema v6)."""
import pathlib
import sqlite3
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import publisher_profiles as profiles  # noqa: E402
from library import ComponentLibrary  # noqa: E402


def _user_version(path):
    with sqlite3.connect(path) as connection:
        return connection.execute("PRAGMA user_version").fetchone()[0]


def _columns(path):
    with sqlite3.connect(path) as connection:
        return {row[1] for row in connection.execute("PRAGMA table_info(component_versions)")}


def test_a_new_database_has_the_column_and_round_trips_styles(tmp_path):
    path = tmp_path / "db.sqlite3"
    library = ComponentLibrary(path)
    assert profiles.SCHEMA_VERSION >= 6 and "paragraph_styles" in _columns(path)
    component_id = library.create_component(
        "Heading block", "The title\n\nThe subtitle", paragraph_styles=["Title", "Subtitle"]
    )
    version = library.list_component_versions(component_id)[0]
    assert version["paragraph_styles"] == ["Title", "Subtitle"]
    assert library.get_component_version(version["id"])["paragraph_styles"] == ["Title", "Subtitle"]


def test_saving_a_new_version_keeps_each_versions_own_styles(tmp_path):
    library = ComponentLibrary(tmp_path / "db.sqlite3")
    component_id = library.create_component("C", "One\n\nTwo", paragraph_styles=["Title"])
    library.save_component(component_id, "C", "One\n\nTwo", paragraph_styles=["Title", "Subtitle"])
    library.save_component_version(component_id, "One", paragraph_styles=[])
    versions = library.list_component_versions(component_id)
    assert [v["paragraph_styles"] for v in versions] == [[], ["Title", "Subtitle"], ["Title"]]


def test_versions_stay_immutable_with_the_new_column(tmp_path):
    path = tmp_path / "db.sqlite3"
    library = ComponentLibrary(path)
    component_id = library.create_component("C", "One", paragraph_styles=["Title"])
    with sqlite3.connect(path) as connection:
        with pytest.raises(sqlite3.DatabaseError):
            connection.execute("UPDATE component_versions SET paragraph_styles = ''")


def test_assembly_revisions_carry_the_pinned_versions_styles(tmp_path):
    library = ComponentLibrary(tmp_path / "db.sqlite3")
    component_id = library.create_component("C", "One\n\nTwo", paragraph_styles=["Title"])
    first = library.list_component_versions(component_id)[0]
    library.save_component(component_id, "C", "One\n\nTwo", paragraph_styles=["Title", "Subtitle"])
    assembly_id = library.create_assembly("A")
    revision = library.save_assembly_revision(
        assembly_id, str(tmp_path / "shell.docx"), "0" * 64, [first["id"]]
    )
    loaded = library.get_assembly_revision(revision["id"])
    assert loaded["components"][0]["paragraph_styles"] == ["Title"]
    newer = library.list_newer_versions_for_revision(revision["id"])[0]["newer_versions"]
    assert newer[0]["paragraph_styles"] == ["Title", "Subtitle"]


def test_upgrade_from_v5_adds_the_column_backs_up_and_keeps_old_versions(tmp_path, monkeypatch):
    path = tmp_path / "db.sqlite3"
    # Build a real v5 file with the migrations that existed then.
    monkeypatch.setattr(profiles, "SCHEMA_VERSION", 5)
    monkeypatch.setattr(profiles, "_MIGRATIONS", {k: v for k, v in profiles._MIGRATIONS.items() if k <= 5})
    old = ComponentLibrary(path)
    component_id = old.create_component("Old", "Old wording")
    assert _user_version(path) == 5 and "paragraph_styles" not in _columns(path)
    # An older library can still read its versions (no styles key needed).
    assert old.list_component_versions(component_id)[0]["paragraph_styles"] == []
    monkeypatch.undo()

    current = ComponentLibrary(path)
    assert _user_version(path) == profiles.SCHEMA_VERSION
    assert "paragraph_styles" in _columns(path)
    assert (tmp_path / "db.sqlite3.bak-5").exists()
    version = current.list_component_versions(component_id)[0]
    assert version["markdown"] == "Old wording" and version["paragraph_styles"] == []


def test_an_older_application_still_opens_a_v6_file(tmp_path, monkeypatch):
    path = tmp_path / "db.sqlite3"
    current = ComponentLibrary(path)
    component_id = current.create_component("C", "Words", paragraph_styles=["Title"])
    monkeypatch.setattr(profiles, "SCHEMA_VERSION", 5)
    monkeypatch.setattr(profiles, "_MIGRATIONS", {k: v for k, v in profiles._MIGRATIONS.items() if k <= 5})
    older = ComponentLibrary(path)
    assert older.get_component(component_id)["name"] == "C"
    monkeypatch.undo()
    assert _user_version(path) == 6
