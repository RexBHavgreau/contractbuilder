"""Local SQLite storage for reusable publisher profiles.

The database is kept in the user's application-data directory, not beside the
executable or in the source repository, so application updates do not replace it.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import sqlite3
import sys
from typing import Callable, Iterator, Mapping, Sequence




# The existing publisher_profiles.sqlite3 layout is schema version 1.
# Later component-library changes add one migration per new version.
SCHEMA_VERSION = 3
_MIGRATIONS: dict[int, Callable[[sqlite3.Connection], None]] = {}

PROFILE_FIELDS = (
    "publisher_name",
    "contact_name",
    "contact_title",
    "contact_email",
    "contact_phone",
    "website",
    "address_line1",
    "address_line2",
    "city",
    "region",
    "postal_code",
    "country",
    "notes",
)

_FIELD_ALIASES = {
    "international publisher name": "publisher_name",
    "publisher name": "publisher_name",
    "international publisher": "publisher_name",
    "publisher": "publisher_name",
    "international publisher contact": "contact_name",
    "international publisher contact name": "contact_name",
    "international publisher contact person": "contact_name",
    "publisher contact": "contact_name",
    "publisher contact person": "contact_name",
    "contact person": "contact_name",
    "contact name": "contact_name",
    "international publisher contact title": "contact_title",
    "publisher contact title": "contact_title",
    "contact title": "contact_title",
    "international publisher email": "contact_email",
    "international publisher contact email": "contact_email",
    "publisher email": "contact_email",
    "contact email": "contact_email",
    "email": "contact_email",
    "international publisher phone": "contact_phone",
    "international publisher contact phone": "contact_phone",
    "publisher phone": "contact_phone",
    "contact phone": "contact_phone",
    "phone": "contact_phone",
    "international publisher website": "website",
    "publisher website": "website",
    "website": "website",
    "international publisher address": "formatted_address",
    "international publisher mailing address": "formatted_address",
    "publisher address": "formatted_address",
    "mailing address": "formatted_address",
    "address": "formatted_address",
    "international publisher address line 1": "address_line1",
    "publisher address line 1": "address_line1",
    "address line 1": "address_line1",
    "international publisher address line 2": "address_line2",
    "publisher address line 2": "address_line2",
    "address line 2": "address_line2",
    "international publisher city": "city",
    "publisher city": "city",
    "city": "city",
    "international publisher state": "region",
    "international publisher province": "region",
    "publisher state": "region",
    "publisher province": "region",
    "state province": "region",
    "state": "region",
    "province": "region",
    "international publisher postal code": "postal_code",
    "international publisher zip code": "postal_code",
    "publisher postal code": "postal_code",
    "postal code": "postal_code",
    "zip code": "postal_code",
    "international publisher country": "country",
    "publisher country": "country",
    "country": "country",
}


def default_database_path() -> Path:
    """Return a per-user, OS-appropriate location for the profile database."""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share"))
    return base / "TMAI Contract Builder" / "publisher_profiles.sqlite3"


def _normalize_field_name(value: str) -> str:
    value = re.sub(r"['’]s\b", "", str(value).casefold())
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def format_address(profile: Mapping[str, object]) -> str:
    """Format saved address components as a conventional multiline postal address."""
    lines = [
        str(profile.get("address_line1") or "").strip(),
        str(profile.get("address_line2") or "").strip(),
    ]
    lines = [line for line in lines if line]
    city = str(profile.get("city") or "").strip()
    region = str(profile.get("region") or "").strip()
    postal_code = str(profile.get("postal_code") or "").strip()
    locality = ", ".join(part for part in (city, region) if part)
    if postal_code:
        locality = f"{locality} {postal_code}".strip()
    if locality:
        lines.append(locality)
    country = str(profile.get("country") or "").strip()
    if country:
        lines.append(country)
    return "\n".join(lines)


def values_for_template(
    profile: Mapping[str, object], field_names: Sequence[str]
) -> dict[str, str]:
    """Return non-empty publisher values keyed by the template's exact field names.

    A small alias table connects common placeholder labels to profile properties.
    Unrecognized fields are deliberately left untouched for the user to complete.
    """
    result: dict[str, str] = {}
    for field_name in field_names:
        property_name = _FIELD_ALIASES.get(_normalize_field_name(field_name))
        if not property_name:
            continue
        if property_name == "formatted_address":
            # The main form uses a single-line Entry for ordinary text fields.
            # Tkinter Entry silently removes newline characters, which caused
            # address components to run together (for example, "HouseStr.").
            # Convert the formatted postal-address lines to comma-separated
            # components before placing the value in that form control.
            value = ", ".join(
                part.strip()
                for part in format_address(profile).splitlines()
                if part.strip()
            )
        else:
            value = profile.get(property_name)
        if value is not None and str(value).strip():
            result[field_name] = str(value).strip()
    return result


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _create_publisher_schema(connection: sqlite3.Connection) -> None:
    """Create the version-1 publisher schema, without changing existing rows."""
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS publishers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            publisher_name TEXT NOT NULL,
            publisher_name_key TEXT NOT NULL UNIQUE,
            contact_name TEXT NOT NULL DEFAULT '',
            contact_title TEXT NOT NULL DEFAULT '',
            contact_email TEXT NOT NULL DEFAULT '',
            contact_phone TEXT NOT NULL DEFAULT '',
            website TEXT NOT NULL DEFAULT '',
            address_line1 TEXT NOT NULL DEFAULT '',
            address_line2 TEXT NOT NULL DEFAULT '',
            city TEXT NOT NULL DEFAULT '',
            region TEXT NOT NULL DEFAULT '',
            postal_code TEXT NOT NULL DEFAULT '',
            country TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_publishers_name "
        "ON publishers(publisher_name_key)"
    )


def _set_schema_version(connection: sqlite3.Connection, version: int) -> None:
    connection.execute(f"PRAGMA user_version = {int(version)}")


def _migrate_components_and_versions(connection: sqlite3.Connection) -> None:
    """Add reusable components and immutable, numbered Markdown versions."""
    connection.execute(
        """
        CREATE TABLE components (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL CHECK (length(trim(name)) > 0),
            description TEXT NOT NULL DEFAULT '',
            category TEXT NOT NULL DEFAULT '',
            tags TEXT NOT NULL DEFAULT '[]',
            status TEXT NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'archived'))
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE component_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            component_id INTEGER NOT NULL
                REFERENCES components(id) ON DELETE RESTRICT,
            number INTEGER NOT NULL CHECK (number > 0),
            markdown TEXT NOT NULL,
            created TEXT NOT NULL,
            note TEXT NOT NULL DEFAULT '',
            UNIQUE (component_id, number)
        )
        """
    )
    connection.execute(
        "CREATE INDEX idx_component_versions_component_number "
        "ON component_versions(component_id, number DESC)"
    )
    # A saved version is a historical record, not an editable row. Edits
    # insert a new version; no update or delete may rewrite old wording.
    connection.execute(
        """
        CREATE TRIGGER component_versions_immutable_update
        BEFORE UPDATE ON component_versions
        BEGIN
            SELECT RAISE(ABORT, 'component versions are immutable');
        END
        """
    )
    connection.execute(
        """
        CREATE TRIGGER component_versions_immutable_delete
        BEFORE DELETE ON component_versions
        BEGIN
            SELECT RAISE(ABORT, 'component versions cannot be deleted');
        END
        """
    )


_MIGRATIONS[2] = _migrate_components_and_versions


def _migrate_assemblies_and_revisions(connection: sqlite3.Connection) -> None:
    """Add named assemblies and revisions that pin exact component versions."""
    connection.execute(
        """
        CREATE TABLE assemblies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL CHECK (length(trim(name)) > 0),
            description TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'archived')),
            created TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE assembly_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assembly_id INTEGER NOT NULL
                REFERENCES assemblies(id) ON DELETE RESTRICT,
            number INTEGER NOT NULL CHECK (number > 0),
            shell_path TEXT NOT NULL CHECK (length(trim(shell_path)) > 0),
            shell_sha256 TEXT NOT NULL
                CHECK (
                    length(shell_sha256) = 64
                    AND shell_sha256 NOT GLOB '*[^0-9A-Fa-f]*'
                ),
            created TEXT NOT NULL,
            note TEXT NOT NULL DEFAULT '',
            finalized INTEGER NOT NULL DEFAULT 0
                CHECK (finalized IN (0, 1)),
            UNIQUE (assembly_id, number)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE assembly_components (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assembly_version_id INTEGER NOT NULL
                REFERENCES assembly_versions(id) ON DELETE RESTRICT,
            component_version_id INTEGER NOT NULL
                REFERENCES component_versions(id) ON DELETE RESTRICT,
            position INTEGER NOT NULL CHECK (position >= 0),
            included INTEGER NOT NULL DEFAULT 1 CHECK (included IN (0, 1)),
            UNIQUE (assembly_version_id, position)
        )
        """
    )
    connection.execute(
        "CREATE INDEX idx_assembly_versions_assembly_number "
        "ON assembly_versions(assembly_id, number DESC)"
    )
    connection.execute(
        "CREATE INDEX idx_assembly_components_version "
        "ON assembly_components(component_version_id)"
    )

    # A revision is assembled in one transaction while finalized=0. The one
    # permitted update changes only finalized from 0 to 1. Thereafter neither
    # the revision metadata nor its pinned component membership can change.
    connection.execute(
        """
        CREATE TRIGGER assembly_versions_finalize_only
        BEFORE UPDATE ON assembly_versions
        WHEN NOT (
            OLD.finalized = 0 AND NEW.finalized = 1
            AND NEW.id = OLD.id
            AND NEW.assembly_id = OLD.assembly_id
            AND NEW.number = OLD.number
            AND NEW.shell_path = OLD.shell_path
            AND NEW.shell_sha256 = OLD.shell_sha256
            AND NEW.created = OLD.created
            AND NEW.note = OLD.note
        )
        BEGIN
            SELECT RAISE(ABORT, 'assembly revisions are immutable');
        END
        """
    )
    connection.execute(
        """
        CREATE TRIGGER assembly_versions_immutable_delete
        BEFORE DELETE ON assembly_versions
        BEGIN
            SELECT RAISE(ABORT, 'assembly revisions cannot be deleted');
        END
        """
    )
    connection.execute(
        """
        CREATE TRIGGER assembly_components_no_late_insert
        BEFORE INSERT ON assembly_components
        WHEN COALESCE(
            (SELECT finalized FROM assembly_versions
             WHERE id = NEW.assembly_version_id), 0
        ) = 1
        BEGIN
            SELECT RAISE(ABORT, 'assembly revisions are immutable');
        END
        """
    )
    connection.execute(
        """
        CREATE TRIGGER assembly_components_immutable_update
        BEFORE UPDATE ON assembly_components
        BEGIN
            SELECT RAISE(ABORT, 'assembly revisions are immutable');
        END
        """
    )
    connection.execute(
        """
        CREATE TRIGGER assembly_components_immutable_delete
        BEFORE DELETE ON assembly_components
        BEGIN
            SELECT RAISE(ABORT, 'assembly revisions are immutable');
        END
        """
    )
    # Keep referential safety even for SQLite connections that have not
    # enabled PRAGMA foreign_keys. Archived history is never hard-deleted.
    connection.execute(
        """
        CREATE TRIGGER components_prevent_delete_with_history
        BEFORE DELETE ON components
        WHEN EXISTS (
            SELECT 1 FROM component_versions
            WHERE component_id = OLD.id
        )
        BEGIN
            SELECT RAISE(ABORT, 'components with versions cannot be deleted');
        END
        """
    )
    connection.execute(
        """
        CREATE TRIGGER assemblies_prevent_delete_with_revisions
        BEFORE DELETE ON assemblies
        WHEN EXISTS (
            SELECT 1 FROM assembly_versions
            WHERE assembly_id = OLD.id
        )
        BEGIN
            SELECT RAISE(ABORT, 'assemblies with revisions cannot be deleted');
        END
        """
    )


_MIGRATIONS[3] = _migrate_assemblies_and_revisions



def _verify_publisher_schema(connection: sqlite3.Connection) -> None:
    """Refuse to stamp or migrate a database missing its existing profile data."""
    if not _table_exists(connection, "publishers"):
        raise sqlite3.DatabaseError("The publisher profiles table is missing.")
    columns = {
        row[1] for row in connection.execute("PRAGMA table_info(publishers)").fetchall()
    }
    required = {
        "id", "publisher_name", "publisher_name_key", "contact_name",
        "contact_title", "contact_email", "contact_phone", "website",
        "address_line1", "address_line2", "city", "region", "postal_code",
        "country", "notes", "created_at", "updated_at",
    }
    missing = sorted(required - columns)
    if missing:
        raise sqlite3.DatabaseError(
            "The publisher profiles table is missing required column(s): "
            + ", ".join(missing)
        )


def _verify_component_schema(connection: sqlite3.Connection) -> None:
    """Verify the version-2 component tables and immutability triggers."""
    required = {
        "components": {"id", "name", "description", "category", "tags", "status"},
        "component_versions": {
            "id", "component_id", "number", "markdown", "created", "note"
        },
    }
    for table_name, expected in required.items():
        if not _table_exists(connection, table_name):
            raise sqlite3.DatabaseError(f"The {table_name} table is missing.")
        actual = {
            row[1] for row in connection.execute(
                f"PRAGMA table_info({table_name})"
            ).fetchall()
        }
        missing = sorted(expected - actual)
        if missing:
            raise sqlite3.DatabaseError(
                f"The {table_name} table is missing required column(s): "
                + ", ".join(missing)
            )

    triggers = {
        row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'trigger'"
        ).fetchall()
    }
    required_triggers = {
        "component_versions_immutable_update",
        "component_versions_immutable_delete",
    }
    missing_triggers = sorted(required_triggers - triggers)
    if missing_triggers:
        raise sqlite3.DatabaseError(
            "The component schema is missing required trigger(s): "
            + ", ".join(missing_triggers)
        )


def _verify_assembly_schema(connection: sqlite3.Connection) -> None:
    """Verify the version-3 assembly tables and revision-protection triggers."""
    required = {
        "assemblies": {"id", "name", "description", "status", "created"},
        "assembly_versions": {
            "id", "assembly_id", "number", "shell_path", "shell_sha256",
            "created", "note", "finalized",
        },
        "assembly_components": {
            "id", "assembly_version_id", "component_version_id",
            "position", "included",
        },
    }
    for table_name, expected in required.items():
        if not _table_exists(connection, table_name):
            raise sqlite3.DatabaseError(f"The {table_name} table is missing.")
        actual = {
            row[1] for row in connection.execute(
                f"PRAGMA table_info({table_name})"
            ).fetchall()
        }
        missing = sorted(expected - actual)
        if missing:
            raise sqlite3.DatabaseError(
                f"The {table_name} table is missing required column(s): "
                + ", ".join(missing)
            )

    triggers = {
        row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'trigger'"
        ).fetchall()
    }
    required_triggers = {
        "assembly_versions_finalize_only",
        "assembly_versions_immutable_delete",
        "assembly_components_no_late_insert",
        "assembly_components_immutable_update",
        "assembly_components_immutable_delete",
        "components_prevent_delete_with_history",
        "assemblies_prevent_delete_with_revisions",
    }
    missing_triggers = sorted(required_triggers - triggers)
    if missing_triggers:
        raise sqlite3.DatabaseError(
            "The assembly schema is missing required trigger(s): "
            + ", ".join(missing_triggers)
        )


def _verify_database(
    connection: sqlite3.Connection, expected_version: int | None
) -> None:
    """Check database integrity and the known publisher schema before commit."""
    if expected_version is not None:
        actual = int(connection.execute("PRAGMA user_version").fetchone()[0])
        if actual != expected_version:
            raise sqlite3.DatabaseError(
                f"Database schema version is {actual}; expected {expected_version}."
            )
    _verify_publisher_schema(connection)
    if expected_version is not None and expected_version >= 2:
        _verify_component_schema(connection)
    if expected_version is not None and expected_version >= 3:
        _verify_assembly_schema(connection)
    integrity = connection.execute("PRAGMA integrity_check").fetchall()
    if integrity != [("ok",)]:
        raise sqlite3.DatabaseError(
            "The database did not pass its integrity check: "
            + "; ".join(str(row[0]) for row in integrity[:5])
        )
    foreign_key_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
    if foreign_key_errors:
        raise sqlite3.DatabaseError("The database contains broken foreign-key references.")


def _backup_database(
    connection: sqlite3.Connection, database_path: Path, version: int
) -> Path:
    """Create and verify one consistent backup for the schema being upgraded."""
    backup_path = Path(str(database_path) + f".bak-{version}")
    if backup_path.exists():
        if not backup_path.is_file():
            raise OSError(f"The database backup path is not a file: {backup_path.name}")
        backup = sqlite3.connect(str(backup_path))
        try:
            backup_version = int(backup.execute("PRAGMA user_version").fetchone()[0])
            if backup_version != version:
                raise sqlite3.DatabaseError(
                    f"The existing backup '{backup_path.name}' has schema version "
                    f"{backup_version}, not {version}; it was not replaced."
                )
            _verify_database(backup, version)
        finally:
            backup.close()
        return backup_path

    # O_EXCL prevents two app instances from replacing one another's backup.
    descriptor = os.open(
        str(backup_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600
    )
    os.close(descriptor)
    try:
        backup = sqlite3.connect(str(backup_path))
        try:
            connection.backup(backup)
            _verify_database(backup, version)
        finally:
            backup.close()
    except Exception:
        try:
            backup_path.unlink()
        except OSError:
            pass
        raise
    return backup_path


class PublisherProfileStore:
    """CRUD access to publisher profiles in a local SQLite database."""

    def __init__(self, path: str | Path | None = None):
        use_default_path = path is None
        self.path = Path(path) if path is not None else default_database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if use_default_path and os.name != "nt":
            # Publisher contact details are personal/business data; keep the
            # per-user database directory private on POSIX systems.
            self.path.parent.chmod(0o700)
        self._initialize()
        if use_default_path and os.name != "nt":
            self.path.chmod(0o600)

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(str(self.path), timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        """Create the legacy schema or apply versioned, recoverable migrations."""
        connection = sqlite3.connect(str(self.path), timeout=10, isolation_level=None)
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            version = int(connection.execute("PRAGMA user_version").fetchone()[0])

            if version == 0:
                # Databases made before schema versioning already have the
                # publisher schema. SQLite's default user_version is zero, so
                # treat that existing layout (and a brand-new empty database)
                # as version 1 rather than trying to migrate it from nothing.
                connection.execute("BEGIN IMMEDIATE")
                try:
                    _create_publisher_schema(connection)
                    _set_schema_version(connection, 1)
                    _verify_database(connection, 1)
                    connection.commit()
                except Exception:
                    connection.rollback()
                    raise
                version = 1

            _verify_publisher_schema(connection)

            if version > SCHEMA_VERSION:
                # A newer app has already extended this database. Older
                # versions may continue using the publisher table, but must
                # neither downgrade the version nor touch unknown tables.
                _verify_database(connection, expected_version=None)
                return

            if version < SCHEMA_VERSION:
                missing = [target for target in range(version + 1, SCHEMA_VERSION + 1)
                           if target not in _MIGRATIONS]
                if missing:
                    raise sqlite3.DatabaseError(
                        "Database upgrade is missing migration(s) for schema version(s): "
                        + ", ".join(str(item) for item in missing)
                    )

                # The backup is a consistent SQLite snapshot, not a raw file
                # copy (which could miss committed data in a WAL file). It is
                # named for the version being upgraded and is never replaced.
                _backup_database(connection, self.path, version)
                connection.execute("BEGIN IMMEDIATE")
                try:
                    # Another app instance may have completed the same upgrade
                    # while this one was creating or checking the backup. Read
                    # the version again after obtaining the write lock so no
                    # migration is applied twice.
                    locked_version = int(
                        connection.execute("PRAGMA user_version").fetchone()[0]
                    )
                    if locked_version < version:
                        raise sqlite3.DatabaseError(
                            "The database schema version changed unexpectedly during upgrade."
                        )
                    if locked_version > SCHEMA_VERSION:
                        # A newer app won the race. Leave its tables and
                        # version marker alone.
                        _verify_database(connection, expected_version=None)
                    else:
                        for target in range(locked_version + 1, SCHEMA_VERSION + 1):
                            _MIGRATIONS[target](connection)
                            _set_schema_version(connection, target)
                        _verify_database(connection, SCHEMA_VERSION)
                    connection.commit()
                except Exception:
                    connection.rollback()
                    raise
            else:
                _verify_database(connection, SCHEMA_VERSION)
        finally:
            connection.close()

    def list_profiles(self) -> list[dict[str, object]]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM publishers ORDER BY publisher_name COLLATE NOCASE"
            ).fetchall()
            return [dict(row) for row in rows]

    def get_profile(self, profile_id: int) -> dict[str, object] | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM publishers WHERE id = ?", (int(profile_id),)
            ).fetchone()
            return dict(row) if row else None

    def save_profile(
        self, profile: Mapping[str, object], profile_id: int | None = None
    ) -> int:
        """Insert a profile or update the requested profile; return its database ID."""
        name = str(profile.get("publisher_name") or "").strip()
        if not name:
            raise ValueError("Enter a publisher name.")

        values = {field: str(profile.get(field) or "").strip() for field in PROFILE_FIELDS}
        values["publisher_name"] = name
        # Python's casefold handles international scripts more consistently than
        # SQLite's built-in NOCASE collation, which is limited to ASCII letters.
        name_key = " ".join(name.casefold().split())
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        try:
            with self._connection() as connection:
                if profile_id is None:
                    columns = ", ".join((*PROFILE_FIELDS, "publisher_name_key", "created_at", "updated_at"))
                    placeholders = ", ".join("?" for _ in range(len(PROFILE_FIELDS) + 3))
                    cursor = connection.execute(
                        f"INSERT INTO publishers ({columns}) VALUES ({placeholders})",
                        (*[values[field] for field in PROFILE_FIELDS], name_key, now, now),
                    )
                    return int(cursor.lastrowid)
                assignments = ", ".join(f"{field} = ?" for field in PROFILE_FIELDS)
                cursor = connection.execute(
                    f"UPDATE publishers SET {assignments}, publisher_name_key = ?, "
                    "updated_at = ? WHERE id = ?",
                    (*[values[field] for field in PROFILE_FIELDS], name_key, now, int(profile_id)),
                )
                if cursor.rowcount == 0:
                    raise ValueError("That publisher profile no longer exists.")
                return int(profile_id)
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                "A publisher with that name already exists. Use a distinct name or edit the existing profile."
            ) from exc

    def delete_profile(self, profile_id: int) -> bool:
        with self._connection() as connection:
            cursor = connection.execute(
                "DELETE FROM publishers WHERE id = ?", (int(profile_id),)
            )
            return cursor.rowcount > 0
