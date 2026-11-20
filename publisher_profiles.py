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
SCHEMA_VERSION = 1
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
