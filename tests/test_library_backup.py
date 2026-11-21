from __future__ import annotations

import json
import sqlite3

import pytest

from library import ComponentLibrary
from library_backup import (
    APP_TABLES,
    PROFILE_TABLES,
    backup_reminder_due,
    export_library_backup,
    get_backup_reminder_settings,
    import_library_backup,
    preview_library_import,
    set_backup_reminder_enabled,
)
from publisher_profiles import PublisherProfileStore


def _all_tables():
    return APP_TABLES + PROFILE_TABLES


def _snapshot(path, tables=None):
    tables = tables or _all_tables()
    with sqlite3.connect(path) as connection:
        result = {}
        for table in tables:
            exists = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            ).fetchone()
            if not exists:
                continue
            columns = [row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')]
            rows = [list(row) for row in connection.execute(f'SELECT * FROM "{table}" ORDER BY rowid')]
            result[table] = {"columns": columns, "rows": rows}
        return result


def _populate_library(path, with_profiles=True):
    library = ComponentLibrary(path)
    clause_id = library.create_component(
        "Payment clause", "Payment is due within thirty days.",
        description="Payment timing", category="Commercial",
        tags=["billing", "payment"], note="Initial wording",
    )
    first = library.list_component_versions(clause_id)[0]
    second = library.save_component_version(
        clause_id, "Payment is due within fifteen days.", note="Shortened deadline"
    )
    archived_id = library.create_component(
        "Old clause", "This is retained historical wording.",
        category="Legacy",
    )
    old_version = library.list_component_versions(archived_id)[0]
    library.archive_component(archived_id)

    assembly_id = library.create_assembly(
        "Services agreement", description="Base agreement"
    )
    revision = library.save_assembly_revision(
        assembly_id, "shell.docx", "a" * 64,
        [first["id"], {"component_version_id": old_version["id"], "included": False}],
        note="First assembly revision",
    )
    assert revision["finalized"] is True
    library.archive_assembly(assembly_id)

    field_id = library.add_field_definition(
        "Publisher Type", description="Legal form", group="Publisher",
        default_format="choice", allowed_values=["Non-profit", "Sole proprietor"],
        publisher_detail_name="Publisher type",
    )
    library.archive_field_definition(field_id)

    if with_profiles:
        profiles = PublisherProfileStore(path)
        profiles.add_detail_definition(
            "Publisher category", ["Non-profit", "For-profit"],
            description="The publisher's category",
        )
        profile_id = profiles.save_profile({
            "publisher_name": "Example Press",
            "contact_name": "Alex Editor",
            "contact_email": "alex@example.test",
            "city": "Dallas",
            "country": "United States",
            "details": {"Publisher category": "Non-profit"},
        })
        profiles.save_field_match("Press name", "publisher_name")
        profiles.save_party("Publisher One", "Licensor")
        assert profiles.get_profile_with_details(profile_id)["details"] == {
            "Publisher category": "Non-profit"
        }
    return library


def test_full_backup_restores_components_versions_assemblies_fields_and_profiles(tmp_path):
    source_path = tmp_path / "source.sqlite3"
    restored_path = tmp_path / "restored.sqlite3"
    source = _populate_library(source_path)
    ComponentLibrary(restored_path)  # create an empty current-schema database
    before = _snapshot(source_path)

    backup_path = tmp_path / "library-backup.json"
    exported = export_library_backup(source.path, backup_path, include_publisher_profiles=True)
    payload = json.loads(backup_path.read_text(encoding="utf-8"))
    assert payload["format"] == "contractbuilder-library-backup"
    assert payload["format_version"] == 1
    assert payload["includes_publisher_profiles"] is True
    assert set(payload["tables"]) == set(_all_tables())
    assert sum(exported["counts"].values()) == sum(
        len(table["rows"]) for table in before.values()
    )

    result = import_library_backup(
        restored_path, backup_path, mode="replace",
        include_publisher_profiles=True,
    )
    assert result["mode"] == "replace"
    assert _snapshot(restored_path) == before

    restored = ComponentLibrary(restored_path)
    assert len(restored.list_components(include_archived=True)) == 2
    assert restored.list_assembly_revisions(
        restored.list_assemblies(include_archived=True)[0]["id"]
    )[0]["finalized"] == 1


def test_profile_data_is_excluded_by_default_and_replace_leaves_local_profiles_alone(tmp_path):
    source_path = tmp_path / "source.sqlite3"
    target_path = tmp_path / "target.sqlite3"
    source = _populate_library(source_path, with_profiles=True)
    target = _populate_library(target_path, with_profiles=True)
    backup_path = tmp_path / "without-profiles.json"

    export_library_backup(source.path, backup_path)
    payload = json.loads(backup_path.read_text(encoding="utf-8"))
    assert payload["includes_publisher_profiles"] is False
    assert not (set(payload["tables"]) & set(PROFILE_TABLES))

    target_profiles_before = _snapshot(target_path, PROFILE_TABLES)
    preview = preview_library_import(target.path, backup_path, mode="replace")
    assert preview["includes_publisher_profiles"] is False
    result = import_library_backup(target.path, backup_path, mode="replace")
    assert result["includes_publisher_profiles"] is False
    assert _snapshot(target_path, PROFILE_TABLES) == target_profiles_before


def test_profiles_in_backup_still_require_an_explicit_import_opt_in(tmp_path):
    source_path = tmp_path / "source.sqlite3"
    target_path = tmp_path / "target.sqlite3"
    source = _populate_library(source_path, with_profiles=True)
    target = _populate_library(target_path, with_profiles=True)
    backup_path = tmp_path / "with-profiles.json"
    export_library_backup(source.path, backup_path, include_publisher_profiles=True)

    target_profiles = _snapshot(target_path, PROFILE_TABLES)
    preview = preview_library_import(target.path, backup_path, mode="replace")
    assert preview["includes_publisher_profiles"] is False
    import_library_backup(target.path, backup_path, mode="replace")
    assert _snapshot(target_path, PROFILE_TABLES) == target_profiles

    import_library_backup(
        target.path, backup_path, mode="replace",
        include_publisher_profiles=True,
    )
    assert _snapshot(target_path, PROFILE_TABLES) == _snapshot(source_path, PROFILE_TABLES)


def test_merge_remaps_ids_preserves_existing_data_and_pins_imported_versions(tmp_path):
    source_path = tmp_path / "source.sqlite3"
    target_path = tmp_path / "target.sqlite3"
    source = _populate_library(source_path, with_profiles=False)
    target = ComponentLibrary(target_path)
    local_id = target.create_component("Local clause", "Keep this wording.")
    local_field = target.add_field_definition(
        "Publisher Type", default_format="choice", allowed_values=["Local choice"]
    )
    backup_path = tmp_path / "merge.json"
    export_library_backup(source.path, backup_path)

    preview = preview_library_import(target.path, backup_path, mode="merge")
    assert preview["conflicts"]["field_definitions"] == 1
    result = import_library_backup(target.path, backup_path, mode="merge")
    assert result["skipped"]["field_definitions"] == 1
    assert target.get_component(local_id)["name"] == "Local clause"
    assert target.get_field_definition(local_field)["allowed_values"] == ["Local choice"]
    components = target.list_components(include_archived=True)
    assert len(components) == 3

    imported_assembly = target.list_assemblies(include_archived=True)[0]
    revision = target.list_assembly_revisions(imported_assembly["id"])[0]
    restored_revision = target.get_assembly_revision(revision["id"])
    assert restored_revision["finalized"] is True
    assert len(restored_revision["components"]) == 2
    assert {
        item["markdown"] for item in restored_revision["components"]
    } == {
        "Payment is due within thirty days.",
        "This is retained historical wording.",
    }


def test_bad_backup_is_rejected_without_changing_the_library(tmp_path):
    source_path = tmp_path / "source.sqlite3"
    target_path = tmp_path / "target.sqlite3"
    source = _populate_library(source_path, with_profiles=False)
    target = ComponentLibrary(target_path)
    target.create_component("Keep me", "Existing wording.")
    backup_path = tmp_path / "bad.json"
    export_library_backup(source.path, backup_path)
    payload = json.loads(backup_path.read_text(encoding="utf-8"))
    payload["format"] = "not-a-backup"
    backup_path.write_text(json.dumps(payload), encoding="utf-8")
    before = _snapshot(target_path)

    with pytest.raises(ValueError, match="not a Contract Builder"):
        import_library_backup(target.path, backup_path, mode="replace")
    assert _snapshot(target_path) == before


def test_backup_reminder_is_disabled_by_default_and_uses_a_four_week_interval(tmp_path):
    database = tmp_path / "library.sqlite3"
    settings = get_backup_reminder_settings(database)
    assert settings == {"enabled": False, "last_backup": None}
    assert backup_reminder_due(database) is False

    set_backup_reminder_enabled(database, True)
    assert backup_reminder_due(database) is True
    export_library_backup(
        ComponentLibrary(database).path, tmp_path / "reminder-backup.json"
    )
    assert backup_reminder_due(database) is False
    assert get_backup_reminder_settings(database)["last_backup"]
