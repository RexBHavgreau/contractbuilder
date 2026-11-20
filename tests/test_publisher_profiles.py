"""Tests for the local publisher profile database and template field mapping."""
import pathlib
import sqlite3
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import publisher_profiles as profiles  # noqa: E402


def sample_profile(name="Éditions Exemple"):
    return {
        "publisher_name": name,
        "contact_name": "Camille Martin",
        "contact_title": "Foreign Rights Manager",
        "contact_email": "camille@example.org",
        "contact_phone": "+33 1 23 45 67 89",
        "website": "https://example.org",
        "address_line1": "12 Rue de Paris",
        "address_line2": "Bâtiment B",
        "city": "Lyon",
        "region": "Auvergne-Rhône-Alpes",
        "postal_code": "69002",
        "country": "France",
        "notes": "Prefers email correspondence.",
    }


def test_profile_crud_round_trip(tmp_path):
    store = profiles.PublisherProfileStore(tmp_path / "publishers.sqlite3")
    profile_id = store.save_profile(sample_profile())

    saved = store.get_profile(profile_id)
    assert saved["publisher_name"] == "Éditions Exemple"
    assert saved["contact_name"] == "Camille Martin"
    assert saved["country"] == "France"
    assert len(store.list_profiles()) == 1

    updated = sample_profile()
    updated["contact_name"] = "Alexandre Dupont"
    updated["notes"] = "Updated contact."
    assert store.save_profile(updated, profile_id) == profile_id

    saved = store.get_profile(profile_id)
    assert saved["contact_name"] == "Alexandre Dupont"
    assert saved["notes"] == "Updated contact."
    assert len(store.list_profiles()) == 1

    assert store.delete_profile(profile_id) is True
    assert store.get_profile(profile_id) is None
    assert store.delete_profile(profile_id) is False


def test_publisher_names_are_unique_with_unicode_casefolding(tmp_path):
    store = profiles.PublisherProfileStore(tmp_path / "publishers.sqlite3")
    store.save_profile(sample_profile("Éditions Exemple"))

    with pytest.raises(ValueError, match="already exists"):
        store.save_profile(sample_profile("ÉDITIONS EXEMPLE"))


def test_profile_requires_publisher_name(tmp_path):
    store = profiles.PublisherProfileStore(tmp_path / "publishers.sqlite3")
    with pytest.raises(ValueError, match="publisher name"):
        store.save_profile({"contact_name": "Someone"})


def test_formatted_address_uses_only_populated_parts():
    profile = sample_profile()
    assert profiles.format_address(profile) == (
        "12 Rue de Paris\nBâtiment B\nLyon, Auvergne-Rhône-Alpes 69002\nFrance"
    )
    assert profiles.format_address({"city": "Lyon", "country": "France"}) == "Lyon\nFrance"


def test_template_field_mapping_uses_exact_template_labels():
    profile = sample_profile()
    mapped = profiles.values_for_template(
        profile,
        [
            "International Publisher Name",
            "International Publisher's Contact",
            "International Publisher Address",
            "International Publisher Contact Email",
            "International Publisher Country",
            "Agreement Date",
        ],
    )
    assert mapped == {
        "International Publisher Name": "Éditions Exemple",
        "International Publisher's Contact": "Camille Martin",
        "International Publisher Address": (
            "12 Rue de Paris, Bâtiment B, Lyon, Auvergne-Rhône-Alpes 69002, France"
        ),
        "International Publisher Contact Email": "camille@example.org",
        "International Publisher Country": "France",
    }


def test_empty_profile_values_do_not_overwrite_template_fields():
    profile = {"publisher_name": "Example Publishing", "contact_name": ""}
    assert profiles.values_for_template(
        profile, ["International Publisher Name", "International Publisher Contact"]
    ) == {"International Publisher Name": "Example Publishing"}


def _user_version(path):
    with sqlite3.connect(path) as connection:
        return connection.execute("PRAGMA user_version").fetchone()[0]


def _upgrade_store_to_v2(monkeypatch, path, migration):
    monkeypatch.setattr(profiles, "SCHEMA_VERSION", 2)
    monkeypatch.setattr(profiles, "_MIGRATIONS", {2: migration})
    return profiles.PublisherProfileStore(path)


def test_new_and_unversioned_legacy_databases_are_schema_version_one(tmp_path):
    path = tmp_path / "publisher_profiles.sqlite3"
    store = profiles.PublisherProfileStore(path)
    profile_id = store.save_profile(sample_profile())

    assert _user_version(path) == 1

    # Simulate a database written by the pre-versioning application. Its
    # SQLite user_version is still the default zero, but its layout is v1.
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA user_version = 0")

    reopened = profiles.PublisherProfileStore(path)

    assert _user_version(path) == 1
    assert reopened.get_profile(profile_id) == store.get_profile(profile_id)
    assert reopened.list_profiles() == [store.get_profile(profile_id)]
    assert not pathlib.Path(str(path) + ".bak-0").exists()


def test_upgrade_makes_one_verified_backup_and_preserves_publisher_profiles(
    tmp_path, monkeypatch
):
    path = tmp_path / "publisher_profiles.sqlite3"
    store = profiles.PublisherProfileStore(path)
    first_id = store.save_profile(sample_profile())
    second = sample_profile("Maison Exemple")
    second_id = store.save_profile(second)
    before = store.list_profiles()

    def add_component_table(connection):
        connection.execute(
            "CREATE TABLE component_probe (id INTEGER PRIMARY KEY, value TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO component_probe (value) VALUES ('migration complete')"
        )

    upgraded = _upgrade_store_to_v2(monkeypatch, path, add_component_table)

    assert _user_version(path) == 2
    assert upgraded.list_profiles() == before
    assert upgraded.get_profile(first_id) == before[0]
    assert upgraded.get_profile(second_id) == before[1]

    backup_path = pathlib.Path(str(path) + ".bak-1")
    assert backup_path.is_file()
    assert _user_version(backup_path) == 1
    with sqlite3.connect(backup_path) as backup:
        assert backup.execute(
            "SELECT value FROM sqlite_master WHERE type = 'table' AND name = 'component_probe'"
        ).fetchone() is None
        assert backup.execute("SELECT COUNT(*) FROM publishers").fetchone()[0] == 2

    # Opening the already-upgraded database again must not replace the
    # version-1 recovery copy.
    backup_before = backup_path.read_bytes()
    profiles.PublisherProfileStore(path)
    assert backup_path.read_bytes() == backup_before


def test_failed_migration_rolls_back_database_and_keeps_original_backup(
    tmp_path, monkeypatch
):
    path = tmp_path / "publisher_profiles.sqlite3"
    store = profiles.PublisherProfileStore(path)
    store.save_profile(sample_profile())
    before = store.list_profiles()

    def fail_after_partial_changes(connection):
        connection.execute(
            "CREATE TABLE should_roll_back (id INTEGER PRIMARY KEY, value TEXT)"
        )
        connection.execute(
            "UPDATE publishers SET notes = 'partially changed'"
        )
        raise RuntimeError("simulated migration failure")

    monkeypatch.setattr(profiles, "SCHEMA_VERSION", 2)
    monkeypatch.setattr(profiles, "_MIGRATIONS", {2: fail_after_partial_changes})

    with pytest.raises(RuntimeError, match="simulated migration failure"):
        profiles.PublisherProfileStore(path)

    assert _user_version(path) == 1
    with sqlite3.connect(path) as connection:
        assert connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'should_roll_back'"
        ).fetchone() is None
    assert profiles.PublisherProfileStore(path).list_profiles() == before

    backup_path = pathlib.Path(str(path) + ".bak-1")
    assert backup_path.is_file()
    assert _user_version(backup_path) == 1
    with sqlite3.connect(backup_path) as backup:
        assert backup.execute("SELECT notes FROM publishers").fetchone()[0] == before[0]["notes"]


def test_older_application_can_use_publishers_without_changing_newer_tables(
    tmp_path, monkeypatch
):
    path = tmp_path / "publisher_profiles.sqlite3"

    def add_component_table(connection):
        connection.execute(
            "CREATE TABLE components (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO components (name) VALUES ('Invented component')"
        )

    newer = _upgrade_store_to_v2(monkeypatch, path, add_component_table)
    newer.save_profile(sample_profile())
    with sqlite3.connect(path) as connection:
        component_before = connection.execute(
            "SELECT id, name FROM components"
        ).fetchall()
        schema_before = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'components'"
        ).fetchone()[0]

    # Simulate the older application, which knows only schema version 1.
    monkeypatch.setattr(profiles, "SCHEMA_VERSION", 1)
    monkeypatch.setattr(profiles, "_MIGRATIONS", {})
    older = profiles.PublisherProfileStore(path)
    older.save_profile(sample_profile("Older application profile"))

    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 2
        assert connection.execute("SELECT id, name FROM components").fetchall() == component_before
        assert connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'components'"
        ).fetchone()[0] == schema_before
    assert len(older.list_profiles()) == 2
