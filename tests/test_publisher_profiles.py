"""Tests for the local publisher profile database and template field mapping."""
import pathlib
import sqlite3
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import publisher_profiles as profiles  # noqa: E402
from library import ComponentLibrary  # noqa: E402


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


def _new_v1_store(monkeypatch, path):
    """Create a database using the publisher-only schema for migration tests."""
    monkeypatch.setattr(profiles, "SCHEMA_VERSION", 1)
    monkeypatch.setattr(profiles, "_MIGRATIONS", {})
    return profiles.PublisherProfileStore(path)


def _upgrade_store_to_v2(monkeypatch, path, migration):
    monkeypatch.setattr(profiles, "SCHEMA_VERSION", 2)
    monkeypatch.setattr(profiles, "_MIGRATIONS", {2: migration})
    return profiles.PublisherProfileStore(path)


def test_new_and_unversioned_legacy_databases_are_schema_version_one(tmp_path, monkeypatch):
    path = tmp_path / "publisher_profiles.sqlite3"
    store = _new_v1_store(monkeypatch, path)
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
    store = _new_v1_store(monkeypatch, path)
    first_id = store.save_profile(sample_profile())
    second = sample_profile("Maison Exemple")
    second_id = store.save_profile(second)
    before = store.list_profiles()

    upgraded = _upgrade_store_to_v2(
        monkeypatch, path, profiles._migrate_components_and_versions
    )

    assert _user_version(path) == 2
    assert upgraded.list_profiles() == before
    before_by_id = {row["id"]: row for row in before}
    assert upgraded.get_profile(first_id) == before_by_id[first_id]
    assert upgraded.get_profile(second_id) == before_by_id[second_id]

    backup_path = pathlib.Path(str(path) + ".bak-1")
    assert backup_path.is_file()
    assert _user_version(backup_path) == 1
    with sqlite3.connect(backup_path) as backup:
        assert backup.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'components'"
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
    store = _new_v1_store(monkeypatch, path)
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
    # Reopen with the old schema version after simulating the failed
    # migration, rather than immediately retrying the same failing step.
    monkeypatch.setattr(profiles, "SCHEMA_VERSION", 1)
    monkeypatch.setattr(profiles, "_MIGRATIONS", {})
    assert profiles.PublisherProfileStore(path).list_profiles() == before

    backup_path = pathlib.Path(str(path) + ".bak-1")
    assert backup_path.is_file()
    assert _user_version(backup_path) == 1
    with sqlite3.connect(backup_path) as backup:
        assert backup.execute("SELECT notes FROM publishers").fetchone()[0] == before[0]["notes"]



def test_v2_migration_creates_components_and_immutable_versions(tmp_path, monkeypatch):
    path = tmp_path / "publisher_profiles.sqlite3"
    legacy = _new_v1_store(monkeypatch, path)
    publisher_id = legacy.save_profile(sample_profile())
    publishers_before = legacy.list_profiles()

    monkeypatch.setattr(profiles, "SCHEMA_VERSION", 2)
    monkeypatch.setattr(
        profiles, "_MIGRATIONS", {2: profiles._migrate_components_and_versions}
    )
    upgraded = profiles.PublisherProfileStore(path)

    assert _user_version(path) == 2
    assert upgraded.list_profiles() == publishers_before
    assert upgraded.get_profile(publisher_id) == publishers_before[0]

    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        component_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(components)")
        }
        version_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(component_versions)")
        }
        assert {"id", "name", "description", "category", "tags", "status"} <= component_columns
        assert {"id", "component_id", "number", "markdown", "created", "note"} <= version_columns

        # Arbitrary categories and tag labels are accepted; no fixed taxonomy
        # is imposed by the schema.
        cursor = connection.execute(
            "INSERT INTO components (name, category, tags) VALUES (?, ?, ?)",
            ("Payment terms", "A category made by the user", '["custom tag", "another tag"]'),
        )
        component_id = cursor.lastrowid
        connection.execute(
            "INSERT INTO component_versions "
            "(component_id, number, markdown, created, note) VALUES (?, 1, ?, ?, ?)",
            (component_id, "Payment is due within {{Payment Period}}.", "2026-11-20T16:00:00+00:00", "First draft"),
        )
        version_id = connection.execute(
            "SELECT id FROM component_versions WHERE component_id = ?", (component_id,)
        ).fetchone()[0]

        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute(
                "UPDATE component_versions SET markdown = 'rewritten' WHERE id = ?",
                (version_id,),
            )
        with pytest.raises(sqlite3.IntegrityError, match="cannot be deleted"):
            connection.execute(
                "DELETE FROM component_versions WHERE id = ?", (version_id,)
            )

        # A new version is allowed; it does not overwrite the first one.
        connection.execute(
            "INSERT INTO component_versions "
            "(component_id, number, markdown, created, note) VALUES (?, 2, ?, ?, ?)",
            (component_id, "Payment is due within {{Due Date}}.", "2026-11-20T16:01:00+00:00", "Revised draft"),
        )
        versions = connection.execute(
            "SELECT number, markdown FROM component_versions "
            "WHERE component_id = ? ORDER BY number",
            (component_id,),
        ).fetchall()
        assert versions == [
            (1, "Payment is due within {{Payment Period}}."),
            (2, "Payment is due within {{Due Date}}."),
        ]

        with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
            connection.execute(
                "INSERT INTO component_versions "
                "(component_id, number, markdown, created, note) VALUES (?, 2, ?, ?, ?)",
                (component_id, "Duplicate revision.", "2026-11-20T16:02:00+00:00", ""),
            )
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            connection.execute(
                "INSERT INTO component_versions "
                "(component_id, number, markdown, created, note) VALUES (?, 1, ?, ?, ?)",
                (999999, "Orphaned revision.", "2026-11-20T16:02:00+00:00", ""),
            )

    backup_path = pathlib.Path(str(path) + ".bak-1")
    assert backup_path.is_file()
    assert _user_version(backup_path) == 1
    with sqlite3.connect(backup_path) as backup:
        assert backup.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'components'"
        ).fetchone() is None


def test_v3_migration_pins_immutable_assembly_revisions_and_shell_hash(tmp_path, monkeypatch):
    path = tmp_path / "publisher_profiles.sqlite3"
    # Start from the real v2 schema so this test exercises the v2 -> v3 step,
    # rather than allowing the current application to create v3 immediately.
    monkeypatch.setattr(profiles, "SCHEMA_VERSION", 2)
    monkeypatch.setattr(
        profiles, "_MIGRATIONS", {2: profiles._migrate_components_and_versions}
    )
    library = ComponentLibrary(path)
    component_id = library.create_component(
        "Payment clause", "Payment is due within thirty days."
    )
    component_version_id = library.list_component_versions(component_id)[0]["id"]

    monkeypatch.setattr(profiles, "SCHEMA_VERSION", 3)
    monkeypatch.setattr(
        profiles,
        "_MIGRATIONS",
        {
            2: profiles._migrate_components_and_versions,
            3: profiles._migrate_assemblies_and_revisions,
        },
    )
    upgraded = profiles.PublisherProfileStore(path)
    assert _user_version(path) == 3
    assert library.get_component(component_id)["name"] == "Payment clause"

    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        assembly_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(assemblies)")
        }
        revision_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(assembly_versions)")
        }
        membership_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(assembly_components)")
        }
        assert {"id", "name", "description", "status", "created"} <= assembly_columns
        assert {
            "id", "assembly_id", "number", "shell_path", "shell_sha256",
            "created", "note", "finalized",
        } <= revision_columns
        assert {
            "id", "assembly_version_id", "component_version_id", "position", "included"
        } <= membership_columns

        assembly_id = connection.execute(
            "INSERT INTO assemblies (name, description, created) "
            "VALUES (?, ?, ?)",
            ("Publisher agreement", "A reusable recipe", "2026-11-20T16:30:00+00:00"),
        ).lastrowid
        shell_path = "C:/Contracts/Standard Shell.docx"
        shell_hash = "a" * 64
        revision_id = connection.execute(
            "INSERT INTO assembly_versions "
            "(assembly_id, number, shell_path, shell_sha256, created, note) "
            "VALUES (?, 1, ?, ?, ?, ?)",
            (
                assembly_id,
                shell_path,
                shell_hash,
                "2026-11-20T16:31:00+00:00",
                "Initial assembly",
            ),
        ).lastrowid

        # Pin a specific version ID. The same component version may be used
        # more than once in a recipe, at different positions.
        connection.execute(
            "INSERT INTO assembly_components "
            "(assembly_version_id, component_version_id, position, included) "
            "VALUES (?, ?, 0, 1)",
            (revision_id, component_version_id),
        )
        connection.execute(
            "INSERT INTO assembly_components "
            "(assembly_version_id, component_version_id, position, included) "
            "VALUES (?, ?, 1, 0)",
            (revision_id, component_version_id),
        )
        connection.execute(
            "UPDATE assembly_versions SET finalized = 1 WHERE id = ?",
            (revision_id,),
        )

        pinned = connection.execute(
            "SELECT component_version_id, position, included "
            "FROM assembly_components WHERE assembly_version_id = ? "
            "ORDER BY position",
            (revision_id,),
        ).fetchall()
        assert pinned == [(component_version_id, 0, 1), (component_version_id, 1, 0)]

        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute(
                "UPDATE assembly_versions SET shell_path = 'different.docx' WHERE id = ?",
                (revision_id,),
            )
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute(
                "INSERT INTO assembly_components "
                "(assembly_version_id, component_version_id, position, included) "
                "VALUES (?, ?, 2, 1)",
                (revision_id, component_version_id),
            )
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute(
                "UPDATE assembly_components SET included = 0 WHERE assembly_version_id = ?",
                (revision_id,),
            )
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute(
                "DELETE FROM assembly_components WHERE assembly_version_id = ?",
                (revision_id,),
            )
        with pytest.raises(sqlite3.IntegrityError, match="cannot be deleted"):
            connection.execute(
                "DELETE FROM assembly_versions WHERE id = ?", (revision_id,)
            )

        empty_draft_id = connection.execute(
            "INSERT INTO assembly_versions "
            "(assembly_id, number, shell_path, shell_sha256, created) "
            "VALUES (?, 2, ?, ?, ?)",
            (assembly_id, shell_path, shell_hash, "2026-11-20T16:32:00+00:00"),
        ).lastrowid
        with pytest.raises(
            sqlite3.IntegrityError, match="must include a component"
        ):
            connection.execute(
                "UPDATE assembly_versions SET finalized = 1 WHERE id = ?",
                (empty_draft_id,),
            )

        # The assembly itself remains archivable while its revision is pinned.
        connection.execute(
            "UPDATE assemblies SET status = 'archived' WHERE id = ?", (assembly_id,)
        )
        saved = connection.execute(
            "SELECT shell_path, shell_sha256, finalized FROM assembly_versions WHERE id = ?",
            (revision_id,),
        ).fetchone()
        assert saved == (shell_path, shell_hash, 1)

        with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
            connection.execute(
                "INSERT INTO assembly_versions "
                "(assembly_id, number, shell_path, shell_sha256, created) "
                "VALUES (?, 2, ?, ?, ?)",
                (assembly_id, shell_path, "not-a-hash", "2026-11-20T16:32:00+00:00"),
            )

    backup_path = pathlib.Path(str(path) + ".bak-2")
    assert backup_path.is_file()
    assert _user_version(backup_path) == 2
    with sqlite3.connect(backup_path) as backup:
        assert backup.execute("SELECT COUNT(*) FROM components").fetchone()[0] == 1
        assert backup.execute("SELECT COUNT(*) FROM component_versions").fetchone()[0] == 1

def test_older_application_can_use_publishers_without_changing_newer_tables(
    tmp_path, monkeypatch
):
    path = tmp_path / "publisher_profiles.sqlite3"

    newer = _upgrade_store_to_v2(
        monkeypatch, path, profiles._migrate_components_and_versions
    )
    newer.save_profile(sample_profile())
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT INTO components (name) VALUES ('Invented component')"
        )
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

def test_v4_migration_preserves_v3_publisher_and_component_data(tmp_path, monkeypatch):
    path = tmp_path / "publisher_profiles.sqlite3"
    monkeypatch.setattr(profiles, "SCHEMA_VERSION", 3)
    monkeypatch.setattr(
        profiles,
        "_MIGRATIONS",
        {
            2: profiles._migrate_components_and_versions,
            3: profiles._migrate_assemblies_and_revisions,
        },
    )
    legacy = profiles.PublisherProfileStore(path)
    profile_id = legacy.save_profile(sample_profile())
    library = ComponentLibrary(path)
    component_id = library.create_component(
        "Payment terms", "Payment is due within {{Payment Date}}."
    )
    before_profiles = legacy.list_profiles()
    before_component = library.get_component(component_id)
    assert _user_version(path) == 3

    monkeypatch.setattr(profiles, "SCHEMA_VERSION", 4)
    monkeypatch.setattr(
        profiles,
        "_MIGRATIONS",
        {
            2: profiles._migrate_components_and_versions,
            3: profiles._migrate_assemblies_and_revisions,
            4: profiles._migrate_field_definitions,
        },
    )
    upgraded = profiles.PublisherProfileStore(path)

    assert _user_version(path) == 5
    assert upgraded.list_profiles() == before_profiles
    assert upgraded.get_profile(profile_id) == before_profiles[0]
    assert library.get_component(component_id) == before_component
    with sqlite3.connect(path) as connection:
        columns = {
            row[1] for row in connection.execute(
                "PRAGMA table_info(field_definitions)"
            )
        }
        assert {
            "id", "name", "name_key", "description", "field_group",
            "default_format", "default_options", "allowed_values",
            "publisher_profile_column", "publisher_detail_name", "status",
        } <= columns
        assert connection.execute(
            "SELECT COUNT(*) FROM field_definitions"
        ).fetchone() == (0,)

    backup_path = pathlib.Path(str(path) + ".bak-3")
    assert backup_path.is_file()
    assert _user_version(backup_path) == 3
    with sqlite3.connect(backup_path) as backup:
        assert backup.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name = 'field_definitions'"
        ).fetchone() is None
        assert backup.execute("SELECT COUNT(*) FROM publishers").fetchone() == (1,)
        assert backup.execute("SELECT COUNT(*) FROM components").fetchone() == (1,)
        assert backup.execute(
            "SELECT COUNT(*) FROM component_versions"
        ).fetchone() == (1,)


def test_older_v3_application_uses_profiles_without_changing_newer_tables(
    tmp_path, monkeypatch
):
    path = tmp_path / "publisher_profiles.sqlite3"
    current = profiles.PublisherProfileStore(path)
    first_profile_id = current.save_profile(sample_profile())
    library = ComponentLibrary(path)
    field_id = library.add_field_definition(
        "Publisher Type",
        group="Publisher",
        default_format="choice",
        allowed_values=["Non-profit", "Sole proprietor"],
    )
    with sqlite3.connect(path) as connection:
        field_before = connection.execute(
            "SELECT id, name, name_key, allowed_values, status "
            "FROM field_definitions"
        ).fetchall()
        schema_before = connection.execute(
            "SELECT sql FROM sqlite_master "
            "WHERE type = 'table' AND name = 'field_definitions'"
        ).fetchone()[0]
    assert field_before[0][0] == field_id
    assert _user_version(path) == 4

    # Simulate the previous release, which knows schemas only through v3.
    monkeypatch.setattr(profiles, "SCHEMA_VERSION", 3)
    monkeypatch.setattr(
        profiles,
        "_MIGRATIONS",
        {
            2: profiles._migrate_components_and_versions,
            3: profiles._migrate_assemblies_and_revisions,
        },
    )
    older = profiles.PublisherProfileStore(path)
    second_profile_id = older.save_profile(sample_profile("Older application profile"))

    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (5,)
        assert connection.execute(
            "SELECT id, name, name_key, allowed_values, status "
            "FROM field_definitions"
        ).fetchall() == field_before
        assert connection.execute(
            "SELECT sql FROM sqlite_master "
            "WHERE type = 'table' AND name = 'field_definitions'"
        ).fetchone()[0] == schema_before
    assert older.get_profile(first_profile_id) is not None
    assert older.get_profile(second_profile_id)["publisher_name"] == (
        "Older application profile"
    )

def test_builtin_publisher_fields_link_to_profile_columns_and_autofill():
    fields = profiles.publisher_profile_field_definitions()
    assert [field["publisher_profile_column"] for field in fields] == [
        *profiles.PROFILE_FIELDS,
        "formatted_address",
    ]
    assert all(field["group"] == "Publisher" for field in fields)
    assert all(field["source"] == "publisher_profile" for field in fields)

    by_column = {
        field["publisher_profile_column"]: field["name"] for field in fields
    }
    assert by_column["publisher_name"] == "Publisher name"
    assert by_column["contact_email"] == "Contact email"
    assert by_column["formatted_address"] == "Publisher address"
    assert "notes" in by_column
    assert not any("contract type" in name.casefold() for name in by_column.values())

    profile = sample_profile()
    mapped = profiles.values_for_template(
        profile, [field["name"] for field in fields]
    )
    expected = {
        by_column[column]: str(profile[column])
        for column in profiles.PROFILE_FIELDS
        if str(profile.get(column) or "").strip()
    }
    expected[by_column["formatted_address"]] = ", ".join(
        profiles.format_address(profile).splitlines()
    )
    assert mapped == expected

def test_user_field_matches_are_saved_updated_and_removed(tmp_path):
    store = profiles.PublisherProfileStore(tmp_path / "publisher_profiles.sqlite3")
    first = store.save_field_match("Legal Name", "publisher_name")
    assert store.field_match_map() == {"Legal Name": "publisher_name"}

    second = store.save_field_match("Legal Name", "contact_name")
    assert second == first
    assert len(store.list_field_matches()) == 1
    assert store.field_match_map() == {"Legal Name": "contact_name"}

    assert store.delete_field_match(first)
    assert store.field_match_map() == {}
    assert not store.delete_field_match(first)


def test_user_field_matches_override_builtins_and_normalize_names(tmp_path):
    store = profiles.PublisherProfileStore(tmp_path / "publisher_profiles.sqlite3")
    store.save_field_match(" Publisher’s   Legal Name ", "contact_name")
    profile = sample_profile()
    values = profiles.values_for_template(
        profile,
        ["Publisher's Legal   Name", "Publisher Name", "Unknown Field"],
        store.field_match_map(),
    )
    assert values == {
        "Publisher's Legal   Name": profile["contact_name"],
        "Publisher Name": profile["publisher_name"],
    }


def test_user_field_matches_reject_invalid_columns_and_names(tmp_path):
    store = profiles.PublisherProfileStore(tmp_path / "publisher_profiles.sqlite3")
    with pytest.raises(ValueError, match="valid publisher profile detail"):
        store.save_field_match("Legal Name", "made_up_column")
    with pytest.raises(ValueError, match="Enter a field name"):
        store.save_field_match("   ", "publisher_name")
    with pytest.raises(ValueError, match="without braces"):
        store.save_field_match("{{Legal Name}}", "publisher_name")


def test_schema_v4_migrates_to_user_field_matching_without_losing_fields(tmp_path):
    path = tmp_path / "publisher_profiles.sqlite3"
    store = profiles.PublisherProfileStore(path)
    store.save_field_match("Legacy field", "publisher_name")
    expected = store.list_field_matches()

    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(profiles, "SCHEMA_VERSION", 4)
        monkeypatch.setattr(
            profiles,
            "_MIGRATIONS",
            {
                2: profiles._migrate_components_and_versions,
                3: profiles._migrate_assemblies_and_revisions,
                4: profiles._migrate_field_definitions,
            },
        )
        older = profiles.PublisherProfileStore(path)
        assert older.list_field_matches() == expected
    finally:
        monkeypatch.undo()

def test_schema_v4_upgrade_adds_field_matches_table(tmp_path, monkeypatch):
    path = tmp_path / "publisher_profiles.sqlite3"
    monkeypatch.setattr(profiles, "SCHEMA_VERSION", 4)
    monkeypatch.setattr(
        profiles,
        "_MIGRATIONS",
        {
            2: profiles._migrate_components_and_versions,
            3: profiles._migrate_assemblies_and_revisions,
            4: profiles._migrate_field_definitions,
        },
    )
    legacy = profiles.PublisherProfileStore(path)
    legacy.save_profile(sample_profile())
    assert _user_version(path) == 4

    monkeypatch.undo()
    current = profiles.PublisherProfileStore(path)
    assert _user_version(path) == 5
    current.save_field_match("Legacy Publisher", "publisher_name")
    assert current.field_match_map() == {"Legacy Publisher": "publisher_name"}
